from __future__ import annotations

import typing as _typ

_BUILTINS_CACHE = {}


class Module:
    def __init__(self, name: str, statements):
        """Create a module.

        :param name: Module’s name.
        :param statements: Module’s statements.
        :type statements: list[ottm.api.wiki.modules._syntax_tree.Statement]
        """
        self._name = name
        self.__name__ = name
        self.__qualname__ = name
        self._exported_names = []
        self._statements = tuple(statements)
        self._scope = Scope(self)
        for k, v in self._load_builtins().items():
            self._scope.declare_variable(k, False, v)

    @classmethod
    def _load_builtins(cls) -> dict[str, _typ.Any]:
        global _BUILTINS_CACHE
        if not _BUILTINS_CACHE:
            from . import _syntax_tree as _st

            def all_(o, f: _typ.Callable[[...], bool]):
                """Return True if f(x) is True for all values x in the iterable.
                If the iterable is empty, return True."""
                return all(f(e) for e in o)

            def any_(o, f: _typ.Callable[[...], bool]):
                """Return True if f(x) is True for any x in the iterable.
                If the iterable is empty, return False."""
                return any(f(e) for e in o)

            def attrs(o):
                """Return a list of the names of all public attributes of the given object."""
                return [attr for attr in dir(o) if _st.GetPropertyExpression.is_attribute_allowed(attr)]

            def doc(o) -> str:
                """Return the documentation of the given object.
                This function is meant to be used from the interactive console."""
                return o.__doc__ or 'No documentation available.'

            def has_attr(o, name: str) -> bool:
                """Return whether an object has an attribute with the given name."""
                return _st.GetPropertyExpression.is_attribute_allowed(name) and hasattr(o, name)

            def get_attr(o, name: str) -> _typ.Any:
                """Get a named attribute from an object; get_attr(x, 'y') is equivalent to x.y.
                When the attribute doesn’t exist, an exception is raised."""
                return _st.GetPropertyExpression.get_attr(o, name)

            def set_attr(o, name: str, value):
                """Sets the named attribute on the given object to the specified value.
                set_attr(x, 'y', v) is equivalent to x.y = v"""
                if not _st.GetPropertyExpression.is_attribute_allowed(name):
                    raise _st.GetPropertyExpression.get_error(o, name)
                setattr(o, name, value)

            # Override default qualified names to not expose the current module name
            all_.__qualname__ = all_.__name__ = 'all'
            any_.__qualname__ = any_.__name__ = 'any'
            attrs.__qualname__ = attrs.__name__
            attrs.__qualname__ = attrs.__name__
            doc.__qualname__ = doc.__name__
            has_attr.__qualname__ = has_attr.__name__
            get_attr.__qualname__ = get_attr.__name__
            set_attr.__qualname__ = set_attr.__name__

            # TODO redefine print() function to print in the debug console of "Module:" pages instead of stdout
            properties = [
                # functions and types
                abs, all_, any_, ascii, attrs, bin, callable, complex, doc, format, get_attr, has_attr, hash, hex, id,
                isinstance, issubclass, iter, len, max, min, next, oct, ord, pow, print, repr, round, set_attr, sorted,
                sum, object, int, bool, bytearray, bytes, dict, enumerate, filter, float, frozenset, list, map, range,
                reversed, set, slice, str, tuple, type, zip,
                # Errors and exceptions
                AssertionError, AttributeError, ImportError, LookupError, IndexError, KeyError, NameError,
                NotImplementedError, TypeError, ValueError, UnicodeError, UnicodeDecodeError, UnicodeEncodeError,
                UnicodeTranslateError, ZeroDivisionError,
            ]
            _BUILTINS_CACHE = {f.__name__: f for f in properties}
        return _BUILTINS_CACHE

    def __dir__(self) -> _typ.Iterable[str]:
        return [n for n in self._scope.get_variable_names() if n in self._exported_names]

    def get_attr(self, name: str) -> _typ.Any:
        try:
            variable = self._scope.get_variable(name)
        except NameError:
            raise AttributeError(f'module {self._name} does not have a property named "{name}"')
        if variable not in self._exported_names:
            raise AttributeError(f'module {self._name} does not export name "{name}"')
        return variable.value

    def set_exported_names(self, names: set[str]):
        for name in names:
            self._scope.get_variable(name)  # Check if variable exists
            self._exported_names.append(name)

    def execute(self):
        call_stack = CallStack(self._name)
        # Execute statements
        for statement in self._statements:
            if isinstance(result := statement.execute(self._scope, call_stack), list):
                raise SyntaxError(f'unexpected statement "{result[0]}"')

    def __str__(self):
        return f'<module "{self._name}">'

    def __repr__(self):
        return f'Module[name={self._name!r},statements={self._statements}]'


