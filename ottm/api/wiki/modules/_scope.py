from __future__ import annotations


class CallStack:
    MAX_DEPTH = 500

    def __init__(self, name: str):
        self._name = name
        self._parent: CallStack | None = None

    @property
    def name(self) -> str:
        return self._name

    def __len__(self):
        return 1 + len(self._parent or [])

    def push(self, element: CallStack) -> CallStack:
        if len(self) == self.MAX_DEPTH:
            raise OverflowError(f'reached max call recursion depth of {self.MAX_DEPTH}')
        element._parent = self
        return element


class Scope:
    MAX_DEPTH = 500

    def __init__(self, parent: Scope = None):
        self._parent = parent
        self._variables: dict[str, Variable] = {}

    def __contains__(self, variable_name: str):
        """Check whether this scope or its parents contain the given variable.

        :param variable_name: Name of the variable to check.
        :return: True if this scope or its parents define this variable.
        """
        return variable_name in self._variables or self._parent and variable_name in self._parent

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

    def set_variable(self, name: str, value):
        """Set the value of the given variable. If it is undefined, it will be created.

        :param name: Variable’s name.
        :param value: Variable’s new value.
        """
        if name not in self._variables:
            self._variables[name] = Variable(value, public=name[0] != '_')
        else:
            self._variables[name].value = value

    def delete_variable(self, name: str):
        """Delete the given variable.

        :param name: Name of the variable to delete.
        :raise NameError: If no variable with this name is defined or the variable is defined in a parent scope.
        """
        if name not in self._variables:
            if name in self._parent:
                raise NameError('cannot delete variables from outer scope')
            raise NameError(f'undefined variable "{name}"')
        del self._variables[name]

    def copy(self) -> Scope:
        """Return a copy of this scope object. Variables’ values are not copied."""
        s = Scope()
        s._variables = {k: v.copy() for k, v in self._variables.items()}
        return s


class Variable:
    def __init__(self, value, public: bool):
        """Create a new variable.

        :param value: Variable’s value.
        :param public: Whether the variable should be accessible from outside of the module that defines it.
        """
        self._value = value
        self._public = public

    @property
    def value(self):
        """This variable’s value."""
        return self._value

    @value.setter
    def value(self, value):
        """Set this variable’s value."""
        self._value = value

    @property
    def public(self) -> bool:
        """Whether this variable’s value should be accessible from outside of the module that defines it."""
        return self._public

    def copy(self):
        """Return a shallow copy of this variable."""
        return Variable(self.value, self.public)
