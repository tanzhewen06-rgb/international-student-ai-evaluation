"""JSON file IO using relative paths; scientific hashing uses standard JSON."""
import json as _json
from pathlib import Path
from runtime.paths import portable_path, relocated_path

JSONDecodeError = _json.JSONDecodeError


def _encode(value):
    if isinstance(value, (str, Path)):
        return portable_path(str(value))
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        return {_encode(key): _encode(item) for key, item in value.items()}
    return value


def _decode(value):
    if isinstance(value, str) and value.startswith('project://') and '\n' not in value:
        return str(relocated_path(value))
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if isinstance(value, dict):
        return {_decode(key): _decode(item) for key, item in value.items()}
    return value


def dumps(value, *args, **kwargs):
    return _json.dumps(_encode(value), *args, **kwargs)


def loads(value, *args, **kwargs):
    return _decode(_json.loads(value, *args, **kwargs))


def dump(value, stream, *args, **kwargs):
    return _json.dump(_encode(value), stream, *args, **kwargs)


def load(stream, *args, **kwargs):
    return _decode(_json.load(stream, *args, **kwargs))


def __getattr__(name):
    return getattr(_json, name)