class FunctionClosure:
    def __init__(
            self,
            name: str | None,
            arg_names: _typ.Sequence[str],
            default_args: _typ.Sequence[tuple[str, _typ.Any]],
            vararg: bool,
            scope: Scope,
            call_stack: CallStack,
            *statements,
    ):
        """Create a WikiScript function closure.

        :param name: Function’s name. May be prefixed by the module’s name if in global scope. May be None if lambda.
        :param arg_names: Names of this function’s arguments.
        :param default_args: The names of arguments and their default values.
        :param vararg: Whether the last argument is a vararg.
        :param scope: The scope the function is defined in.
        :param call_stack: The call stack when the function is defined.
        :param statements: This function’s statements.
        :type statements: ottm.api.wiki.modules._syntax_tree.Statement
        """
        if vararg and default_args:
            raise TypeError('vararg functions cannot have default arguments')
        self._arg_names = tuple(arg_names)
        self._default_args = tuple(default_args)
        self._ensure_no_duplicates(self._arg_names + tuple(name for name, _ in self._default_args))
        self._vararg = vararg
        self._scope = scope
        self._call_stack = call_stack
        self._statements = statements
        self.__name__ = name or '<anonymous>'
        self.__qualname__ = call_stack.path + '.' + self.__name__

    def _ensure_no_duplicates(self, values: _typ.Iterable[str]):
        seen = set()
        for v in values:
            if v in seen:
                raise NameError(f'duplicate argument name "{v}"')

    def __call__(self, *args: _typ.Any) -> _typ.Any:
        min_expected_args_nb = len(self._arg_names)
        max_expected_args_nb = min_expected_args_nb + len(self._default_args)
        actual_args_nb = len(args)

        if actual_args_nb < min_expected_args_nb:
            raise RuntimeError(
                f'function {self.__name__!r} expects at least {min_expected_args_nb} arguments, {actual_args_nb} given')
        if actual_args_nb > max_expected_args_nb:
            raise RuntimeError(
                f'function {self.__name__!r} expects at most {max_expected_args_nb} arguments, {actual_args_nb} given')

        scope = self._scope.push()
        call_stack = self._call_stack.push(self.__name__)

        # Unpack arguments
        if self._vararg:
            unpacked_values = self.unpack_values(actual_args_nb, True, args)
            for var_name, v in zip(self._arg_names, unpacked_values):
                scope.declare_variable(var_name, False, v, ignore_name_conflicts=True)
        else:
            start_i = len(args) - min_expected_args_nb
            completed_args = args + tuple(default for _, default in self._default_args[start_i:])
            unpacked_values = self.unpack_values(max_expected_args_nb, False, completed_args)
            all_arg_names = self._arg_names + tuple(vname for vname, _ in self._default_args)
            for var_name, v in zip(all_arg_names, unpacked_values):
                scope.declare_variable(var_name, False, v, ignore_name_conflicts=True)

        # Execute statements
        for statement in self._statements:
            match statement.execute(scope, call_stack):
                case ['return', value]:
                    return value
                case [stmt]:
                    raise SyntaxError(f'unexpected statement "{stmt}"')
        return None

    def __repr__(self):
        return f'<function "{self.__qualname__}" at {id(self):#x}>'

    @staticmethod
    def unpack_values(vars_nb: int, last_takes_rest: bool, values: _typ.Any) -> list[_typ.Any]:
        unpacked_values = []
        iterator = iter(values)
        for i in range(vars_nb):
            if last_takes_rest and i == vars_nb - 1:
                break
            try:
                value = next(iterator)
            except StopIteration:
                raise ValueError(f'not enough values to unpack (expected {vars_nb})')
            else:
                unpacked_values.append(value)
        if last_takes_rest:
            unpacked_values.append(list(iterator))
        else:
            try:
                next(iterator)
            except StopIteration:
                pass
            else:
                raise ValueError(f'too many values to unpack (expected {vars_nb})')
        return unpacked_values


