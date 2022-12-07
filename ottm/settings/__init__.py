"""This package defines the website’s settings."""
import json as _json
import logging as _logging
import pathlib as _pathlib
import re as _re


class UILanguage:
    """Class representing a language of the site’s UI."""

    def __init__(self, language, mappings: dict[str, str]):
        """Create a UI language.

        :param language: Related language instance from the database.
        :type language: ottm.models.Language
        :param mappings: Language’s UI translation mappings.
        """
        self._language = language
        self._mappings = mappings

    @property
    def code(self) -> str:
        """This language’s code."""
        return self._language.code

    @property
    def name(self) -> str:
        """This language’s name."""
        return self._language.name

    @property
    def writing_direction(self) -> str:
        """This language’s writing direction."""
        return self._language.writing_direction

    @property
    def date_format(self) -> str:
        """This language’s date format."""
        return self._language.date_format

    def translate(self, key: str, default: str = None, /, **kwargs) -> str:
        """Translate the given key.

        :param key: Key to translate.
        :param default: The value to return if the key is not defined.
        :param kwargs: Translation’s arguments.
        :return: The translated text or the key/default value if it is undefined for the current language.
        """
        return self._mappings.get(key, default if default is not None else key).format(**kwargs)


SITE_NAME = 'OpenTrainTrackMap'
DEFAULT_LANGUAGE_CODE = 'en'
INVALID_TITLE_REGEX = _re.compile(
    r'([%<>_#|{}\[\]\x00-\x1f\x7f-\x9f]|^[/\s]|[/\s]$|&[A-Za-z0-9]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;)')
LANGUAGES: dict[str, UILanguage] = {}
LOGGER: _logging.Logger


def init(debug: bool):
    """Initialize the settings.

    :param debug: Whether the website is in debug mode or not.
    """
    global LOGGER, LANGUAGES

    LOGGER = _logging.Logger('OTTM', level=_logging.DEBUG if debug else _logging.INFO)
    sh = _logging.StreamHandler()
    sh.setFormatter(_logging.Formatter('%(name)s:%(levelname)s:%(message)s'))
    LOGGER.addHandler(sh)


def init_languages():
    """Initialize UI languages."""
    from .. import models  # Local import to avoid loops
    LOGGER.info('Loading translations…')
    for language in models.Language.objects.filter(available_for_ui=True):
        lang_file = _pathlib.Path(__file__).parent / 'langs' / f'{language.code}.json'
        if not lang_file.exists():
            LOGGER.error(f'Missing translation file for language code {language.code}')
            continue
        with lang_file.open(encoding='utf8') as lang_file:
            LANGUAGES[language.code] = UILanguage(
                language=language,
                mappings=_build_mapping(_json.load(lang_file)),
            )
            LOGGER.info(f'Loaded translations for {language.name} ({language.code})')
    LOGGER.info('Translations loaded.')


def _build_mapping(json_object: dict[str, str | dict], root: str = None) -> dict[str, str]:
    """Build translation mappings for the given JSON dict.

    Example:
        A JSON dict of the form ``{"a": {"b": "c"}}`` will result in the mappings ``{"a.b": "c"}``.

    :param json_object: A dict object containing translations defined in a JSON language file.
    :param root: The root translation key prefix. May be None.
    :return: A flat dict containing the mappings.
    """
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
