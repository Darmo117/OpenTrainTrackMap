import dataclasses as _dataclasses
import datetime as _dt

from .... import data_model as _models


@_dataclasses.dataclass
class ParserContext:
    placeholder_index: int
    user: _models.User
    page: _models.Page
    revision: _models.Revision | None
    date: _dt.datetime
    display_title: str
    default_sort_key: str
    hidden_category: bool = False
    no_toc: bool = False
    nowiki_placeholders: dict[str, str] = _dataclasses.field(default_factory=lambda: {})
    variables: dict[str, str] = _dataclasses.field(default_factory=lambda: {})
    transcluding: bool = False