class CallStack:
    MAX_DEPTH = 500

    def __init__(self, name: str):
        self._name = name
        self._parent: CallStack | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        if self._parent:
            return self._parent.path + '.' + self.name
        return self.name

    def __len__(self):
        return 1 + len(self._parent or [])

    def push(self, name: str) -> CallStack:
        if len(self) == self.MAX_DEPTH:
            raise OverflowError(f'reached max call recursion depth of {self.MAX_DEPTH}')
        element = CallStack(name)
        element._parent = self
        return element


_NO_VALUE = object()


class Scope:
    MAX_DEPTH = 500

    def __init__(self, module: Module, parent: Scope = None):
        """Create a new scope.

        :param module: The module the scope belongs to.
        :param parent: The parent scope.
        """
        self._module = module
        self._parent = parent
        self._variables: dict[str, Variable] = {}

    @property
    def module(self) -> Module:
        """This scope’s module.

        :return: This scope’s module.
        """
        return self._module

    def declare_variable(self, name: str, is_const: bool, value=_NO_VALUE, ignore_name_conflicts: bool = False):
        """Declare a new variable.

        :param name: The variable’s name.
        :param is_const: If true, the variable’s value won’t be changeable.
        :param value: Optional. The variable’s initial value.
        :param ignore_name_conflicts: If true, name conflicts will be ignored.
        :raise NameError: If a variable with the same name already exists.
        :raise ValueError: If ``is_const`` is true and no value was provided.
        """
        if not ignore_name_conflicts:
            try:
                self.get_variable(name)
            except NameError:
                pass
            else:
                raise NameError(f'variable "{name}" is already defined')

        if is_const and value is _NO_VALUE:
            raise ValueError('const variables must have an initial value')
        self._variables[name] = Variable(None if value is _NO_VALUE else value, is_const)

    def get_variable_names(self) -> list[str]:
        """Return the names of all variables from this scope and its parents.

        :return: A sorted list of this scope’s and its parents’ variables names.
        """
        names = []
        sc = self
        while sc:
            names += sc._variables.keys()
            sc = sc._parent
        return sorted(names)

    def get_variable(self, name: str, current_only: bool = False) -> Variable:
        """Return the Variable object for the given name.

        :param name: Variable’s name.
        :param current_only: Whether to only look into the current scope, not its parents.
        :return: A Variable object.
        :raise NameError: If no variable with this name is defined.
        """
        if name not in self._variables:
            if current_only or not self._parent:
                raise NameError(f'undefined variable "{name}"')
            return self._parent.get_variable(name)
        return self._variables[name]

    def set_variable(self, name: str, value: _typ.Any):
        """Set the value of the given variable.

        :param name: Variable’s name.
        :param value: Variable’s new value.
        :raise NameError: If no variable with this name is defined.
        :raise TypeError: If the variable is const.
        """
        if name not in self._variables:
            raise NameError(f'undefined variable "{name}"')
        else:
            variable = self._variables[name]
            if variable.is_const:
                raise TypeError(f'cannot reassign const variable "{name}"')
            variable.value = value

    def push(self) -> Scope:
        return Scope(self.module, self)

    def pop(self) -> Scope:
        return self._parent


class Variable:
    def __init__(self, value: _typ.Any, is_const: bool):
        """Create a new variable.

        :param value: Variable’s value.
        :param is_const: Whether the variable is constant.
        """
        self._value = value
        self._is_const = is_const

    @property
    def value(self) -> _typ.Any:
        """This variable’s value."""
        return self._value

    @value.setter
    def value(self, value: _typ.Any):
        """Set this variable’s value."""
        self._value = value

    @property
    def is_const(self) -> bool:
        """Whether this variable’s value is constant."""
        return self._is_const

    def copy(self) -> Variable:
        """Return a shallow copy of this variable."""
        return Variable(self.value, self.is_const)
