#!/bin/sh
# Submit a fixed research job from a Linux container sharing files with the host.
# Usage: sh submit_research_job.sh ROOT RECORD BRIEF ROLE TARGET INPUT [TIMEOUT]
set -eu

if [ "$#" -lt 6 ] || [ "$#" -gt 7 ]; then
  echo "Usage: sh submit_research_job.sh ROOT RECORD BRIEF ROLE TARGET INPUT [TIMEOUT]" >&2
  exit 2
fi

root=$1
record=$2
brief=$3
role=$4
target=$5
input=$6
timeout=${7:-600}

case "$role" in validate|gap_fill) ;; *) echo "Invalid role" >&2; exit 2 ;; esac
case "$target" in ''|*[!a-zA-Z0-9_-]*) echo "Invalid target" >&2; exit 2 ;; esac
case "$timeout" in ''|*[!0-9]*) echo "Invalid timeout" >&2; exit 2 ;; esac
if [ "$timeout" -lt 1 ] || [ "$timeout" -gt 3600 ]; then
  echo "Timeout must be 1-3600 seconds" >&2
  exit 2
fi
for value in "$record" "$brief" "$input"; do
  case "$value" in
    ''|/*|../*|*/../*|*/..|*[!a-zA-Z0-9._/-]*)
      echo "Use safe relative file paths beneath ROOT" >&2; exit 2 ;;
  esac
  if [ ! -f "$root/$value" ]; then
    echo "Missing input: $value" >&2; exit 2
  fi
done

if [ ! -r /proc/sys/kernel/random/uuid ]; then
  echo "This container needs /proc/sys/kernel/random/uuid to create a job ID" >&2
  exit 2
fi
job_id=$(tr -d '-' < /proc/sys/kernel/random/uuid)
mkdir -p "$root/requests" "$root/responses"
temporary="$root/requests/$job_id.tmp"
request="$root/requests/$job_id.json"
trap 'rm -f "$temporary"' EXIT HUP INT TERM
printf '{"id":"%s","role":"%s","target":"%s","record":"%s","brief":"%s","input":"%s","timeout":%s}\n' \
  "$job_id" "$role" "$target" "$record" "$brief" "$input" "$timeout" > "$temporary"
mv "$temporary" "$request"
echo "Submitted $job_id"

response="$root/responses/$job_id.json"
elapsed=0
limit=$((timeout + 30))
while [ ! -f "$response" ]; do
  if [ "$elapsed" -ge "$limit" ]; then
    echo "No host-worker response for $job_id" >&2
    exit 2
  fi
  sleep 1
  elapsed=$((elapsed + 1))
done
cat "$response"
if ! grep -q '"status": "completed"' "$response"; then
  exit 2
fi
