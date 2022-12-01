import collections as _collections
import json as _json
import logging as _logging
import pathlib as _pathlib
import typing as _typ

from .. import apps as _apps


class Language:
    def __init__(self, code: str, name: str, writing_direction: str, date_format: str, mappings: _typ.Dict[str, str]):
        self.__code = code
        self.__name = name
        self.__writing_direction = writing_direction
        self.__date_format = date_format
        self.__mappings = mappings

    @property
    def code(self) -> str:
        return self.__code

    @property
    def name(self) -> str:
        return self.__name

    @property
    def writing_direction(self) -> str:
        return self.__writing_direction

    @property
    def date_format(self) -> str:
        return self.__date_format

    def translate(self, key: str, default: str = None) -> str:
        return self.__mappings.get(key, default if default is not None else key)


SITE_NAME = 'OpenTrainTrackMap'

DEFAULT_LANGUAGE: str = 'en'
LANGUAGES: _typ.Dict[str, Language] = {}


def init(base_dir: _pathlib.Path):
    global LANGUAGES

    _logging.basicConfig(format=_apps.OTTMConfig.name + ':%(levelname)s:%(message)s', level=_logging.DEBUG)

    _logging.info('Loading translations…')
    langs_dir = base_dir / 'ottm/settings/langs/'
    for fname in langs_dir.glob('*.json'):
        with (langs_dir / fname).open(encoding='UTF-8') as lang_file:
            json_obj = _json.load(lang_file)
            lang_name = json_obj['name']
            lang_code = json_obj['code']
            writing_direction = json_obj['writing_direction']
            date_format = json_obj['date_format']
            mappings = _build_mapping(None, json_obj['mappings'])
            LANGUAGES[lang_code] = Language(lang_code, lang_name, writing_direction, date_format, mappings)
            _logging.info(f'Loaded translations for {lang_name} ({lang_code})')
    _logging.info('Translations loaded.')


def _build_mapping(root: _typ.Optional[str], json_object: _typ.Mapping[str, _typ.Union[str, _typ.Mapping]]) \
        -> _typ.Dict[str, str]:
    mapping = {}

    for k, v in json_object.items():
        if root is not None:
            key = f'{root}.{k}'
        else:
            key = k
        if isinstance(v, str):
            mapping[key] = str(v)
        elif isinstance(v, _collections.Mapping):
            mapping = dict(mapping, **_build_mapping(key, v))
        else:
            raise ValueError(f'illegal value type "{type(v)}" for translation value')

    return mapping
