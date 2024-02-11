from __future__ import annotations

import abc as _abc
import typing as _typ

from . import _builtin_modules as _bm, _exceptions as _ex, _types

# Sentinel object which indicates that a statement is not a return
# and that the block statement should thus proceed
NO_RETURN = object()
type StatementResult = tuple[str] | tuple[str, _typ.Any] | NO_RETURN


class Statement(_abc.ABC):
    def __init__(self, line: int, column: int):
        self._line = line
        self._column = column

    @property
    def line(self) -> int:
        return self._line

    @property
    def column(self) -> int:
        return self._column

    @_abc.abstractmethod
    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        pass

    def _unpack_variables(
            self,
            var_names: tuple[str, ...],
            last_takes_rest: bool,
            value: _typ.Any,
            scope: _types.Scope,
            declare_as_const: bool = None,
    ):
        unpacked_values = _types.FunctionClosure.unpack_values(len(var_names), last_takes_rest, iter(value))
        for var_name, v in zip(var_names, unpacked_values):
            if declare_as_const is not None:
                self._declare_variable(var_name, declare_as_const, v, scope)
            else:
                scope.set_variable(var_name, v)

    def _declare_variable(self, name: str, is_const: bool, value, scope: _types.Scope):
        try:
            scope.declare_variable(name, is_const, value)
        except NameError as e:
            raise _ex.WikiScriptException(str(e), self.line, self.column)

    @classmethod
    def _execute_statements(cls, scope: _types.Scope, call_stack: _types.CallStack,
                            statements: tuple[Statement, ...]) -> StatementResult:
        for statement in statements:
            if (result := statement.execute(scope, call_stack)) is not NO_RETURN:
                return result
        return NO_RETURN


class Expression(_abc.ABC):
    def __init__(self, line: int, column: int):
        self._line = line
        self._column = column

    @_abc.abstractmethod
    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        pass

    @property
    def line(self) -> int:
        return self._line

    @property
    def column(self) -> int:
        return self._column


type UnpackExpression = tuple['*', Expression]


##############
# Statements #
##############


class ImportStatement(Statement):
    def __init__(self, line: int, column: int, module_name: str, alias: str | None, builtin: bool):
        super().__init__(line, column)
        if not alias and not builtin:
            raise _ex.WikiScriptException('Missing alias for non-builtin module', line, column)
        self._module_name = module_name
        self._alias = alias
        self._builtin = builtin

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        if self._builtin:
            scope.set_variable(self._alias or self._module_name, _bm.get_module(self._module_name))
        else:
            raise NotImplementedError('load wiki module')  # TODO load wiki module
        return NO_RETURN

    def __repr__(self):
        return f'Import[module_name={self._module_name!r},alias={self._alias!r},builtin={self._builtin}]'


class ExportStatement(Statement):
    def __init__(self, line: int, column: int, names: _typ.Sequence[str]):
        super().__init__(line, column)
        self._ensure_no_duplicates(names)
        self._names = names

    def _ensure_no_duplicates(self, values: _typ.Iterable[str]):
        seen = set()
        for v in values:
            if v in seen:
                raise _ex.WikiScriptException(f'name "{v}" exported multiple times', self.line, self.column)

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        try:
            scope.module.set_exported_names(set(self._names))
        except NameError as e:
            raise _ex.WikiScriptException(str(e), self.line, self.column)
        return NO_RETURN

    def __repr__(self):
        return f'Export[names={self._names!r}]'


class DeclareFunctionStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            name: str,
            args: _typ.Sequence[str],
            default_args: _typ.Sequence[tuple[str, Expression]],
            vararg: bool,
            statements: _typ.Sequence[Statement],
    ):
        super().__init__(line, column)
        if vararg and default_args:
            raise _ex.WikiScriptException('vararg functions cannot have default arguments', line, column)
        self._name = name
        self._arg_names = tuple(args)
        self._default_args = tuple(default_args)
        self.ensure_no_duplicates(self._arg_names + tuple(n for n, _ in self._default_args), line, column)
        self._vararg = vararg
        self._statements = tuple(statements)

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        function = _types.FunctionClosure(
            self._name,
            self._arg_names,
            {name: default.evaluate(scope, call_stack) for name, default in self._default_args},
            self._vararg,
            scope,
            call_stack,
            *self._statements
        )
        self._declare_variable(self._name, False, function, scope)
        return NO_RETURN

    @staticmethod
    def ensure_no_duplicates(values: _typ.Iterable[str], line: int, column: int):
        seen = set()
        for v in values:
            if v in seen:
                raise _ex.WikiScriptException(f'duplicate argument name "{v}"', line, column)

    def __repr__(self):
        return (f'DeclareFunction[name={self._name},args={self._arg_names},vararg={self._vararg},'
                f'default_args={self._default_args},statements={self._statements}]')


class ForLoopStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            variables_names: _typ.Sequence[str],
            last_variable_takes_rest: bool,
            iterator: Expression,
            statements: _typ.Sequence[Statement],
    ):
        super().__init__(line, column)
        self._variables_names = tuple(variables_names)
        self._last_variable_takes_rest = last_variable_takes_rest
        self._iterator = iterator
        self._statements = tuple(statements)

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        scope = scope.push()

        for var_name in self._variables_names:
            self._declare_variable(var_name, False, None, scope)

        for element in self._iterator.evaluate(scope, call_stack):
            scope = scope.push()
            stop = False
            self._unpack_variables(self._variables_names, self._last_variable_takes_rest, element, scope)
            for statement in self._statements:
                match statement.execute(scope, call_stack):
                    case ['break']:
                        stop = True
                        break
                    case ['continue']:
                        break
                    case ['return', result]:
                        return result
            scope = scope.pop()
            if stop:
                break

        return NO_RETURN

    def __repr__(self):
        return (f'ForLoop[variables_names={self._variables_names!r},'
                f'last_var_takes_rest={self._last_variable_takes_rest},'
                f'iterator={self._iterator!r},'
                f'statements={self._statements}]')


class WhileLoopStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            cond: Expression,
            statements: _typ.Sequence[Statement],
    ):
        super().__init__(line, column)
        self._cond = cond
        self._statements = tuple(statements)

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        scope = scope.push()
        cond = self._cond.evaluate(scope, call_stack)
        while cond:
            scope = scope.push()
            stop = False
            for statement in self._statements:
                match statement.execute(scope, call_stack):
                    case ['break']:
                        stop = True
                        break
                    case ['continue']:
                        break
                    case ['return', result]:
                        return result
            scope = scope.pop()
            if stop:
                break
            cond = self._cond.evaluate(scope, call_stack)
        return NO_RETURN

    def __repr__(self):
        return f'WhileLoop[cond={self._cond!r},statements={self._statements}]'


class BreakStatement(Statement):
    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        return ('break',)

    def __repr__(self):
        return f'Break'


class ContinueStatement(Statement):
    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        return ('continue',)

    def __repr__(self):
        return f'Continue'


class IfStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            ifs_statements: _typ.Sequence[tuple[Expression, _typ.Sequence[Statement]]],
            else_statements: _typ.Sequence[Statement],
    ):
        super().__init__(line, column)
        self._ifs_statements = tuple((cond, tuple(statements)) for cond, statements in ifs_statements)
        self._else_statements = tuple(else_statements)

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        for cond, statements in self._ifs_statements:
            if cond.evaluate(scope, call_stack):
                scope = scope.push()
                return self._execute_statements(scope, call_stack, statements)
        else:
            if self._else_statements:
                scope = scope.push()
                value = self._execute_statements(scope, call_stack, self._else_statements)
                return value
        return NO_RETURN

    def __repr__(self):
        return f'If[ifs_stmts={self._ifs_statements},else_stmts={self._else_statements}]'


class TryStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            try_statements: _typ.Sequence[Statement],
            except_parts: _typ.Sequence[tuple[_typ.Sequence[str], str | None, _typ.Sequence[Statement]]],
    ):
        super().__init__(line, column)
        self._try_statements = tuple(try_statements)
        self._except_parts = tuple((types, var_name, tuple(statements)) for types, var_name, statements in except_parts)

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        scope = scope.push()
        try:
            return self._execute_statements(scope, call_stack, self._try_statements)
        except _ex.WikiScriptException:  # Uncatchable from scripts
            raise
        except SyntaxError | OverflowError as e:  # Uncatchable errors
            raise _ex.WikiScriptException(str(e), self.line, self.column)
        except Exception as e:
            for exception_types, var_name, statements in self._except_parts:
                try:
                    ex_classes = tuple(scope.get_variable(ex).value for ex in exception_types)
                except NameError as e:
                    raise _ex.WikiScriptException(str(e), self.line, self.column)
                if any(not isinstance(ex_class, type) or not issubclass(ex_class, BaseException)
                       for ex_class in ex_classes):
                    raise _ex.WikiScriptException(f'except clause only accepts subclasses of BaseException',
                                                  self.line, self.column)
                if isinstance(e, ex_classes):
                    if var_name:
                        # Do not pass actual exception object to avoid potential runtime leaks
                        self._declare_variable(var_name, False, str(e), scope)
                    return self._execute_statements(scope, call_stack, statements)
        return NO_RETURN

    def __repr__(self):
        return f'Try[try_statements={self._try_statements},except_parts={self._except_parts}]'


class ExpressionStatement(Statement):
    def __init__(self, line: int, column: int, expr: Expression):
        super().__init__(line, column)
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        self._expr.evaluate(scope, call_stack)
        return NO_RETURN

    def __repr__(self):
        return f'Expression[expr={self._expr!r}]'


class DeclareVariableStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            names: _typ.Sequence[str],
            last_takes_rest: bool,
            is_const: bool,
            expr: Expression,
    ):
        super().__init__(line, column)
        self._names = tuple(names)
        self._last_takes_rest = last_takes_rest
        self._is_const = is_const
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        value = self._expr.evaluate(scope, call_stack)
        self._unpack_variables(self._names, self._last_takes_rest, value, scope, declare_as_const=self._is_const)
        return NO_RETURN

    def __repr__(self):
        return (f'DeclareVariables[names={self._names!r},last_takes_rest={self._last_takes_rest},'
                f'is_const={self._is_const},value={self._expr!r}]')


class SetVariableStatement(Statement):
    def __init__(self, line: int, column: int, name: str, operator: str, expr: Expression):
        super().__init__(line, column)
        self._name = name
        self._op = operator
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        right_value = self._expr.evaluate(scope, call_stack)
        if self._op == '=':
            try:
                scope.set_variable(self._name, right_value)
            except NameError | TypeError as e:
                raise _ex.WikiScriptException(str(e), self.line, self.column)
            return NO_RETURN

        try:
            value = scope.get_variable(self._name).value
        except NameError as e:
            raise _ex.WikiScriptException(str(e), self.line, self.column)

        match self._op:
            case '**=':
                value **= right_value
            case '*=':
                value *= right_value
            case '/=':
                value /= right_value
            case '//=':
                value //= right_value
            case '%=':
                value %= right_value
            case '+=':
                value += right_value
            case '-=':
                value -= right_value
            case '&=':
                value &= right_value
            case '|=':
                value |= right_value
            case '^=':
                value ^= right_value
            case '<<=':
                value <<= right_value
            case '>>=':
                value >>= right_value
        try:
            scope.set_variable(self._name, value)
        except NameError as e:
            raise _ex.WikiScriptException(str(e), self.line, self.column)
        return NO_RETURN

    def __repr__(self):
        return f'SetVariable[name={self._name!r},op={self._op!r},expr={self._expr!r}]'


class SetVariablesStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            names: _typ.Sequence[str],
            last_takes_rest: bool,
            expr: Expression,
    ):
        super().__init__(line, column)
        self._names = tuple(names)
        self._last_takes_rest = last_takes_rest
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        right_value = self._expr.evaluate(scope, call_stack)
        self._unpack_variables(self._names, self._last_takes_rest, right_value, scope)
        return NO_RETURN

    def __repr__(self):
        return f'SetVariables[names={self._names!r},last_takes_rest={self._last_takes_rest},expr={self._expr!r}]'


