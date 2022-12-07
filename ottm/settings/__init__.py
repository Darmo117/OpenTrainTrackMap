import dataclasses as _dt
import json as _json
import logging as _logging
import pathlib as _pathlib
import re as _re


@_dt.dataclass(frozen=True)
class Language:
    code: str
    name: str
    writing_direction: str
    date_format: str
    _mappings: dict[str, str]

    def translate(self, key: str, default: str = None, /, **kwargs) -> str:
        return self._mappings.get(key, default if default is not None else key).format(**kwargs)


SITE_NAME = 'OpenTrainTrackMap'
DEFAULT_LANGUAGE_CODE = 'en'
INVALID_TITLE_REGEX = _re.compile(
    r'([%@<>_#|{}\[\]\x00-\x1f\x7f]|&[A-Za-z0-9\x80-\xff]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;)')
LANGUAGES: dict[str, Language] = {}
LOGGER: _logging.Logger


def init(debug: bool):
    global LOGGER, LANGUAGES

    LOGGER = _logging.Logger('OTTM', level=_logging.DEBUG if debug else _logging.INFO)
    sh = _logging.StreamHandler()
    sh.setFormatter(_logging.Formatter('%(name)s:%(levelname)s:%(message)s'))
    LOGGER.addHandler(sh)
    LOGGER.info('Loading translations…')
    langs_dir = _pathlib.Path(__file__).parent / 'langs'
    for fname in langs_dir.glob('*.json'):
        with (langs_dir / fname).open(encoding='utf8') as lang_file:
            json_obj = _json.load(lang_file)
            lang_code = json_obj['code']
            lang_name = json_obj['name']
            LANGUAGES[lang_code] = Language(
                code=lang_code,
                name=lang_name,
                writing_direction=json_obj['writing_direction'],
                date_format=json_obj['date_format'],
                _mappings=_build_mapping(json_obj['mappings']),
            )
            LOGGER.info(f'Loaded translations for {lang_name} ({lang_code})')
    LOGGER.info('Translations loaded.')


def _build_mapping(json_object: dict[str, str | dict], root: str = None) -> dict[str, str]:
    mapping = {}
    for k, v in json_object.items():
        if root is not None:
            k = f'{root}.{k}'
        if isinstance(v, str):
            mapping[k] = str(v)
        elif isinstance(v, dict):
            mapping.update(_build_mapping(v, k))
        else:
            raise ValueError(f'illegal value type "{type(v)}" for translation value')
    return mapping
