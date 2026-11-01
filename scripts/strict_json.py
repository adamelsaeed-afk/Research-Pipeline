"""Bounded JSON decoding for local contracts and untrusted model responses."""
import json
import math
from pathlib import Path

MAX_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 64


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member')
        result[key] = value
    return result


def _constant(_):
    raise ValueError('nonfinite JSON number')


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('nonfinite JSON number')
    return number


def loads(content):
    if len(content) > MAX_BYTES or len(content.encode('utf-8') if isinstance(content, str) else content) > MAX_BYTES:
        raise ValueError('JSON exceeds the 4 MiB contract limit')
    if isinstance(content, bytes):
        content = content.decode('utf-8')
    depth, quoted, escaped = 0, False, False
    for char in content:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '{[':
            depth += 1
            if depth > MAX_DEPTH:
                raise ValueError('JSON nesting exceeds the 64-level contract limit')
        elif char in '}]':
            depth -= 1
    try:
        return json.loads(content, object_pairs_hook=_object,
                          parse_constant=_constant, parse_float=_float)
    except RecursionError as exc:
        raise ValueError('JSON nesting exceeds the decoder limit') from exc


def read_text(path: Path, *, limit=MAX_BYTES, errors='strict'):
    with path.open('rb') as source:
        content = source.read(limit + 1)
    if len(content) > limit:
        raise ValueError(f'input exceeds the {limit}-byte limit')
    return content.decode('utf-8', errors=errors)


def read(path: Path):
    return loads(read_text(path))
