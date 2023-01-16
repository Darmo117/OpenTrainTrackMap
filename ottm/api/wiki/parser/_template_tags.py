import abc as _abc

from . import _parser_context


class TemplateTag(_abc.ABC):
    def __init__(self, name: str, args_nb: int | tuple[int, int] = 0, standalone: bool = True,
                 *intermediary_tags: tuple[str, int, tuple[int, int]]):
        """Define a template tag.

        :param name: Tag’s name.
        :param args_nb: Number of arguments this tag may take: either an int or a tuple of two ints.
        :param standalone: Whether this tag is standalone, i.e. has no closing tag.
        :param intermediary_tags: Tuples that specify additional intermediary tags in order of appearance.
            Each tuple contains the tag’s name, number of arguments and the min/max number of times it may appear.
        """
        self._name = name
        self._args_nb = (args_nb, args_nb) if isinstance(args_nb, int) else args_nb
        self._standalone = standalone
        self._intermediary_tags = intermediary_tags
        if standalone and intermediary_tags:
            raise ValueError('standalone tags cannot have intermediary tags')

    @property
    def name(self) -> str:
        return self._name

    @property
    def args_nb(self) -> tuple[int, int]:
        return self._args_nb

    @property
    def is_standalone(self) -> bool:
        return self._standalone

    @property
    def intermediary_tags(self) -> tuple[tuple[str, int, tuple[int, int]], ...]:
        return self._intermediary_tags

    def evaluate(self, context: _parser_context.ParserContext, args: list, tag: str = None) -> str | bool:
        """Evaluate this template tag.

        :param context: Current parser context.
        :param args: List of this tag’s arguments as nodes to evaluate.
        :param tag: For tags with intermediary tags, the name of the current sub-tag.
        :return: A string for standalone tags, or a boolean indicating whether the next section
            should be parsed for other tags.
        :raise RuntimeError: If any error happens.
        """
        if not (self.args_nb[0] <= len(args) <= self.args_nb[1]):
            raise RuntimeError()
        return self._evaluate(context, args, tag=tag)

    @_abc.abstractmethod
    def _evaluate(self, context: _parser_context.ParserContext, args: list, tag: str = None) -> str | bool:
        """Evaluate this template tag.

        :param context: Current parser context.
        :param args: List of this tag’s arguments as nodes to evaluate.
        :param tag: For tags with intermediary tags, the name of the current sub-tag.
        :return: A string for standalone tags, or a boolean indicating whether the next section
            should be parsed for other tags.
        :raise RuntimeError: If any error happens.
        """
        pass

    def transform_section(self, context: _parser_context.ParserContext, section: str) -> str:
        """For non-standalone tags, transform this tag’s content."""
        return section


class NoWikiTT(TemplateTag):
    def __init__(self):
        super().__init__('no_wiki', standalone=False)

    def _evaluate(self, context: _parser_context.ParserContext, args: list, tag: str = None) -> bool:
        return False

    def transform_section(self, context: _parser_context.ParserContext, section: str) -> str:
        placeholder = f'`$:!PLACEHOLDER-nowiki-{context.placeholder_index}!:$`'
        context.nowiki_placeholders[placeholder] = section
        context.placeholder_index += 1
        return placeholder


class IncludeOnlyTT(TemplateTag):
    def __init__(self):
        super().__init__('include_only', standalone=False)

    def _evaluate(self, context: _parser_context.ParserContext, args: list, tag: str = None) -> bool:
        return context.transcluding

    def transform_section(self, context: _parser_context.ParserContext, section: str) -> str:
        return section if context.transcluding else ''


class NoIncludeTT(TemplateTag):
    def __init__(self):
        super().__init__('no_include', standalone=False)

    def _evaluate(self, context: _parser_context.ParserContext, args: list, tag: str = None) -> bool:
        return not context.transcluding

    def transform_section(self, context: _parser_context.ParserContext, section: str) -> str:
        return section if not context.transcluding else ''