class SetPropertyStatement(Statement):
    def __init__(
            self,
            line: int,
            column: int,
            target: Expression,
            property_name: str,
            operator: str,
            expr: Expression,
    ):
        super().__init__(line, column)
        self._target = target
        self._op = operator
        self._property_name = property_name
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        t = self._target.evaluate(scope, call_stack)
        if not GetPropertyExpression.is_attribute_allowed(self._property_name):
            raise GetPropertyExpression.get_error(t, self._property_name)
        v = self._expr.evaluate(scope, call_stack)
        if self._op == '=':
            setattr(t, self._property_name, v)
            return NO_RETURN
        pv = getattr(t, self._property_name)
        match self._op:
            case '**=':
                pv **= v
            case '*=':
                pv *= v
            case '/=':
                pv /= v
            case '//=':
                pv //= v
            case '%=':
                pv %= v
            case '+=':
                pv += v
            case '-=':
                pv -= v
            case '&=':
                pv &= v
            case '|=':
                pv |= v
            case '^=':
                pv ^= v
            case '<<=':
                pv <<= v
            case '>>=':
                pv >>= v
        setattr(t, self._property_name, pv)
        return NO_RETURN

    def __repr__(self):
        return f'SetProperty[target={self._target!r},property={self._property_name!r},op={self._op!r},' \
               f'expr={self._expr!r}]'


class SetItemStatement(Statement):
    def __init__(self, line: int, column: int, target: Expression, key: Expression, operator: str, expr: Expression):
        super().__init__(line, column)
        self._target = target
        self._op = operator
        self._key = key
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        t = self._target.evaluate(scope, call_stack)
        k = self._key.evaluate(scope, call_stack)
        v = self._expr.evaluate(scope, call_stack)
        match self._op:
            case '=':
                t[k] = v
            case '**=':
                t[k] **= v
            case '*=':
                t[k] *= v
            case '/=':
                t[k] /= v
            case '//=':
                t[k] //= v
            case '%=':
                t[k] %= v
            case '+=':
                t[k] += v
            case '-=':
                t[k] -= v
            case '&=':
                t[k] &= v
            case '|=':
                t[k] |= v
            case '^=':
                t[k] ^= v
            case '<<=':
                t[k] <<= v
            case '>>=':
                t[k] >>= v
        return NO_RETURN

    def __repr__(self):
        return f'SetItem[target={self._target!r},key={self._key!r},op={self._op!r},expr={self._expr!r}]'


class RaiseStatement(Statement):
    def __init__(self, line: int, column: int, expr: Expression):
        super().__init__(line, column)
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        v = self._expr.evaluate(scope, call_stack)
        if not isinstance(v, BaseException):
            raise _ex.WikiScriptException('attempt to raise value that is not an instance of BaseException',
                                          self.line, self.column)
        raise v

    def __repr__(self):
        return f'Raise[expr={self._expr!r}]'


class DeleteItemStatement(Statement):
    def __init__(self, line: int, column: int, target: Expression, key: Expression):
        super().__init__(line, column)
        self._target = target
        self._key = key

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        del self._target.evaluate(scope, call_stack)[self._key.evaluate(scope, call_stack)]
        return NO_RETURN

    def __repr__(self):
        return f'DeleteItem[target={self._target!r},key={self._key!r}]'


class ReturnStatement(Statement):
    def __init__(self, line: int, column: int, expr: Expression = None):
        super().__init__(line, column)
        self._expr = expr

    def execute(self, scope: _types.Scope, call_stack: _types.CallStack) -> StatementResult:
        return 'return', self._expr.evaluate(scope, call_stack) if self._expr else None

    def __repr__(self):
        return f'Return[expr={self._expr!r}]'


###############
# Expressions #
###############


class UnaryOperatorExpression(Expression):
    def __init__(
            self,
            line: int,
            column: int,
            symbol: str,
            operator: _typ.Callable[[_typ.Any], _typ.Any],
            expr: Expression,
    ):
        super().__init__(line, column)
        self._symbol = symbol
        self._op = operator
        self._expr = expr

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return self._op(self._expr.evaluate(scope, call_stack))

    def __repr__(self):
        return f'UnaryOp[op={self._symbol!r},expr={self._expr!r}]'


