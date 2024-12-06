import abc as _abc
import datetime as _dt
import urllib.parse as _url_parse

from django.conf import settings as _dj_settings
import django.shortcuts as _dj_scut

from . import _parser_context as _pc
from .. import namespaces as _w_ns, pages as _w_pages
from .... import data_model as _models, settings as _settings


class MagicVariable(_abc.ABC):
    """Magic variables are special wikicode constructs that get substituted by a specific value when parsed."""

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
        """Return the value to substitute to this magic variable.

        :param context: Context of the parser calling this magic variable.
        :param args: Optional arguments.
        :return: This magic variable’s value.
        :raise ValueError: If the wrong number of arguments is passed.
        """
        if not (self.params_nb_min <= len(args) <= self.params_nb_max):
            raise ValueError(
                f'invalid parameters number, expected between {self.params_nb_min} and {self.params_nb_max},'
                f' got {len(args)}'
            )
        return self._substitute(context, *args)

    @_abc.abstractmethod
    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        """Return the value to substitute to this magic variable.

        :param context: Context of the parser calling this magic variable.
        :param args: Optional arguments.
        :return: This magic variable’s value.
        """
        pass


# region Date and time


class CurrentYearMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_YEAR')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(context.date.year)


class CurrentMonthMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_MONTH', params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(context.date.month)


class CurrentMonthPaddedMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_MONTH_P', params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return format(context.date.month, '02')


class CurrentWeekMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_WEEK')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return context.date.strftime('%W')


class CurrentDayMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_DAY')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(context.date.day)


class CurrentDayPaddedMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_DAY_P')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return format(context.date.day, '02')


class CurrentDayOfWeekMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_DOW')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(context.date.weekday())


class CurrentTimeMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_TIME')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(context.date.time().strftime('%H:%M'))


class CurrentHourMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_HOUR')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(context.date.time().hour)


class CurrentHourPaddedMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_HOUR_P')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return format(context.date.time().hour, '02')


class CurrentMinuteMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_MINUTE')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(context.date.time().minute)


class CurrentMinutePaddedMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_MINUTE_P')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return format(context.date.time().minute, '02')


class CurrentTimestampMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_TIMESTAMP')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(round(context.date.timestamp()))


class CurrentISODateMV(MagicVariable):
    def __init__(self):
        super().__init__('CURRENT_ISO_DATE')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return context.date.isoformat()


# endregion
# region Technical


class SiteNameMV(MagicVariable):
    def __init__(self):
        super().__init__('SITE_NAME')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return _settings.SITE_NAME


class ServerURLMV(MagicVariable):
    def __init__(self):
        super().__init__('SERVER_URL')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return f'//{_dj_settings.ALLOWED_HOSTS[0]}'


class ServerNameMV(MagicVariable):
    def __init__(self):
        super().__init__('SERVER_NAME')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return _dj_settings.ALLOWED_HOSTS[0]


class WikiPathMV(MagicVariable):
    def __init__(self):
        super().__init__('WIKI_PATH')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return _dj_scut.reverse('ottm:wiki_main_page')


class WikiAPIPathMV(MagicVariable):
    def __init__(self):
        super().__init__('WIKI_API_PATH')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return _dj_scut.reverse('ottm:wiki_api')


class APIPathMV(MagicVariable):
    def __init__(self):
        super().__init__('OTTM_API_PATH')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return _dj_scut.reverse('ottm:api')


class StaticPathMV(MagicVariable):
    def __init__(self):
        super().__init__('OTTM_API_PATH')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return _dj_settings.STATIC_URL


# endregion
# region Page


