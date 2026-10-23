"""Own a local CLI process tree for the lifetime of one dispatch."""
import os
import signal
import subprocess

_NATIVE_POPEN = subprocess.Popen


class ProcessTree:
    """Windows Job Object, or a dedicated POSIX process group.

    Windows starts suspended so no child can escape before job assignment.
    POSIX descendants are covered while they retain the inherited process group.
    """
    def __init__(self):
        self.process = None
        self.job = None
        self.native = False
        self.cleanup_error = None
        if os.name == 'nt':
            self._create_job()

    def _create_job(self):
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [('ProcessTime', ctypes.c_int64), ('JobTime', ctypes.c_int64),
                        ('Flags', wintypes.DWORD), ('MinWorkingSet', ctypes.c_size_t),
                        ('MaxWorkingSet', ctypes.c_size_t), ('ActiveProcesses', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t), ('Priority', wintypes.DWORD),
                        ('Scheduling', wintypes.DWORD)]

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ('ReadOps', 'WriteOps', 'OtherOps', 'ReadBytes', 'WriteBytes', 'OtherBytes')]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [('Basic', BasicLimits), ('Io', IoCounters),
                        ('ProcessMemory', ctypes.c_size_t), ('JobMemory', ctypes.c_size_t),
                        ('PeakProcessMemory', ctypes.c_size_t), ('PeakJobMemory', ctypes.c_size_t)]

        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                       ctypes.c_void_p, wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.job = self.kernel.CreateJobObjectW(None, None)
        if not self.job:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def launch(self, command, **kwargs):
        if os.name == 'nt':
            kwargs['creationflags'] = kwargs.get('creationflags', 0) | 0x4  # CREATE_SUSPENDED
        else:
            kwargs['start_new_session'] = True
        self.process = subprocess.Popen(command, **kwargs)
        self.native = isinstance(self.process, _NATIVE_POPEN)
        if os.name == 'nt' and hasattr(self.process, '_handle'):
            import ctypes
            from ctypes import wintypes
            try:
                if not self.kernel.AssignProcessToJobObject(self.job, int(self.process._handle)):
                    raise ctypes.WinError(ctypes.get_last_error())
                # Popen closes the primary thread handle. Resume the suspended
                # process only after assigning it to our non-breakaway job.
                ntdll = ctypes.WinDLL('ntdll')
                ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
                ntdll.NtResumeProcess.restype = ctypes.c_long
                status = ntdll.NtResumeProcess(int(self.process._handle))
                if status < 0:
                    raise OSError(f'Unable to resume dispatch process: NTSTATUS {status:#x}')
            except BaseException:
                self.process.kill()
                self.process.wait(timeout=5)
                raise
        return self.process

    def stop(self):
        if os.name == 'nt':
            import ctypes
            if self.job and not self.kernel.TerminateJobObject(self.job, 1):
                raise ctypes.WinError(ctypes.get_last_error())
        elif self.process is not None and self.native:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def close(self):
        if self.job:
            self.kernel.CloseHandle(self.job)
            self.job = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        try:
            self.stop()
        except Exception as error:
            self.cleanup_error = str(error)
            if exc[0] is None:
                raise
        finally:
            self.close()
