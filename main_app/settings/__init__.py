import collections as _collections
import json as _json
import os as _os
import typing as _typ


class Language:
    def __init__(self, code: str, name: str, writing_direction: str, mappings: _typ.Dict[str, str]):
        self.__code = code
        self.__name = name
        self.__writing_direction = writing_direction
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

    def translate(self, key: str, default: str = None) -> str:
        return self.__mappings.get(key, default if default is not None else key)


SITE_NAME = 'OpenTrainTrackMap'

DEFAULT_LANGUAGE: str = 'en'
LANGUAGES: _typ.Dict[str, Language] = {}


def init(base_dir: str):
    global LANGUAGES

    langs_dir = _os.path.join(base_dir, 'main_app/settings/langs/')
    for fname in _os.listdir(langs_dir):
        with open(_os.path.join(langs_dir, fname), mode='r', encoding='UTF-8') as lang_file:
            json_obj = _json.load(lang_file)
            lang_name = json_obj["name"]
            lang_code = json_obj["code"]
            writing_direction = json_obj["writing_direction"]
            mappings = _build_mapping(None, json_obj["mappings"])
            LANGUAGES[lang_code] = Language(lang_code, lang_name, writing_direction, mappings)


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