class _PageMV(MagicVariable, _abc.ABC):
    def __init__(self, name: str):
        super().__init__(name, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        if args:
            page = _w_pages.get_page(*_w_pages.split_title(args[0]))
        else:
            page = context.page
        return self._get_page_info(page)

    @_abc.abstractmethod
    def _get_page_info(self, page: _models.Page) -> str:
        pass


class PageIDMV(_PageMV):
    def __init__(self):
        super().__init__('PAGE_ID')

    def _get_page_info(self, page: _models.Page) -> str:
        return str(page.id) if page.id else ''


class PageLanguageMV(_PageMV):
    def __init__(self):
        super().__init__('PAGE_LANGUAGE')

    def _get_page_info(self, page: _models.Page) -> str:
        return page.content_language.code


class PageProtectionLevelMV(_PageMV):
    def __init__(self):
        super().__init__('PAGE_PROTECTION_LEVEL')

    def _get_page_info(self, page: _models.Page) -> str:
        if pp := page.get_edit_protection():
            return pp.protection_level.label
        return 'all'


class PageProtectionExpiryMV(_PageMV):
    def __init__(self):
        super().__init__('PAGE_PROTECTION_EXPIRY')

    def _get_page_info(self, page: _models.Page) -> str:
        if (pp := page.get_edit_protection()) and pp.end_date:
            return pp.end_date.isoformat()
        return 'infinity'


# endregion
# region Page revisions


class _RevisionMV(MagicVariable, _abc.ABC):
    def __init__(self, name: str):
        super().__init__(name, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        if args:
            page = _w_pages.get_page(*_w_pages.split_title(args[0]))
        else:
            page = context.page
        return self._get_revision_info(page.get_latest_revision(), context)

    @_abc.abstractmethod
    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        pass


class PageRevisionIDMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_ID')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str(revision.id) if revision else ''


class RevisionYearMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_YEAR')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str((revision.date if revision else context.date).year)


class RevisionMonthMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_MONTH')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str((revision.date if revision else context.date).month)


class RevisionMonthPaddedMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_MONTH_P')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return format((revision.date if revision else context.date).month, '02')


class RevisionWeekMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_WEEK')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return (revision.date if revision else context.date).strftime('%W')


class RevisionDayMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_DAY')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str((revision.date if revision else context.date).day)


class RevisionDayPaddedMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_DAY_P')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return format((revision.date if revision else context.date).day, '02')


class RevisionDayOfWeekMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_DOW')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str((revision.date if revision else context.date).weekday())


class RevisionTimeMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_TIME')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str((revision.date if revision else context.date).time().strftime('%H:%M'))


class RevisionHourMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_HOUR')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str((revision.date if revision else context.date).time().hour)


class RevisionHourPaddedMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_HOUR_P')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return format((revision.date if revision else context.date).time().hour, '02')


class RevisionMinuteMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_MINUTE')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str((revision.date if revision else context.date).time().minute)


class RevisionMinutePaddedMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_MINUTE_P')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return format((revision.date if revision else context.date).time().minute, '02')


class RevisionTimestampMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_TIMESTAMP')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str(round((revision.date if revision else context.date).timestamp()))


class RevisionISODateMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_ISO_DATE')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return (revision.date if revision else context.date).isoformat()


class RevisionSizeMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_SIZE')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return str(revision.bytes_size if revision else 0)


class RevisionAuthorMV(_RevisionMV):
    def __init__(self):
        super().__init__('REVISION_AUTHOR')

    def _get_revision_info(self, revision: _models.PageRevision, context: _pc.ParserContext) -> str:
        return revision.author.username if revision else context.user.username


# endregion
# region Page content


class DisplayTitleMV(MagicVariable):
    def __init__(self):
        super().__init__('DISPLAY_TITLE', params_nb_min=1, params_nb_max=2)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        title = args[0]
        match args[1:]:
            case ['no_replace']:
                if not context.display_title:
                    context.display_title = title
            case []:
                if context.display_title:
                    raise RuntimeError(f'{self.name} already set')
                context.display_title = title
            case [v]:
                raise ValueError(f'invalid parameter: {v!r}')
        return ''


class DefaultSortKeyMV(MagicVariable):
    def __init__(self):
        super().__init__('DEFAULT_SORT_KEY', params_nb_min=1, params_nb_max=2)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        sort_key = args[0]
        match args[1:]:
            case ['no_replace']:
                if not context.default_sort_key:
                    context.default_sort_key = sort_key
            case []:
                if context.default_sort_key:
                    raise RuntimeError(f'{self.name} already set')
                context.default_sort_key = sort_key
            case [v]:
                raise ValueError(f'invalid parameter: {v!r}')
        return ''


# endregion
# region Statistics


class NumberOfPagesMV(MagicVariable):
    def __init__(self):
        super().__init__('NUMBER_OF_PAGES')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(_models.Page.objects.count())


class NumberOfArticlesMV(MagicVariable):
    def __init__(self):
        super().__init__('NUMBER_OF_ARTICLES')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        content_namespaces = [ns.id for ns in _w_ns.NAMESPACE_IDS.values() if ns.is_content]
        # Exclude redirection pages
        return str(_models.Page.objects.filter(namespace_id__in=content_namespaces, redirects_to_namespace_id=None,
                                               redirects_to_title=None).count())


class NumberOfFilesMV(MagicVariable):
    def __init__(self):
        super().__init__('NUMBER_OF_FILES')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(_models.Page.objects.filter(namespace_id=_w_ns.NS_FILE.id).count())


class NumberOfEditsMV(MagicVariable):
    def __init__(self):
        super().__init__('NUMBER_OF_EDITS')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(_models.PageRevision.objects.filter(hidden=False).count())


class NumberOfUsersMV(MagicVariable):
    def __init__(self):
        super().__init__('NUMBER_OF_USERS')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        return str(_models.CustomUser.objects.count())


class NumberOfActiveUsersMV(MagicVariable):
    def __init__(self):
        super().__init__('NUMBER_OF_ACTIVE_USERS')

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        # TODO take map edits into account
        date = context.date - _dt.timedelta(days=30)
        return str(_models.CustomUser.objects.filter(pagerevision__date__gte=date).distinct().count())


class PagesInCategoryMV(MagicVariable):
    def __init__(self):
        super().__init__('PAGES_IN_CATEGORY', params_nb_min=1, params_nb_max=2)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        if context.page.namespace == _w_ns.NS_CATEGORY:
            title = args[0]
            match args[1:]:
                case [] | ['all']:
                    return str(_models.PageCategory.objects.filter(cat_title=title).count())
                case ['pages']:
                    return str(_models.PageCategory.pages_for_category(title).count())
                case ['subcats']:
                    return str(_models.PageCategory.subcategories_for_category(title).count())
                case ['files']:
                    return str(_models.PageCategory.pages_for_category(title)
                               .filter(page__namespace_id=_w_ns.NS_FILE.id).count())
                case [v]:
                    raise ValueError(f'invalid filter: {v!r}')
        return ''


class NumberInGroupMV(MagicVariable):
    def __init__(self):
        super().__init__('NUMBER_IN_GROUP', params_nb_min=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        group_label = args[0]
        try:
            return str(_models.UserGroup.objects.get(label=group_label).users.count())
        except _models.UserGroup.DoesNotExist:
            raise ValueError(f'invalid user group: {group_label!r}')


class PagesInNamespaceMV(MagicVariable):
    def __init__(self):
        super().__init__('PAGES_IN_NS', params_nb_min=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        try:
            ns_id = int(args[0])
        except ValueError:
            raise ValueError(f'invalid namespace ID: {args[0]!r}')
        if ns_id not in _w_ns.NAMESPACE_IDS:
            raise ValueError(f'no namespace with ID {ns_id}')
        return str(_models.Page.objects.filter(namespace_id=ns_id).count())


# endregion
# region Page titles


class _PageTitleMV(MagicVariable, _abc.ABC):
    def __init__(self, name: str, encode_url: bool = False):
        super().__init__(name, params_nb_max=1)
        self._encode_url = encode_url

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        s = ''
        match args:
            case []:
                s = self._get_page_title(context.page)
            case [v]:
                s = self._get_page_title(_w_pages.get_page(*_w_pages.split_title(v)))
        if self._encode_url:
            return _url_parse.quote(_w_pages.url_encode_page_title(s))
        return s

    @_abc.abstractmethod
    def _get_page_title(self, page: _models.Page) -> str:
        pass


class FullPageTitleMV(_PageTitleMV):
    def __init__(self):
        super().__init__('FULL_PAGE_TITLE')

    def _get_page_title(self, page: _models.Page) -> str:
        return page.full_title


class PageTitleMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_TITLE')

    def _get_page_title(self, page: _models.Page) -> str:
        return page.title


class PageBaseNameMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_BASE_NAME')

    def _get_page_title(self, page: _models.Page) -> str:
        return page.base_name


class PageParentTitleMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_PARENT_TITLE')

    def _get_page_title(self, page: _models.Page) -> str:
        return page.parent_title


class PageNameMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_NAME')

    def _get_page_title(self, page: _models.Page) -> str:
        return page.page_name


class FullPageTitleURLMV(_PageTitleMV):
    def __init__(self):
        super().__init__('FULL_PAGE_TITLE_U', encode_url=True)

    def _get_page_title(self, page: _models.Page) -> str:
        return page.full_title


class PageTitleURLMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_TITLE_U', encode_url=True)

    def _get_page_title(self, page: _models.Page) -> str:
        return page.title


class PageBaseNameURLMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_BASE_NAME_U', encode_url=True)

    def _get_page_title(self, page: _models.Page) -> str:
        return page.base_name


class PageParentTitleURLMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_PARENT_TITLE_U', encode_url=True)

    def _get_page_title(self, page: _models.Page) -> str:
        return page.parent_title


class PageNameURLMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_NAME_U', encode_url=True)

    def _get_page_title(self, page: _models.Page) -> str:
        return page.page_name


class PagePathMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_PATH')

    def _get_page_title(self, page: _models.Page) -> str:
        return _dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': page.full_title
        })


class PageURLMV(_PageTitleMV):
    def __init__(self):
        super().__init__('PAGE_URL')

    def _get_page_title(self, page: _models.Page) -> str:
        return f'//{_dj_settings.ALLOWED_HOSTS[0]}' + _dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': page.full_title
        })


