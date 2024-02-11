import operator as _op
import pathlib as _pl
import re as _re
import typing as _typ

import lark as _lark

from . import _exceptions as _ex, _syntax_tree as _st, _types

type UnpackedVars = tuple[list[str], bool, tuple[int, int]]


# noinspection PyMethodMayBeStatic
class WikiScriptParser(_lark.Transformer):
    KEYWORDS = (
        'const', 'var',
        'not', 'is', 'in', 'and', 'or',
        'import', 'as', 'export',
        'function', 'end',
        'for', 'while', 'do',
        'break', 'continue',
        'if', 'then', 'elif', 'else',
        'try', 'except',
        'raise',
        'del',
        'return',
        'True', 'False', 'None',
    )
    UNARY_OPS: dict[str, _typ.Callable[[_typ.Any], _typ.Any]] = {
        '-': _op.neg,
        '~': _op.inv,
        '!': _op.not_,
    }
    BINARY_OPS: dict[str, _typ.Callable[[_typ.Any, _typ.Any], _typ.Any]] = {
        '**': _op.pow,
        '*': _op.mul,
        '/': _op.truediv,
        '//': _op.floordiv,
        '%': _op.mod,
        '+': _op.add,
        '-': _op.sub,
        '&': _op.and_,
        '|': _op.or_,
        '^': _op.xor,
        '<<': _op.lshift,
        '>>': _op.rshift,
        'is': _op.is_,
        'is not': _op.is_not,
        'in': lambda a, b: a in b,
        'not in': lambda a, b: a not in b,
        '==': _op.eq,
        '!=': _op.ne,
        '>': _op.gt,
        '>=': _op.ge,
        '<': _op.lt,
        '<=': _op.le,
        'and': lambda a, b: a and b,
        'or': lambda a, b: a or b,
    }
    TERNARY_OPS: dict[str, _typ.Callable[[_typ.Any, _typ.Any, _typ.Any], _typ.Any]] = {
        'if else': lambda a, b, c: a if b else c,
    }

    def __init__(self, module_name: str):
        super().__init__()
        self._module_name = module_name
        self._parser = _lark.Lark(grammar=_GRAMMAR, start='module', parser='lalr', propagate_positions=True)

    def parse(self, code: str) -> _lark.Tree:
        try:
            return self._parser.parse(code)
        except _lark.exceptions.LarkError as e:
            # TODO better error messages
            raise ValueError(e)

    def transform(self, tree: _lark.Tree) -> _types.Module:
        return super().transform(tree)

    def module(self, tokens) -> _types.Module:
        return _types.Module(self._module_name, tokens)

    # Statements

    def import_builtin_stmt(self, tokens) -> _st.ImportStatement:
        keyword, name, *alias = tokens
        return _st.ImportStatement(
            keyword.line,
            keyword.column,
            self._ident(name),
            alias=self._ident(alias[0]) if alias else None,
            builtin=True,
        )

    def import_wiki_module_stmt(self, tokens) -> _st.ImportStatement:
        keyword, name, alias = tokens
        return _st.ImportStatement(
            keyword.line,
            keyword.column,
            name,
            alias=self._ident(alias),
            builtin=False,
        )

    def export_stmt(self, tokens) -> _st.ExportStatement:
        keyword, *names = tokens
        return _st.ExportStatement(keyword.line, keyword.column, [self._ident(n) for n in names])

    def decl_function_stmt(self, tokens) -> _st.DeclareFunctionStatement:
        keyword = tokens[0]
        name = tokens[1]
        statements = []
        args, vararg, default_args = [], False, []
        for token in tokens[2:]:
            match token:
                case [list(args_), list(def_args), bool(var_arg)]:
                    args = args_
                    vararg = var_arg
                    default_args = def_args
                case s:
                    statements.append(s)
        return _st.DeclareFunctionStatement(
            keyword.line,
            keyword.column,
            self._ident(name),
            args,
            default_args,
            vararg,
            statements,
        )

    def decl_function_params(self, tokens) -> tuple[list[str], list[tuple[str, _typ.Any]], bool]:
        args, vararg, default_args = [], False, []
        for token in tokens:
            match token:
                case ['*', str(name)]:
                    args.append(self._ident(name))
                    vararg = True
                case [str(name), default]:
                    default_args.append((name, default))
                case name:
                    args.append(self._ident(name))
        return args, default_args, vararg

    def decl_function_default_arg(self, tokens) -> tuple[str, _typ.Any]:
        return self._ident(tokens[0]), tokens[1]

    def for_loop_stmt(self, tokens) -> _st.ForLoopStatement:
        keyword, (variables, last_takes_rest, _), iterator, *statements = tokens
        return _st.ForLoopStatement(
            keyword.line,
            keyword.column,
            variables_names=variables,
            last_variable_takes_rest=last_takes_rest,
            iterator=iterator,
            statements=statements,
        )

    def while_loop_stmt(self, tokens) -> _st.WhileLoopStatement:
        keyword, cond, *statements = tokens
        return _st.WhileLoopStatement(keyword.line, keyword.column, cond=cond, statements=statements)

    def break_stmt(self, tokens) -> _st.BreakStatement:
        keyword, = tokens
        return _st.BreakStatement(keyword.line, keyword.column)

    def continue_stmt(self, tokens) -> _st.ContinueStatement:
        keyword, = tokens
        return _st.ContinueStatement(keyword.line, keyword.column)

    def if_stmt(self, tokens) -> _st.IfStatement:
        keyword = tokens[0]
        ifs = [tokens[1]]
        else_ = []
        for token in tokens[2:]:
            match token:
                case ['elif', cond, statements]:
                    ifs.append((cond, statements))
                case ['else', statements]:
                    else_ = statements
        return _st.IfStatement(keyword.line, keyword.column, ifs, else_)

    def if_stmt_if_part(self, tokens) -> tuple[_st.Expression, list[_st.Statement]]:
        cond, *statements = tokens
        return cond, statements

    def if_stmt_elif_part(self, tokens) -> tuple[str, _st.Expression, list[_st.Statement]]:
        cond, *statements = tokens
        return 'elif', cond, statements

    def if_stmt_else_part(self, tokens) -> tuple[str, list[_st.Statement]]:
        return 'else', list(tokens)

    def try_stmt(self, tokens) -> _st.TryStatement:
        keyword, try_statements, *except_parts = tokens
        return _st.TryStatement(keyword.line, keyword.column, try_statements, except_parts)

    def try_stmt_try_part(self, tokens) -> list[_st.Statement]:
        return list(tokens)

    def try_stmt_except_part(self, tokens) -> tuple[list[str], str | None, list[_st.Statement]]:
        names = []
        alias = None
        statements = []
        for token in tokens:
            match token:
                case ['as', str(s)]:
                    alias = s
                case t if isinstance(t, _lark.Token):
                    names.append(self._ident(t))
                case statement:
                    statements.append(statement)
        return names, alias, statements

    def try_stmt_except_alias_part(self, tokens) -> tuple[str, str]:
        name, = tokens
        return 'as', self._ident(name)

    def decl_var_stmt(self, tokens) -> _st.DeclareVariableStatement:
        keyword, ((var_names, vararg, _), expr) = tokens
        return _st.DeclareVariableStatement(
            keyword.line,
            keyword.column,
            names=var_names,
            last_takes_rest=vararg,
            is_const=str(keyword) == 'const',
            expr=expr,
        )

        # Common

    def set_variable_stmt(self, tokens) -> _st.SetVariableStatement | _st.SetVariablesStatement:
        match tokens:
            case [str(name), str(op), expr, [int(line), int(column)]]:
                return _st.SetVariableStatement(line, column, name, op, expr)
            case [[list(names), bool(vararg), [int(line), int(column)]], expr]:
                return _st.SetVariablesStatement(line, column, names, vararg, expr)

    def set_single_var_stmt(self, tokens) -> tuple[str, str, _st.Expression, tuple[int, int]]:
        name, op, expr = tokens
        return self._ident(name), op, expr, (name.line, name.column)

    def set_multiple_vars_stmt(self, tokens) -> tuple[UnpackedVars, _st.Expression]:
        unpacked_var_names, expr = tokens
        return unpacked_var_names, expr

    def expr_stmt(self, tokens) -> _st.ExpressionStatement:
        expr, = tokens
        return _st.ExpressionStatement(expr.line, expr.column, expr)

    def set_property_stmt(self, tokens) -> _st.SetPropertyStatement:
        target, name, op, expr = tokens
        return _st.SetPropertyStatement(
            target.line,
            target.column,
            target=target,
            property_name=self._ident(name),
            operator=str(op),
            expr=expr,
        )

    def set_item_stmt(self, tokens) -> _st.SetItemStatement:
        target, key, op, expr = tokens
        return _st.SetItemStatement(
            target.line,
            target.column,
            target=target,
            key=key,
            operator=str(op),
            expr=expr,
        )

    def raise_stmt(self, tokens) -> _st.RaiseStatement:
        keyword, expr = tokens
        return _st.RaiseStatement(keyword.line, keyword.column, expr)

    def delete_item_stmt(self, tokens) -> _st.DeleteItemStatement:
        keyword, target, key = tokens
        return _st.DeleteItemStatement(keyword.line, keyword.column, target, key)

    def return_stmt(self, tokens) -> _st.ReturnStatement:
        keyword, *expr = tokens
        return _st.ReturnStatement(keyword.line, keyword.column, expr[0] if expr else None)

    # Expressions

    def ternary_op(self, tokens) -> _st.TernaryOperatorExpression:
        expr1, expr2, expr3 = tokens
        return _st.TernaryOperatorExpression(
            expr1.line,
            expr1.column,
            symbol='ifelse',
            operator=self.TERNARY_OPS['ifelse'],
            expr1=expr1,
            expr2=expr2,
            expr3=expr3,
        )

    def binary_op(self, tokens) -> _st.BinaryOperatorExpression:
        match tokens:
            case [e1, o, e2]:
                expr1 = e1
                op = str(o)
                expr2 = e2
            case [e1, o1, o2, e2]:
                expr1 = e1
                op = f'{o1} {o2}'
                expr2 = e2
            case _:
                raise ValueError(f'invalid tokens: {tokens}')
        return _st.BinaryOperatorExpression(
            expr1.line,
            expr1.column,
            symbol=op,
            operator=self.BINARY_OPS[op],
            expr1=expr1,
            expr2=expr2,
        )

    def unary_op(self, tokens) -> _st.UnaryOperatorExpression:
        op, expr = tokens
        return _st.UnaryOperatorExpression(
            op.line,
            op.column,
            symbol=str(op),
            operator=self.UNARY_OPS[str(op)],
            expr=expr,
        )

    def get_variable(self, tokens) -> _st.GetVariableExpression:
        name, = tokens
        return _st.GetVariableExpression(name.line, name.column, self._ident(name))

    def get_property(self, tokens) -> _st.GetPropertyExpression:
        target, name = tokens
        return _st.GetPropertyExpression(target.line, target.column, target=target, property_name=self._ident(name))

    def get_item(self, tokens) -> _st.GetItemExpression:
        target, key = tokens
        return _st.GetItemExpression(target.line, target.column, target, key)

    def function_call(self, tokens) -> _st.FunctionCallExpression:
        target, *args = tokens
        return _st.FunctionCallExpression(target.line, target.column, target, args)

    def decl_anon_function(self, tokens) -> _st.DeclareAnonymousFunctionExpression:
        keyword = tokens[0]
        statements = []
        args, vararg, default_args = [], False, []
        for token in tokens[1:]:
            match token:
                case [list(args_), list(def_args), bool(var_arg)]:
                    args = args_
                    vararg = var_arg
                    default_args = def_args
                case s:
                    statements.append(s)
        return _st.DeclareAnonymousFunctionExpression(
            keyword.line,
            keyword.column,
            args,
            default_args,
            vararg,
            statements,
        )

    def string_lit(self, token) -> _st.SimpleLiteralExpression:
        literal, = token
        return _st.SimpleLiteralExpression(
            literal.line,
            literal.column,
            self._subst_escape_sequences(str(literal)[1:-1])
        )

    def multiline_string_lit(self, token) -> _st.SimpleLiteralExpression:
        literal, = token
        return _st.SimpleLiteralExpression(
            literal.line,
            literal.column,
            self._subst_escape_sequences(str(literal)[1:-1], multiline=True),
        )

    def _subst_escape_sequences(self, s: str, multiline: bool = False) -> str:
        def repl(m: _re.Match) -> str:
            match m.groups():
                case [str(v), None, None]:  # \\, \n, \t, \", \' and \`
                    return {
                        '\\': '\\',
                        'n': '\n',
                        't': '\t',
                        '"': '"',
                        "'": "'",
                        '`': '`',
                    }[v]
                case [None, str(v), None] | [None, None, str(v)]:  # \uXXXX and \uXXXXXXXX
                    return chr(int(v, 16))
                case [None, None, None]:  # \ at the end of a line
                    return ''

        if multiline:
            return _re.sub(r'\\(?:([\\nt\'"`])|u([\da-fA-F]{4})|U([\da-fA-F]{8})|\n[ \t]*)', repl, s)
        return _re.sub(r'\\(?:([\\nt\'"`])|u([\da-fA-F]{4})|U([\da-fA-F]{8}))', repl, s)

    def int_lit(self, tokens) -> _st.SimpleLiteralExpression:
        literal, = tokens
        string = str(literal)
        if string.startswith('0x'):
            nb = int(string, 16)
        elif string.startswith('0o'):
            nb = int(string, 8)
        elif string.startswith('0b'):
            nb = int(string, 2)
        else:
            nb = int(string)
        return _st.SimpleLiteralExpression(literal.line, literal.column, nb)

    def float_lit(self, tokens) -> _st.SimpleLiteralExpression:
        literal = tokens[0]
        return _st.SimpleLiteralExpression(literal.line, literal.column, float(str(literal)))

    def boolean_true(self, tokens) -> _st.SimpleLiteralExpression:
        keyword, = tokens
        return _st.SimpleLiteralExpression(keyword.line, keyword.column, True)

    def boolean_false(self, tokens) -> _st.SimpleLiteralExpression:
        keyword, = tokens
        return _st.SimpleLiteralExpression(keyword.line, keyword.column, False)

    def none_lit(self, tokens) -> _st.SimpleLiteralExpression:
        keyword, = tokens
        return _st.SimpleLiteralExpression(keyword.line, keyword.column, None)

    def list_lit(self, tokens) -> _st.ListLiteralExpression:
        bracket, *values = tokens
        return _st.ListLiteralExpression(bracket.line, bracket.column, *values)

    def tuple_lit(self, tokens) -> _st.TupleLiteralExpression:
        parenthesis, *values = tokens
        return _st.TupleLiteralExpression(parenthesis.line, parenthesis.column, *values)

    def set_lit(self, tokens) -> _st.SetLiteralExpression:
        curly_brace, *values = tokens
        return _st.SetLiteralExpression(curly_brace.line, curly_brace.column, *values)

    def dict_lit(self, tokens) -> _st.DictLiteralExpression:
        curly_brace, *entries = tokens
        return _st.DictLiteralExpression(curly_brace.line, curly_brace.column, *[(k, v) for k, v in entries])

    def dict_entry(self, tokens) -> tuple[_st.Expression, _st.Expression]:
        key, value = tokens
        return key, value

    # Common

    def unpack_values(self, tokens) -> UnpackedVars:
        line_col = None
        var_names = []
        vararg = False
        for token in tokens:
            match token:
                case ['*', str(name)]:
                    var_names.append(name)
                    vararg = True
                case name:
                    var_names.append(self._ident(name))
                    line_col = (name.line, name.column)
        return var_names, vararg, line_col

    def unpack_value(self, tokens) -> tuple[str, _st.Expression]:
        value, = tokens
        return '*', value

    def remaining_values(self, tokens) -> tuple[str, str]:
        name, = tokens
        return '*', self._ident(name)

    def slice_both(self, tokens) -> _st.SliceLiteralExpression:
        expr1, expr2, *expr3 = tokens
        return _st.SliceLiteralExpression(
            expr1.line,
            expr1.column,
            start=expr1,
            end=expr2,
            step=expr3[0] if expr3 else None,
        )

    def slice_end(self, tokens) -> _st.SliceLiteralExpression:
        colon, expr1, *expr2 = tokens
        return _st.SliceLiteralExpression(
            colon.line,
            colon.column,
            end=expr1,
            step=expr2[0] if expr2 else None,
        )

    def slice_start(self, tokens) -> _st.SliceLiteralExpression:
        expr1, *expr2 = tokens
        return _st.SliceLiteralExpression(
            expr1.line,
            expr1.column,
            start=expr1,
            step=expr2[0] if expr2 else None,
        )

    def slice_none(self, tokens) -> _st.SliceLiteralExpression:
        colon, *expr = tokens
        return _st.SliceLiteralExpression(colon.line, colon.column, step=expr[0] if expr else None)

    def _ident(self, token: _lark.Token) -> str:
        name = str(token)
        if name in self.KEYWORDS:
            raise _ex.WikiScriptException(f'invalid identifier: {name!r}', token.line, token.column)
        return name


_GRAMMAR = ''


def _init():
    global _GRAMMAR
    with (_pl.Path(__file__).parent / 'wiki_script.lark').open() as f:
        _GRAMMAR = f.read()


_init()
