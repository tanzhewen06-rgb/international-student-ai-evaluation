"""Portable project roots and explicit project-relative path references."""
import os
from pathlib import Path, PurePosixPath

AGENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parent
RESPONSE_AGENT_ROOT = PROJECT_ROOT / 'Response Agent'
DATA_ROOT = PROJECT_ROOT / 'Sample Data'
RESPONSES_ROOT = DATA_ROOT / 'responses'
EVALUATIONS_ROOT = DATA_ROOT / 'evaluations'
REFERENCE_DATA_ROOT = DATA_ROOT / 'reference_data'


def _io_path(value):
    path = Path(value)
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        absolute = str(path.absolute())
        return Path('\\\\?\\UNC\\' + absolute[2:] if absolute.startswith('\\\\') else '\\\\?\\' + absolute)
    return path


def relocated_path(value):
    raw = str(value)
    if raw.startswith('project://'):
        relative = PurePosixPath(raw[len('project://'):])
        if relative.is_absolute() or '..' in relative.parts or ':' in str(relative):
            raise ValueError('Project path must stay inside the project directory.')
        return _io_path(PROJECT_ROOT.joinpath(*relative.parts))
    normalized = raw.replace('\\', '/')
    if normalized.startswith(('Sample Data/', 'Evaluation Agent/', 'Response Agent/')):
        return _io_path(PROJECT_ROOT / normalized)
    return _io_path(value)


def portable_path(value):
    raw = str(value).removeprefix('\\\\?\\')
    path = Path(raw)
    root = Path(str(PROJECT_ROOT).removeprefix('\\\\?\\'))
    if path.is_absolute() and path.is_relative_to(root):
        return 'project://' + path.relative_to(root).as_posix()
    return value


def path_key(value):
    return str(relocated_path(value)).replace('\\', '/').removeprefix('//?/').casefold()
