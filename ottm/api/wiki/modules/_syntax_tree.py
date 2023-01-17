import abc as _abc
import typing as _typ

from . import _scope, _types, _exceptions as _ex


# TODO wrap all exceptions in WikiScriptException


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
    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str] | tuple[str, _typ.Any] | None:
        pass


class Expression(_abc.ABC):
    def __init__(self, line: int, column: int):
        self._line = line
        self._column = column

    @_abc.abstractmethod
    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        pass

    @property
    def line(self) -> int:
        return self._line

    @property
    def column(self) -> int:
        return self._column


##############
# Statements #
##############


class ExpressionStatement(Statement):
    def __init__(self, line: int, column: int, expr: Expression):
        super().__init__(line, column)
        self._expr = expr

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        self._expr.evaluate(scope, call_stack)

    def __repr__(self):
        return f'Expression[expr={self._expr!r}]'


class UnpackVariablesStatement(Statement):
    def __init__(self, line: int, column: int, names: list[str], expr: Expression):
        super().__init__(line, column)
        self._names = names
        self._expr = expr

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        sequence = self._expr.evaluate(scope, call_stack)
        left_len = len(self._names)
        right_len = len(sequence)
        if left_len < right_len:
            raise _ex.WikiScriptException(f'too many values to unpack (expected {right_len})', self.line, self.column)
        if left_len > right_len:
            raise _ex.WikiScriptException(f'not enough values to unpack (expected {left_len})', self.line, self.column)
        for i, value in enumerate(sequence):
            scope.set_variable(self._names[i], value)

    def __repr__(self):
        return f'UnpackVariables[names={self._names},expr={self._expr!r}]'


class SetVariableStatement(Statement):
    def __init__(self, line: int, column: int, name: str, operator: str, expr: Expression):
        super().__init__(line, column)
        self._name = name
        self._op = operator
        self._expr = expr

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        new_value = self._expr.evaluate(scope, call_stack)
        if self._op == '=':
            scope.set_variable(self._name, new_value)
            return

        try:
            value = scope.get_variable(self._name, current_only=True).value
        except NameError as e:
            raise _ex.WikiScriptException(str(e), self.line, self.column) from None

        match self._op:
            case '**=':
                value **= new_value
            case '*=':
                value *= new_value
            case '/=':
                value /= new_value
            case '//=':
                value //= new_value
            case '%=':
                value %= new_value
            case '+=':
                value += new_value
            case '-=':
                value -= new_value
            case '&=':
                value &= new_value
            case '|=':
                value |= new_value
            case '^=':
                value ^= new_value
            case '<<=':
                value <<= new_value
            case '>>=':
                value >>= new_value
        scope.set_variable(self._name, value)

    def __repr__(self):
        return f'SetVariable[name={self._name!r},op={self._op!r},expr={self._expr!r}]'


class SetPropertyStatement(Statement):
    def __init__(self, line: int, column: int, target: Expression, property_name: str, operator: str, expr: Expression):
        super().__init__(line, column)
        self._target = target
        self._op = operator
        self._property_name = property_name
        self._expr = expr

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        t = self._target.evaluate(scope, call_stack)
        if not GetPropertyExpression.is_attribute_allowed(self._property_name):
            raise GetPropertyExpression.get_error(t, self._property_name)
        v = self._expr.evaluate(scope, call_stack)
        if self._op == '=':
            setattr(t, self._property_name, v)
            return
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

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
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

    def __repr__(self):
        return f'SetItem[target={self._target!r},key={self._key!r},op={self._op!r},expr={self._expr!r}]'


class DeleteVariableStatement(Statement):
    def __init__(self, line: int, column: int, name: str):
        super().__init__(line, column)
        self._var_name = name

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        scope.delete_variable(self._var_name)

    def __repr__(self):
        return f'DeleteVariable[name={self._var_name!r}]'


class DeleteItemStatement(Statement):
    def __init__(self, line: int, column: int, target: Expression, key: Expression):
        super().__init__(line, column)
        self._target = target
        self._key = key

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        del self._target.evaluate(scope, call_stack)[self._key.evaluate(scope, call_stack)]

    def __repr__(self):
        return f'DeleteItem[target={self._target!r},key={self._key!r}]'


