"""This package defines the website’s settings."""
import datetime
import json as _json
import logging as _logging
import math
import pathlib as _pathlib
import re as _re

import markdown


class UILanguage:
    """Class representing a language of the site’s UI."""

    def __init__(
            self,
            language,
            day_names: list[str],
            abbr_day_names: list[str],
            month_names: list[str],
            abbr_month_names: list[str],
            am_pm: tuple[str, str],
            decimal_sep: str,
            thousands_sep: str,
            mappings: dict[str, str],
    ):
        """Create a UI language.

        :param language: Related language instance from the database.
        :type language: ottm.models.Language
        :param day_names: Names of week days.
        :param abbr_day_names: Abbreviated names of week days.
        :param month_names: Names of months.
        :param abbr_month_names: Abbreviated names of months.
        :param am_pm: AM and PM equivalents for the language.
        :param mappings: Language’s UI translation mappings.
        """
        if len(day_names) != 7:
            raise ValueError('day_names expected 7 values')
        if len(abbr_day_names) != 7:
            raise ValueError('abbr_day_names expected 7 values')
        if len(month_names) != 12:
            raise ValueError('month_names expected 12 values')
        if len(abbr_month_names) != 12:
            raise ValueError('abbr_month_names expected 12 values')
        if len(am_pm) != 2:
            raise ValueError('am_pm expected 2 values')
        self._language = language
        self._day_names = day_names
        self._abbr_day_names = abbr_day_names
        self._month_names = month_names
        self._abbr_month_names = abbr_month_names
        self._am_pm = am_pm
        self._decimal_sep = decimal_sep
        self._thousands_sep = thousands_sep
        self._mappings = mappings

    @property
    def internal_language(self):
        """The underlying language instance.

        :rtype: ottm.models.Language
        """
        return self._language

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
    def default_datetime_format(self) -> str:
        """This language’s default datetime format."""
        return self._language.default_datetime_format.format

    def translate(self, key: str, default: str = None, /, **kwargs) -> str:
        """Translate the given key.

        :param key: Key to translate.
        :param default: The value to return if the key is not defined.
        :param kwargs: Translation’s arguments.
        :return: The translated text or the key/default value if it is undefined for the current language.
        """
        text = self._mappings.get(key, default if default is not None else key)
        has_several_paragraphs = '\n\n' in text
        text = text.replace('{license-url}', f'https://creativecommons.org/licenses/by-sa/3.0/deed.{self.code}')
        # Parse Markdown before kwargs substitution to avoid formatting them.
        text = markdown.markdown(text, output_format='html')
        if not has_several_paragraphs:
            text = text[3:-4]  # Remove enclosing <p> tags if there is a single paragraph
        text = text.format(**kwargs)
        return text

    def format_datetime(self, dt: datetime.datetime, format_: str) -> str:
        """Format a datetime object according to the given format.
        All format codes from ``datetime.strftime()`` are available except ``%c``, ``%x`` and ``%X``.

        :param dt: The datetime object to format.
        :param format_: The desired format.
        :return: The formatted date.
        """
        for c in 'cxX':
            if f'%{c}' in format_:
                raise ValueError(f'illegal format code %{c} in format {format_!r}')
        if '%a' in format_:
            format_ = format_.replace('%a', self._day_names[dt.weekday()])
        if '%A' in format_:
            format_ = format_.replace('%A', self._abbr_day_names[dt.weekday()])
        if '%b' in format_:
            format_ = format_.replace('%b', self._month_names[dt.weekday()])
        if '%B' in format_:
            format_ = format_.replace('%B', self._abbr_month_names[dt.weekday()])
        if '%p' in format_:
            format_ = format_.replace('%p', self._am_pm[dt.hour == 0 or dt.hour > 12])
        return dt.strftime(format_)

    def format_number(self, n: int | float) -> str:
        """Format a number according to this language’s format.

        :param n: The number to format.
        :return: The formatted number.
        """
        s = str(n)
        dec_part = s.split('.')[1] if '.' in s else ''
        int_part = ('{:,}'.format(math.floor(n))).replace(',', self._thousands_sep)
        return int_part + (self._decimal_sep + dec_part if dec_part else '')


SITE_NAME = 'OpenTrainTrackMap'
DEFAULT_LANGUAGE_CODE = 'en'
INVALID_TITLE_REGEX = _re.compile(
    r'([_#|{}\[\]\x00-\x1f\x7f-\x9f]|^[:/\s]|[:/\s]$|&[A-Za-z0-9]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;)')
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
            json_obj = _json.load(lang_file)
            LANGUAGES[language.code] = UILanguage(
                language=language,
                day_names=json_obj['day_names'],
                abbr_day_names=json_obj['abbr_day_names'],
                month_names=json_obj['month_names'],
                abbr_month_names=json_obj['abbr_month_names'],
                am_pm=json_obj['am_pm'],
                decimal_sep=json_obj['number_format']['decimal_sep'],
                thousands_sep=json_obj['number_format']['thousands_sep'],
                mappings=_build_mapping(json_obj['mappings']),
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