class BinaryOperatorExpression(Expression):
    def __init__(
            self,
            line: int,
            column: int,
            symbol: str,
            operator: _typ.Callable[[_typ.Any, _typ.Any], _typ.Any],
            expr1: Expression,
            expr2: Expression,
    ):
        super().__init__(line, column)
        self._symbol = symbol
        self._op = operator
        self._expr1 = expr1
        self._expr2 = expr2

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        v1 = self._expr1.evaluate(scope, call_stack)
        match self._symbol:
            case 'and':
                if not v1:  # Short circuit
                    return v1
                return self._expr2.evaluate(scope, call_stack)
            case 'or':
                if v1:  # Short circuit
                    return v1
                return self._expr2.evaluate(scope, call_stack)
            case _:
                return self._op(v1, self._expr2.evaluate(scope, call_stack))

    def __repr__(self):
        return f'BinaryOp[op={self._symbol!r},expr1={self._expr1!r},expr2={self._expr2!r}]'


class TernaryOperatorExpression(Expression):
    def __init__(
            self,
            line: int,
            column: int,
            symbol: str,
            operator: _typ.Callable[[_typ.Any, _typ.Any, _typ.Any], _typ.Any],
            expr1: Expression,
            expr2: Expression,
            expr3: Expression,
    ):
        super().__init__(line, column)
        self._symbol = symbol
        self._op = operator
        self._expr1 = expr1
        self._expr2 = expr2
        self._expr3 = expr3

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return self._op(self._expr1.evaluate(scope, call_stack),
                        self._expr2.evaluate(scope, call_stack),
                        self._expr3.evaluate(scope, call_stack))

    def __repr__(self):
        return f'TernaryOp[op={self._symbol!r},expr1={self._expr1!r},expr2={self._expr2!r}]'


class GetVariableExpression(Expression):
    def __init__(self, line: int, column: int, variable_name: str):
        super().__init__(line, column)
        self._variable_name = variable_name

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        try:
            return scope.get_variable(self._variable_name).value
        except NameError as e:
            raise _ex.WikiScriptException(str(e), self.line, self.column)

    def __repr__(self):
        return f'GetVariable[name={self._variable_name!r}]'


class GetPropertyExpression(Expression):
    def __init__(self, line: int, column: int, target: Expression, property_name: str):
        super().__init__(line, column)
        self._target = target
        self._property_name = property_name

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        target = self._target.evaluate(scope, call_stack)
        return self.get_attr(target, self._property_name)

    @classmethod
    def is_attribute_allowed(cls, name: str) -> bool:
        """Check whether the given attribute name is allowed.

        :param name: Attribute name to check.
        :return: True if the name is allowed, False otherwise.
        """
        # Prevent accessing dunder and private attributes
        return not name.startswith('_')

    @classmethod
    def get_attr(cls, o, attr_name: str) -> _typ.Any:
        """Return the value of the specified attribute in object `o`.

        :param o: Object to query.
        :param attr_name: Name of the attribute to get the value of.
        :return: Attribute’s value.
        :raise AttributeError: If the attribute is not allowed or does not exist.
        """
        if not cls.is_attribute_allowed(attr_name):
            raise cls.get_error(o, attr_name)
        try:
            return getattr(o, attr_name)
        except AttributeError:
            raise cls.get_error(o, attr_name)

    @staticmethod
    def get_error(target, attr_name: str) -> AttributeError:
        """Return the AttributeError object for the given object and attribute name.

        :param target: Target object.
        :param attr_name: Attribute name.
        :return: A AttributeError object.
        """
        return AttributeError(f'{type(target).__qualname__!r} object has no attribute {attr_name!r}')

    def __repr__(self):
        return f'GetProperty[target={self._target!r},property={self._property_name!r}]'


class GetItemExpression(Expression):
    def __init__(self, line: int, column: int, target: Expression, key: Expression):
        super().__init__(line, column)
        self._target = target
        self._key = key

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return self._target.evaluate(scope, call_stack)[self._key.evaluate(scope, call_stack)]

    def __repr__(self):
        return f'GetItem[target={self._target!r},key={self._key!r}]'