class TryStatement(Statement):
    def __init__(self, line: int, column: int, try_statements: list[Statement],
                 except_parts: list[tuple[list[Expression], str | None, list[Statement]]]):
        super().__init__(line, column)
        self._try_statements = try_statements
        self._except_parts = except_parts

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str] | tuple[str, _typ.Any] | None:
        try:
            for statement in self._try_statements:
                if (result := statement.execute(scope, call_stack)) is not None:
                    return result
        except Exception as e:
            for exception_classes, variable_name, statements in self._except_parts:
                ex_classes = tuple(ex.evaluate(scope, call_stack) for ex in exception_classes)
                if any(not isinstance(ex_classes, type) or not issubclass(ex_class, BaseException)
                       for ex_class in ex_classes):
                    raise _ex.WikiScriptException(f'except clause only accepts subclasses of BaseException',
                                                  self.line, self.column)
                if isinstance(e, ex_classes):
                    if variable_name:
                        scope.set_variable(variable_name, str(e))
                    for statement in statements:
                        if (result := statement.execute(scope, call_stack)) is not None:
                            return result
                    break

    def __repr__(self):
        return f'Try[try_statements={self._try_statements},except_parts={self._except_parts}]'


class RaiseStatement(Statement):
    def __init__(self, line: int, column: int, expr: Expression = None):
        super().__init__(line, column)
        self._expr = expr

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        v = self._expr.evaluate(scope, call_stack)
        if not isinstance(v, BaseException):
            raise _ex.WikiScriptException('attempt to raise value that is not an instance of BaseException',
                                          self.line, self.column)
        raise v

    def __repr__(self):
        return f'Raise[expr={self._expr!r}]'


class IfStatement(Statement):
    def __init__(self, line: int, column: int, cond: Expression, if_statements: list[Statement],
                 elif_parts: list[tuple[Expression, list[Statement]]],
                 else_statements: list[Statement]):
        super().__init__(line, column)
        self._cond = cond
        self._if_statements = if_statements
        self._elif_parts = elif_parts
        self._else_statements = else_statements

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str] | tuple[str, _typ.Any] | None:
        if self._cond.evaluate(scope, call_stack):
            for statement in self._if_statements:
                if (result := statement.execute(scope, call_stack)) is not None:
                    return result
        else:
            for elif_cond, elif_statements in self._elif_parts:
                if elif_cond.evaluate(scope, call_stack):
                    for statement in elif_statements:
                        if (result := statement.execute(scope, call_stack)) is not None:
                            return result
                    break
            else:
                for statement in self._else_statements:
                    if (result := statement.execute(scope, call_stack)) is not None:
                        return result

    def __repr__(self):
        return f'If[cond={self._cond!r},if_stmts={self._if_statements},elifs={self._elif_parts},' \
               f'else_stmts={self._else_statements}]'


class ForLoopStatement(Statement):
    def __init__(self, line: int, column: int, variables_names: str | list[str], iterator: Expression,
                 statements: list[Statement]):
        super().__init__(line, column)
        self._variables_names = variables_names
        self._iterator = iterator
        self._statements = statements

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str] | tuple[str, _typ.Any] | None:
        for element in self._iterator.evaluate(scope, call_stack):
            stop = False
            # Assign loop variable(s)
            if isinstance(self._variables_names, list):
                left_len = len(self._variables_names)
                right_len = len(element)
                if left_len < right_len:
                    raise _ex.WikiScriptException(f'too many values to unpack (expected {right_len})',
                                                  self.line, self.column)
                if left_len > right_len:
                    raise _ex.WikiScriptException(f'not enough values to unpack (expected {left_len})',
                                                  self.line, self.column)
                for i, value in enumerate(element):
                    scope.set_variable(self._variables_names[i], value)
            else:
                scope.set_variable(self._variables_names, element)
            # Execute statements
            for statement in self._statements:
                match statement.execute(scope, call_stack):
                    case ['break']:
                        stop = True
                        break
                    case ['continue']:
                        break
                    case result if result is not None:
                        return result
            if stop:
                break

    def __repr__(self):
        return f'ForLoop[variables_names={self._variables_names!r},iterator={self._iterator!r},' \
               f'statements={self._statements}]'