# endregion
# region Namespaces


class _NamespaceMV(MagicVariable, _abc.ABC):
    def __init__(self, name: str):
        super().__init__(name, params_nb_max=1)

    def _substitute(self, context: _pc.ParserContext, *args: str) -> str:
        match args:
            case []:
                page = context.page
            case [v]:
                page = _w_pages.get_page(*_w_pages.split_title(v))
        # noinspection PyUnboundLocalVariable
        return self._get_namespace_info(page.namespace)

    @_abc.abstractmethod
    def _get_namespace_info(self, namespace: _w_ns.Namespace) -> str:
        pass


class NamespaceNameMV(_NamespaceMV):
    def __init__(self):
        super().__init__('NAMESPACE_NAME')

    def _get_namespace_info(self, namespace: _w_ns.Namespace) -> str:
        return namespace.name


class NamespaceIDMV(_NamespaceMV):
    def __init__(self):
        super().__init__('NAMESPACE_ID')

    def _get_namespace_info(self, namespace: _w_ns.Namespace) -> str:
        return str(namespace.id)


class NamespaceNameURLMV(_NamespaceMV):
    def __init__(self):
        super().__init__('NAMESPACE_NAME_U')

    def _get_namespace_info(self, namespace: _w_ns.Namespace) -> str:
        return _url_parse.quote(_w_pages.url_encode_page_title(namespace.name))

# endregion
