import typing as _typ

from . import _scope


class Module:
    _builtins_cache = None

    def __init__(self, name: str, statements):
        """Create a module.

        :param name: Module’s name.
        :param statements: Module’s statements.
        :type statements: list[ottm.api.wiki.modules._syntax_tree.Statement]
        """
        self._load_builtins()
        self._name = name
        self._statements = statements
        self._scope = _scope.Scope()
        for k, v in self._builtins_cache.items():
            self._scope.set_variable(k, v)

    @classmethod
    def _load_builtins(cls):
        if not cls._builtins_cache:
            from . import _syntax_tree as _st

            def attrs(o):
                """Return a list of the names of all public attributes of the given object."""
                return [v for v in dir(o) if _st.GetPropertyExpression.is_attribute_allowed(v)]

            def has_attr(o, name: str) -> bool:
                return _st.GetPropertyExpression.is_attribute_allowed(name) and hasattr(o, name)

            def get_attr(o, name: str) -> _typ.Any:
                return _st.GetPropertyExpression.get_attr(o, name)

            def set_attr(o, name: str, value):
                if not _st.GetPropertyExpression.is_attribute_allowed(name):
                    raise _st.GetPropertyExpression.get_error(o, name)
                setattr(o, name, value)

            # TODO import function

            # Override default qualified names to not expose the current module name
            attrs.__qualname__ = attrs.__name__
            has_attr.__qualname__ = has_attr.__name__
            get_attr.__qualname__ = get_attr.__name__
            set_attr.__qualname__ = set_attr.__name__

            # TODO redefine print() function to print in the debug console of "Module:" pages instead of stdout
            functions = [
                # functions and types
                abs, all, any, ascii, attrs, bin, callable, format, get_attr, has_attr, hash, hex, id, isinstance,
                issubclass, iter, len, max, min, next, oct, ord, pow, print, repr, round, set_attr, sorted, sum, object,
                int, bool, bytearray, bytes, dict, enumerate, filter, float, frozenset, list, map, range, reversed, set,
                slice, str, tuple, type, zip,
                # Errors and exceptions
                AssertionError, AttributeError, ImportError, LookupError, IndexError, KeyError, NameError,
                NotImplementedError, TypeError, ValueError, UnicodeError, UnicodeDecodeError, UnicodeEncodeError,
                UnicodeTranslateError, ZeroDivisionError,
            ]
            cls._builtins_cache = {f.__name__: f for f in functions}

    @property
    def name(self) -> str:
        return self._name

    def __getattr__(self, name: str) -> _typ.Any:
        variable = self._scope.get_variable(name)
        if not variable.public:
            raise AttributeError(f'cannot access non-public variable "{name}" of module {self.name}')
        return variable.value

    def __setattr__(self, name: str, value):
        # __init__ calls this method, defer to parent version to avoid recursion loop
        # Cannot use hasattr() as it would also cause a recursion loop
        if '_scope' not in self.__dict__:
            super().__setattr__(name, value)
            return
        if name not in self._scope or not self.scope.get_variable(name).public:
            raise NameError('cannot define variables in other modules')
        if not self.scope.get_variable(name).public:
            raise AttributeError(f'cannot access non-public variable "{name}"')
        self._scope.set_variable(name, value)

    def execute(self):
        call_stack = _scope.CallStack(self._name)
        # Execute statements
        for statement in self._statements:
            if (result := statement.execute(self._scope, call_stack)) is not None:
                raise SyntaxError(f'unexpected statement "{result[0]}"')

    def __repr__(self):
        return f'Module[name={self.name!r},statements={self._statements}]'


class ScriptFunction:
    _NO_DEFAULT = object()

    def __init__(self, name: str | None, arg_names: list[str], default_arg_names: dict[str, _typ.Any], vararg: bool,
                 closure: _scope.Scope, *statements):
        """Create a WikiScript function.

        :param name: Function’s name. May be prefixed by the module’s name if in global scope. May be None if lambda.
        :param arg_names: Names of this function’s arguments.
        :param vararg: Whether the last argument is a vararg.
        :param default_arg_names: Dict object containing the names of arguments and their default values.
        :param closure: This function’s closure.
        :param statements: This function’s statements.
        :type statements: ottm.api.wiki.modules._syntax_tree.Statement
        """
        if vararg and default_arg_names:
            raise TypeError('vararg functions cannot have default arguments')
        self._name = name
        self._args = {name: self._NO_DEFAULT for name in arg_names}
        for k, v in default_arg_names.items():
            if k in arg_names:
                raise TypeError(f'duplicate argument "{arg_names}" for function {self.name}')
            self._args[k] = v
        self._vararg = vararg
        self._closure = closure
        self._statements = statements

    @property
    def name(self) -> str:
        return self._name or '<anonymous>'

    def __call__(self, call_stack: _scope.CallStack, *args, **kwargs) -> _typ.Any:
        expected_args_len = len(self._args)
        actual_pos_args_len = len(args)

        filled_args = []
        scope = _scope.Scope(self._closure)
        for i, arg_name in enumerate(self._args):
            if self._vararg and i == expected_args_len - 1:
                scope.set_variable(name=arg_name, value=args[i:])
                filled_args.append(arg_name)
            elif i >= actual_pos_args_len:
                if arg_name in kwargs:
                    if arg_name in filled_args:
                        raise TypeError(f'duplicate argument "{arg_name}" passed to function {self.name}()')
                    scope.set_variable(name=arg_name, value=kwargs[arg_name])
                    filled_args.append(arg_name)
                    del kwargs[arg_name]
            else:
                scope.set_variable(name=arg_name, value=args[i])
                filled_args.append(arg_name)
        if kwargs:
            raise TypeError(f'undefined argument "{next(iter(kwargs))}" for function {self.name}()')
        for k, v in self._args.items():
            if k not in filled_args:
                if v is not self._NO_DEFAULT:
                    filled_args.append(k)
                    scope.set_variable(name=k, value=v)
                else:
                    raise TypeError(f'missing required argument "{k}" for function {self.name}()')

        call_stack = call_stack.push(_scope.CallStack(self.name))

        # Execute statements
        for statement in self._statements:
            match statement.execute(scope, call_stack):
                case ['return']:
                    return
                case ['return', value]:
                    return value
                case result if result is not None:
                    raise SyntaxError(f'unexpected statement "{result[0]}"')

    def __repr__(self):
        return f'<function "{self.name}" @ {id(self)}>' if self.name else f'<anonymous function @ {id(self)}>'
