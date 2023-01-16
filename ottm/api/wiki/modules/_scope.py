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

    def __init__(self):
        self._variables: dict[str, Variable] = {}

    def __contains__(self, variable_name: str):
        """Check whether this scope contains the given variable.

        :param variable_name: Name of the variable to check.
        :return: True if this scope defines this variable.
        """
        return variable_name in self._variables

    def get_variable(self, name: str) -> Variable:
        """Return the Variable object for the given name.

        :param name: Variable’s name.
        :return: A Variable object.
        :raise NameError: If no variable with this name is defined.
        """
        if name not in self:
            raise NameError(f'undefined variable "{name}"')
        return self._variables[name]

    def set_variable(self, name: str, value):
        """Set the value of the given variable. If it is undefined, it will be created.

        :param name: Variable’s name.
        :param value: Variable’s new value.
        """
        if name not in self:
            self._variables[name] = Variable(value, public=name[0] != '_')
        else:
            self.get_variable(name).value = value

    def delete_variable(self, name: str):
        """Delete the given variable.

        :param name: Name of the variable to delete.
        :raise NameError: If no variable with this name is defined.
        """
        if name not in self:
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
