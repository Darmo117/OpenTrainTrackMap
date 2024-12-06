"""This package defines the website’s settings."""
import datetime as _dt
import json
import json as _json
import logging as _logging
import pathlib as _pathlib
import re as _re

import markdown as _md

from ..api import data_types as _data_types


class UILanguage:
    """Class representing a language of the site’s UI."""

    def __init__(
            self,
            language,
            comma: str,
            and_word: str,
            day_names: tuple[str, ...],
            abbr_day_names: tuple[str, ...],
            month_names: tuple[str, ...],
            abbr_month_names: tuple[str, ...],
            am_pm: tuple[str, ...],
            day_suffixes: dict[str, str],
            decimal_sep: str,
            thousands_sep: str,
            mappings: dict[str, str],
            js_mappings: dict[str, str],
    ):
        """Create a UI language.

        :param language: Related language instance from the database.
        :type language: ottm.models.Language
        :param comma: The character to use as a comma.
        :param and_word: The word equivalent to english 'and'.
        :param day_names: Names of week days.
        :param abbr_day_names: Abbreviated names of week days.
        :param month_names: Names of months.
        :param abbr_month_names: Abbreviated names of months.
        :param am_pm: AM and PM equivalents for the language.
        :param day_suffixes: Dict that maps regexes to a day suffix.
        :param decimal_sep: Decimal separator.
        :param thousands_sep: Thousands separator.
        :param mappings: Language’s UI translation mappings.
        :param js_mappings: Language’s UI translation JavaScript mappings.
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
        self._comma = comma
        self._and_word = and_word
        self._day_names = day_names
        self._abbr_day_names = abbr_day_names
        self._month_names = month_names
        self._abbr_month_names = abbr_month_names
        # noinspection PyTypeChecker
        self._am_pm: tuple[str, str] = am_pm
        self._day_suffixes: dict[_re.Pattern, str] = {_re.compile(k): v for k, v in day_suffixes.items()}
        self._decimal_sep = decimal_sep
        self._thousands_sep = thousands_sep
        self._mappings = mappings
        self._js_mappings = js_mappings

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
    def comma(self) -> str:
        """The character to use as a comma."""
        return self._comma

    @property
    def and_word(self) -> str:
        """The word equivalent to english 'and'."""
        return self._and_word

    @property
    def day_names(self) -> tuple[str, ...]:
        """Names of week days."""
        return self._day_names

    @property
    def abbr_day_names(self) -> tuple[str, ...]:
        """Abbreviated names of week days."""
        return self._abbr_day_names

    @property
    def month_names(self) -> tuple[str, ...]:
        """Names of months."""
        return self._month_names

    @property
    def abbr_month_names(self) -> tuple[str, ...]:
        """Abbreviated names of months."""
        return self._abbr_month_names

    @property
    def am_pm(self) -> tuple[str, str]:
        """AM and PM equivalents for the language."""
        return self._am_pm

    @property
    def decimal_separator(self) -> str:
        """Thousands separator."""
        return self._decimal_sep

    @property
    def thousands_separator(self) -> str:
        """Language’s UI translation mappings."""
        return self._thousands_sep

    @property
    def default_datetime_format(self) -> str:
        """This language’s default datetime format."""
        return self._language.default_datetime_format.format

    @property
    def js_mappings(self) -> dict[str, str]:
        """A copy of this language’s JavaScript mappings."""
        return dict(self._js_mappings)

    def translate(self, key: str, default: str = None, gender: _data_types.UserGender = None, **kwargs) -> str:
        """Translate the given key.

        :param key: Key to translate.
        :param default: The value to return if the key is not defined.
        :param gender: Gender variant of the requested translation.
        :param kwargs: Translation’s arguments.
        :return: The translated text or the key/default value if it is undefined for the current language.
        """
        text = ''
        if gender:
            text = self._mappings.get(f'{key}.{gender.i18n_label}')
        if not text:
            text = self._mappings.get(key, default if default is not None else key)
        has_several_paragraphs = '\n\n' in text
        text = text.replace('{license-url}', f'https://creativecommons.org/licenses/by-sa/3.0/deed.{self.code}')
        # Parse Markdown before kwargs substitution to avoid formatting them.
        text = _md.markdown(text, output_format='html')
        if not has_several_paragraphs:
            text = text[3:-4]  # Remove enclosing <p> tags if there is a single paragraph
        text = text.format(**kwargs)
        return text

    def format_datetime(self, dt: _dt.datetime, format_: str) -> str:
        """Format a datetime object according to the given format.
        All format codes from ``datetime.strftime()`` are available except ``%c``, ``%x`` and ``%X``.
        Custom ``%s`` code is available for day number prefix.

        :param dt: The datetime object to format.
        :param format_: The desired format.
        :return: The formatted date.
        """
        for c in 'cxX':
            if f'%{c}' in format_:
                raise ValueError(f'illegal format code %{c} in format {format_!r}')
        if '%a' in format_:
            format_ = format_.replace('%a', self._abbr_day_names[dt.weekday()])
        if '%A' in format_:
            format_ = format_.replace('%A', self._day_names[dt.weekday()])
        if '%b' in format_:
            format_ = format_.replace('%b', self._abbr_month_names[dt.month - 1])
        if '%B' in format_:
            format_ = format_.replace('%B', self._month_names[dt.month - 1])
        if '%p' in format_:
            format_ = format_.replace('%p', self._am_pm[dt.hour >= 12])
        if '%s' in format_:
            suffix = ''
            day = str(dt.day)
            for regex, suffix_ in self._day_suffixes.items():
                if regex.search(day):
                    suffix = suffix_
                    break
            format_ = format_.replace('%s', suffix)
        return dt.strftime(format_)

    def format_number(self, n: int | float) -> str:
        """Format a number according to this language’s format.

        :param n: The number to format.
        :return: The formatted number.
        """
        s = str(n)
        dec_part = s.split('.')[1] if '.' in s else ''
        int_part = f'{int(n):,}'.replace(',', self._thousands_sep).replace('-', '−')
        return int_part + (self._decimal_sep + dec_part if dec_part else '')


SITE_NAME = 'OpenTrainTrackMap'
DEFAULT_LANGUAGE_CODE = 'en'
INVALID_TITLE_REGEX = _re.compile(
    r'([_#|{}\[\]\x00-\x1f\x7f-\x9f]|^[:/\s]|[:/\s]$|&[A-Za-z0-9]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;)')
LANGUAGES: dict[str, UILanguage] = {}
LOGGER: _logging.Logger
WIKI_PAGE_CACHE_TTL = 3600  # 1 hour
WIKI_SETUP_USERNAME = 'Wiki Setup'


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
    from .. import data_model  # Local import to avoid loops
    LOGGER.info('Loading translations…')
    langs_dir = _pathlib.Path(__file__).parent / 'langs'
    for language in data_model.Language.objects.filter(available_for_ui=True):
        lang_file = langs_dir / f'{language.code}.json'
        if not lang_file.exists():
            LOGGER.error(f'Missing translation file for language code {language.code}')
            continue
        with lang_file.open(encoding='UTF-8') as f:
            json_obj = _json.load(f)

        mappings_ = json_obj['mappings']
        # Inject OSM feature type translations
        osm_trans_file = langs_dir / f'feature_translations/{language.code}.json'
        if osm_trans_file.exists():
            with osm_trans_file.open(encoding='UTF-8') as f:
                mappings_['js']['osm_feature_type'] = json.load(f)

        mapping = _build_mapping(mappings_)
        js_mappings = {}
        for k, v in list(mapping.items()):
            if k.startswith('js.'):
                js_mappings[k[3:]] = v
                del mapping[k]

        LANGUAGES[language.code] = UILanguage(
            language=language,
            comma=json_obj['comma'],
            and_word=json_obj['and'],
            day_names=tuple(json_obj['day_names']),
            abbr_day_names=tuple(json_obj['abbr_day_names']),
            month_names=tuple(json_obj['month_names']),
            abbr_month_names=tuple(json_obj['abbr_month_names']),
            am_pm=tuple(json_obj['am_pm']),
            day_suffixes=json_obj.get('day_suffixes', {}),
            decimal_sep=json_obj['number_format']['decimal_sep'],
            thousands_sep=json_obj['number_format']['thousands_sep'],
            mappings=mapping,
            js_mappings=js_mappings,
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
