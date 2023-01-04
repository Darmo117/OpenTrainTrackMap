import abc as _abc
import datetime as _dt
import html as _html
import urllib.parse as _url_parse

from . import _parser_context as _pc
from .. import namespaces as _w_ns, pages as _w_pages
from .... import settings as _settings


class ParserFunction:
    """Parser functions are special wikicode constructs that get substituted by a specific value when parsed.
    They differ from magic variables in the sense that they may perform more complex operations and are not
    bound to the current page."""

    def __init__(self, name: str, params_nb_min: int = 0, params_nb_max: int = 0):
        self._name = name
        self._params_nb_min = params_nb_min
        self._params_nb_max = params_nb_max

    @property
    def name(self) -> str:
        return self._name

    @property
    def params_nb_min(self) -> int:
        return self._params_nb_min

    @property
    def params_nb_max(self) -> int:
        return self._params_nb_max

    def substitute(self, context: _pc.ParserContext, *args: str) -> str:
        """Execute this function and return its value.

        :param context: Context of the parser calling this function.
        :param args: Optional arguments.
        :return: This function’s value.
        :raise ValueError: If the wrong number of arguments is passed.
        """
        if not (self.params_nb_min <= len(args) <= self.params_nb_max):
            raise ValueError(
                f'invalid parameters number, expected between {self.params_nb_min} and {self.params_nb_max},'
                f' got {len(args)}'
            )
        return self._substitute(context, *(self.decode_html_entities(arg) for arg in args))

    @_abc.abstractmethod
    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        """Execute this function and return its value.

        :param context: Context of the parser calling this function.
        :param args: Optional arguments.
        :return: This function’s value.
        """
        pass

    @staticmethod
    def decode_html_entities(s: str) -> str:
        return _html.unescape(s)


# region URLs


class URLEncodePF(ParserFunction):
    def __init__(self):
        super().__init__('url_encode', params_nb_min=1, params_nb_max=2)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        s = args[0]
        match args[1:]:
            case []:
                return _url_parse.quote(s)
            case ['query']:
                return _url_parse.quote_plus(s)
            case ['wiki_path']:
                return _url_parse.quote(_w_pages.url_encode_page_title(s))
            case [v]:
                raise ValueError(f'invalid parameter: {v!r}')


class URLDecodePF(ParserFunction):
    def __init__(self):
        super().__init__('url_decode', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return _url_parse.unquote(args[0])


# endregion
# region Namespaces


class NsPF(ParserFunction):
    def __init__(self):
        super().__init__('ns', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        ns_id = int(args[0])
        try:
            return _w_ns.NAMESPACE_IDS[ns_id].name
        except KeyError:
            raise ValueError(f'invalid namespace ID: {ns_id}')


class NsURLPF(ParserFunction):
    def __init__(self):
        super().__init__('ns_url', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        ns_id = int(args[0])
        try:
            return _w_pages.url_encode_page_title(_w_ns.NAMESPACE_IDS[ns_id].name)
        except KeyError:
            raise ValueError(f'invalid namespace ID: {ns_id}')


class NsIDPF(ParserFunction):
    def __init__(self):
        super().__init__('ns_id', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        ns_name = args[0]
        try:
            return str(_w_ns.NAMESPACE_NAMES[ns_name].id)
        except KeyError:
            raise ValueError(f'invalid namespace name: {ns_name!r}')


# endregion
# region Formatting


class FormatNumberPF(ParserFunction):
    def __init__(self):
        super().__init__('format_number', params_nb_min=2, params_nb_max=2)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        raw_value = args[0]
        try:
            n = int(raw_value)
        except ValueError:
            try:
                n = float(raw_value)
            except ValueError:
                raise ValueError(f'{raw_value !r} is not a number')
        lang_code = args[1]
        try:
            formatted_n = _settings.LANGUAGES[lang_code].format_number(n)
        except KeyError:
            raise ValueError(f'invalid language code: {lang_code!r}')
        # language=HTML
        return f'<data value="{n}">{formatted_n}</data>'


class FormatDatePF(ParserFunction):
    def __init__(self):
        super().__init__('format_date', params_nb_min=2, params_nb_max=3)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        raw_date = args[0]
        try:
            date = _dt.datetime.fromisoformat(raw_date)
        except ValueError:
            raise ValueError(f'invalid ISO date: {raw_date!r}')
        lang_code = args[1]
        if len(args) == 3:
            format_ = args[2]
        else:
            format_ = '%y-%m-%dT%H:%M:%S%z'
        try:
            formatted_date = _settings.LANGUAGES[lang_code].format_datetime(date, format_)
        except KeyError:
            raise ValueError(f'invalid language code: {lang_code!r}')
        # language=HTML
        return f'<time datetime="{date.isoformat()}">{formatted_date}</time>'


class LowerCasePF(ParserFunction):
    def __init__(self):
        super().__init__('lc', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[0].lower()


class LowerCaseFirstPF(ParserFunction):
    def __init__(self):
        super().__init__('lc_first', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        if not args[0]:
            return ''
        return args[0][:1].lower() + args[0][1:]


class UpperCasePF(ParserFunction):
    def __init__(self):
        super().__init__('uc', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[0].upper()


class UpperCaseFirstPF(ParserFunction):
    def __init__(self):
        super().__init__('uc_first', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        if not args[0]:
            return ''
        return args[0][:1].upper() + args[0][1:]


class PadLeftPF(ParserFunction):
    def __init__(self):
        super().__init__('pad_left', params_nb_min=2, params_nb_max=3)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[0].rjust(int(args[1]), args[2] if len(args) == 3 else None)


class PadRightPF(ParserFunction):
    def __init__(self):
        super().__init__('pad_right', params_nb_min=2, params_nb_max=3)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[0].ljust(int(args[1]), args[2] if len(args) == 3 else None)


class ReplacePF(ParserFunction):
    def __init__(self):
        super().__init__('replace', params_nb_min=3, params_nb_max=3)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[0].replace(args[1], args[2])


# endregion
# region Localization


class LanguagePF(ParserFunction):
    def __init__(self):
        super().__init__('language', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        lang_code = args[0]
        try:
            return _settings.LANGUAGES[lang_code].name
        except KeyError:
            raise ValueError(f'invalid language code: {lang_code!r}')


# endregion
# region Math


class ExprPF(ParserFunction):
    def __init__(self):
        super().__init__('expr', params_nb_min=1, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        expr = args[0]
        # TODO evaluate
        return ''


# endregion
# region Conditions


class IfPF(ParserFunction):
    def __init__(self):
        super().__init__('if', params_nb_min=3, params_nb_max=3)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[1] if args[0] else args[2]


class IfEqPF(ParserFunction):
    def __init__(self):
        super().__init__('if_eq', params_nb_min=4, params_nb_max=4)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[2] if args[0] == args[1] else args[3]


class IfExprPF(ParserFunction):
    def __init__(self):
        super().__init__('if_expr', params_nb_min=4, params_nb_max=4)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        expr = args[0]
        # TODO evaluate
        return args[1] if 'expr is true' else args[2]


class IfExistsPF(ParserFunction):
    def __init__(self):
        super().__init__('if_exists', params_nb_min=4, params_nb_max=4)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return args[1] if _w_pages.get_page(*_w_pages.split_title(args[0])).exists else args[2]

# TODO switch?

# endregion
