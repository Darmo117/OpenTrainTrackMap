import dataclasses as _dataclasses
import datetime as _dt

from .... import models as _models, settings as _settings


@_dataclasses.dataclass
class ParserContext:
    user: _models.User
    page: _models.Page
    revision: _models.Revision | None
    date: _dt.datetime
    language: _settings.UILanguage
    display_title: str
    default_sort_key: str