class DeclareAnonymousFunctionExpression(Expression):
    def __init__(
            self,
            line: int,
            column: int,
            args: _typ.Sequence[str],
            default_args: _typ.Sequence[tuple[str, Expression]],
            vararg: bool,
            statements: _typ.Sequence[Statement],
    ):
        super().__init__(line, column)
        if vararg and default_args:
            raise _ex.WikiScriptException('vararg functions cannot have default arguments', self.line, self.column)
        self._arg_names = tuple(args)
        self._default_args = tuple(default_args)
        DeclareFunctionStatement.ensure_no_duplicates(
            self._arg_names + tuple(n for n, _ in self._default_args), line, column)
        self._vararg = vararg
        self._statements = tuple(statements)

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return _types.FunctionClosure(
            None,
            self._arg_names,
            {name: default.evaluate(scope, call_stack) for name, default in self._default_args},
            self._vararg,
            scope,
            call_stack,
            *self._statements
        )

    def __repr__(self):
        return (f'DefineAnonymousFunction[args={self._arg_names},vararg={self._vararg},'
                f'default_args={self._default_args},statements={self._statements}]')


class FunctionCallExpression(Expression):
    def __init__(self, line: int, column: int, target: Expression, args: _typ.Sequence[Expression | UnpackExpression]):
        super().__init__(line, column)
        self._target = target
        self._args = tuple(args)

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        function = self._target.evaluate(scope, call_stack)
        args = self.unpack_values(self._args, scope, call_stack)
        if isinstance(function, _types.FunctionClosure):
            return function(call_stack, *args)
        return function(*args)

    @staticmethod
    def unpack_values(
            values: _typ.Sequence[Expression | UnpackExpression],
            scope: _types.Scope,
            call_stack: _types.CallStack,
    ) -> list[_typ.Any]:
        vals = []
        for arg in values:
            match arg:
                case ['*', e]:
                    vals.extend(v for v in e.evaluate(scope, call_stack))
                case e:
                    vals.append(e.evaluate(scope, call_stack))
        return vals

    def __repr__(self):
        return f'FunctionCall[target={self._target!r},args={self._args!r}]'


class SimpleLiteralExpression(Expression):
    def __init__(self, line: int, column: int, value):
        super().__init__(line, column)
        self._value = value

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return self._value

    def __repr__(self):
        return repr(self._value)


class DictLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: tuple[Expression, Expression]):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return {k.evaluate(scope, call_stack): v.evaluate(scope, call_stack) for k, v in self._entries}

    def __repr__(self):
        return f'DictLiteral{list(self._entries)!r}'


class ListLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: Expression | UnpackExpression):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return FunctionCallExpression.unpack_values(self._entries, scope, call_stack)

    def __repr__(self):
        return f'ListLiteral{list(self._entries)!r}'


class TupleLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: Expression | UnpackExpression):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return tuple(FunctionCallExpression.unpack_values(self._entries, scope, call_stack))

    def __repr__(self):
        return f'TupleLiteral{list(self._entries)!r}'


class SetLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: Expression | UnpackExpression):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return set(FunctionCallExpression.unpack_values(self._entries, scope, call_stack))

    def __repr__(self):
        return f'SetLiteral{list(self._entries)!r}'


class SliceLiteralExpression(Expression):
    def __init__(
            self,
            line: int,
            column: int,
            start: Expression = None,
            end: Expression = None,
            step: Expression = None,
    ):
        super().__init__(line, column)
        self._start = start
        self._end = end
        self._step = step

    def evaluate(self, scope: _types.Scope, call_stack: _types.CallStack) -> _typ.Any:
        return slice(
            self._start.evaluate(scope, call_stack) if self._start else None,
            self._end.evaluate(scope, call_stack) if self._end else None,
            self._step.evaluate(scope, call_stack) if self._step else None
        )

    def __repr__(self):
        return f'SliceLiteral[start={self._start!r},end={self._end!r},step={self._step!r}]'