class WhileLoopStatement(Statement):
    def __init__(self, line: int, column: int, cond: Expression, statements: list[Statement]):
        super().__init__(line, column)
        self._cond = cond
        self._statements = statements

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str] | tuple[str, _typ.Any] | None:
        cond = self._cond.evaluate(scope, call_stack)
        while cond:
            stop = False
            for statement in self._statements:
                match statement.execute(scope, call_stack):
                    case ['break']:
                        stop = True
                        break
                    case ['continue']:
                        break
                    case result if result is not None:
                        return result
            if stop:
                break
            cond = self._cond.evaluate(scope, call_stack)

    def __repr__(self):
        return f'WhileLoop[cond={self._cond!r},statements={self._statements}]'


class BreakStatement(Statement):
    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str]:
        return 'break',

    def __repr__(self):
        return f'Break'


class ContinueStatement(Statement):
    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str]:
        return 'continue',

    def __repr__(self):
        return f'Continue'


class DefineFunctionStatement(Statement):
    def __init__(self, line: int, column: int, name: str, args: list[str], vararg: bool, kwargs: dict[str, Expression],
                 statements: list[Statement]):
        super().__init__(line, column)
        if vararg and kwargs:
            raise TypeError('vararg functions cannot have default arguments')
        self._name = name
        self._args = args
        self._vararg = vararg
        self._kwargs = kwargs
        self._statements = statements

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> None:
        # The function’s closure
        scope.set_variable(self._name, _types.ScriptFunction(
            self._name, self._args, self._kwargs, self._vararg, scope, *self._statements
        ))

    def __repr__(self):
        return f'DefineFunction[name={self._name},args={self._args},vararg={self._vararg},kwargs={self._kwargs},' \
               f'statements={self._statements}]'


