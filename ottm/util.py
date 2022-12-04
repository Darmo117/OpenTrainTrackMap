import re


def gather_globals(pattern: str, expected_type: type) -> tuple:
    p = re.compile(pattern)
    return tuple(v for k, v in globals().items() if p.search(k) and isinstance(v, expected_type))


def gather_globals_dict(pattern: str, expected_type: type) -> dict:
    p = re.compile(pattern)
    return {k: v for k, v in globals().items() if p.search(k) and isinstance(v, expected_type)}