class ReturnStatement(Statement):
    def __init__(self, line: int, column: int, expr: Expression = None):
        super().__init__(line, column)
        self._expr = expr

    def execute(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple[str, _typ.Any]:
        return 'return', self._expr.evaluate(scope, call_stack)

    def __repr__(self):
        return f'Return[expr={self._expr!r}]'


###############
# Expressions #
###############


class UnaryOperatorExpression(Expression):
    def __init__(self, line: int, column: int, symbol: str, operator: _typ.Callable[[_typ.Any], _typ.Any],
                 expr: Expression):
        super().__init__(line, column)
        self._symbol = symbol
        self._op = operator
        self._expr = expr

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        return self._op(self._expr.evaluate(scope, call_stack))

    def __repr__(self):
        return f'UnaryOp[op={self._symbol!r},expr={self._expr!r}]'


class BinaryOperatorExpression(Expression):
    def __init__(self, line: int, column: int, symbol: str, operator: _typ.Callable[[_typ.Any, _typ.Any], _typ.Any],
                 expr1: Expression, expr2: Expression):
        super().__init__(line, column)
        self._symbol = symbol
        self._op = operator
        self._expr1 = expr1
        self._expr2 = expr2

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        v1 = self._expr1.evaluate(scope, call_stack)
        match self._symbol:
            case 'and':
                if not v1:  # Short circuit
                    return v1
                return self._op(v1, self._expr2.evaluate(scope, call_stack))
            case 'or':
                if v1:  # Short circuit
                    return v1
                return self._op(v1, self._expr2.evaluate(scope, call_stack))
            case _:
                return self._op(v1, self._expr2.evaluate(scope, call_stack))

    def __repr__(self):
        return f'BinaryOp[op={self._symbol!r},expr1={self._expr1!r},expr2={self._expr2!r}]'


class TernaryOperatorExpression(Expression):
    def __init__(self, line: int, column: int, symbol: str,
                 operator: _typ.Callable[[_typ.Any, _typ.Any, _typ.Any], _typ.Any],
                 expr1: Expression, expr2: Expression, expr3: Expression):
        super().__init__(line, column)
        self._symbol = symbol
        self._op = operator
        self._expr1 = expr1
        self._expr2 = expr2
        self._expr3 = expr3

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        return self._op(self._expr1.evaluate(scope, call_stack),
                        self._expr2.evaluate(scope, call_stack),
                        self._expr3.evaluate(scope, call_stack))

    def __repr__(self):
        return f'TernaryOp[op={self._symbol!r},expr1={self._expr1!r},expr2={self._expr2!r}]'


class GetVariableExpression(Expression):
    def __init__(self, line: int, column: int, variable_name: str):
        super().__init__(line, column)
        self._variable_name = variable_name

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        try:
            return scope.get_variable(self._variable_name).value
        except NameError as e:
            raise _ex.WikiScriptException(str(e), self.line, self.column) from None

    def __repr__(self):
        return f'GetVariable[name={self._variable_name!r}]'


class GetPropertyExpression(Expression):
    ALLOWED_PRIVATE = (
        '__name__',
        '__qualname__',
    )

    def __init__(self, line: int, column: int, target: Expression, property_name: str):
        super().__init__(line, column)
        self._target = target
        self._property_name = property_name

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        target = self._target.evaluate(scope, call_stack)
        return self.get_attr(target, self._property_name)

    @classmethod
    def is_attribute_allowed(cls, name: str) -> bool:
        """Check whether the given attribute name is allowed.

        :param name: Attribute name to check.
        :return: True if the name is allowed, False otherwise.
        """
        # Prevent accessing private attributes
        return not name.startswith('_') or name in cls.ALLOWED_PRIVATE

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
            raise cls.get_error(o, attr_name) from None  # Cut stack trace

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

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        return self._target.evaluate(scope, call_stack)[self._key.evaluate(scope, call_stack)]

    def __repr__(self):
        return f'GetItem[target={self._target!r},key={self._key!r}]'


class DefineAnonymousFunctionExpression(Expression):
    def __init__(self, line: int, column: int, args: list[str], vararg: bool, kwargs: dict[str, Expression],
                 statements: list[Statement]):
        super().__init__(line, column)
        if vararg and kwargs:
            raise TypeError('vararg functions cannot have default arguments')
        self._args = args
        self._vararg = vararg
        self._kwargs = kwargs
        self._statements = statements

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        return _types.ScriptFunction(None, self._args, self._kwargs, self._vararg, scope.copy(), *self._statements)

    def __repr__(self):
        return f'DefineAnonymousFunction[args={self._args},vararg={self._vararg},kwargs={self._kwargs},' \
               f'statements={self._statements}]'


class FunctionCallExpression(Expression):
    def __init__(self, line: int, column: int, target: Expression,
                 args: list[Expression], kwargs: dict[str, Expression]):
        super().__init__(line, column)
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> _typ.Any:
        function = self._target.evaluate(scope, call_stack)
        args = [arg.evaluate(scope, call_stack) for arg in self._args]
        kwargs = {k: v.evaluate(scope, call_stack) for k, v in self._kwargs.items()}
        if isinstance(function, _types.ScriptFunction):
            return function(call_stack, *args, **kwargs)
        return function(*args, **kwargs)

    def __repr__(self):
        return f'FunctionCall[target={self._target!r},args={self._args}]'


class SimpleLiteralExpression(Expression):
    def __init__(self, line: int, column: int, value):
        super().__init__(line, column)
        self._value = value

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> int | float | bool | str | None:
        return self._value

    def __repr__(self):
        return repr(self._value)


class DictLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: tuple[Expression, Expression]):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> dict:
        return {k.evaluate(scope, call_stack): v.evaluate(scope, call_stack) for k, v in self._entries}

    def __repr__(self):
        return f'DictLiteral{list(self._entries)}'


class ListLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: Expression):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> list:
        return [e.evaluate(scope, call_stack) for e in self._entries]

    def __repr__(self):
        return f'ListLiteral{list(self._entries)}'


class TupleLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: Expression):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> tuple:
        return tuple(e.evaluate(scope, call_stack) for e in self._entries)

    def __repr__(self):
        return f'TupleLiteral{list(self._entries)}'


class SetLiteralExpression(Expression):
    def __init__(self, line: int, column: int, *entries: Expression):
        super().__init__(line, column)
        self._entries = entries

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> set:
        return {e.evaluate(scope, call_stack) for e in self._entries}

    def __repr__(self):
        return f'SetLiteral{list(self._entries)}'


class SliceLiteralExpression(Expression):
    def __init__(self, line: int, column: int, start: Expression = None, end: Expression = None,
                 step: Expression = None):
        super().__init__(line, column)
        self._start = start
        self._end = end
        self._step = step

    def evaluate(self, scope: _scope.Scope, call_stack: _scope.CallStack) -> slice:
        return slice(
            self._start.evaluate(scope, call_stack) if self._start else None,
            self._end.evaluate(scope, call_stack) if self._end else None,
            self._step.evaluate(scope, call_stack) if self._step else None
        )

    def __repr__(self):
        return f'SliceLiteral[start={self._start!r},end={self._end!r},step={self._step!r}]'
