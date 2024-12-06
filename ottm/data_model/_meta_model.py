from __future__ import annotations

import base64 as _b64
import collections.abc as colabc
import re
import struct
import typing

import django.core.exceptions as _dj_exc
import django.db.models as _dj_models

from . import _i18n_models as _i18n
from .. import model_fields as _mf
from ..api import data_types as _dt

IDENTIFIER_LENGTH = 50
IDENTIFIER_PATTERN = re.compile(r'^[a-z][a-z0-9_-]*$')

type Number = int | float


def choices(*values: typing.Any, mapper: typing.Callable[[typing.Any], str] = str) -> tuple[tuple[str, str], ...]:
    return tuple((v, mapper(v)) for v in values)


# region Validators


def int_is_positive_or_zero(v: int):
    if v < 0:
        raise _dj_exc.ValidationError('Int value is < 0', code='negative_int')


def int_is_positive(v: int):
    if v <= 0:
        raise _dj_exc.ValidationError('Int value is <= 0', code='negative_or_zero_int')


def non_empty_str(v: str):
    if not v:
        raise _dj_exc.ValidationError('String is empty', code='empty_string')


def identifier_str(v: str):
    if not IDENTIFIER_PATTERN.fullmatch(v):
        raise _dj_exc.ValidationError('String is not a valid identifier', code='invalid_identifier_string')


def _range_validator(v: Number, mini: Number, maxi: Number):
    if v < mini or v > maxi:
        raise _dj_exc.ValidationError(
            f'{v} is outside range [{mini}, {maxi}]',
            code='value_outside_range'
        )


def latitude_validator(v: Number):
    _range_validator(v, -90, 90)


def longitude_validator(v: Number):
    _range_validator(v, -180, 180)


# endregion
# region Types


class UniqueLabeledModel(_dj_models.Model):
    """Abstract base class for models that have a unique label."""

    label = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
        unique=True,
    )

    class Meta:
        abstract = True

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and self.label == other.label

    def __hash__(self) -> int:
        return hash(self.label)


class LabeledModel(_dj_models.Model):
    """Abstract base class for models that have a label that is not unique by itself."""

    label = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
    )

    class Meta:
        abstract = True

    def _type_label(self) -> str:
        """The label for the type associated to this model."""
        raise NotImplementedError()

    def __eq__(self, other) -> bool:
        return (isinstance(other, self.__class__)
                and self.label == other.label
                and self._type_label() == other._type_label())

    def __hash__(self) -> int:
        return hash((self.label, self._type_label()))


class Translation(_dj_models.Model):
    """Abstract base class for label translations."""

    language = _dj_models.ForeignKey(
        _i18n.Language,
        on_delete=_dj_models.PROTECT,
    )
    localized_text = _dj_models.TextField(
        validators=[non_empty_str],
    )
    description = _dj_models.TextField(
        null=True,
        blank=True,
        default=None,
    )

    class Meta:
        abstract = True


class UnitType(UniqueLabeledModel):
    """This class represents a unit type (e.g. length, speed, etc.).

    Two unit types are considered equal if they have the same label.
    """


class UnitTypeTranslation(Translation):
    """This class represents a translation of a UnitType’s label."""

    unit_type = _dj_models.ForeignKey(
        UnitType,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('unit_type', 'language')


class EnumType(UniqueLabeledModel):
    """An enum is a collection of unique values.

    Two enums are considered equal if they have the same label.
    """

    def get_values(self) -> list[EnumValue]:
        """Returns a list of values for this enum, ordered by their label.

        :return: A list of all values for this enum.
        """
        return list(EnumValue.objects.filter(type=self).order_by('label'))

    def has_value(self, v: str) -> bool:
        """Check whether the given enum value label exists in this enum.

        :param v: The label to check.
        :return: True if this enum has an EnumValue with the given label, False otherwise.
        """
        return self.enumvalue_set.filter(type=self, label=v).exists()


class EnumTypeTranslation(Translation):
    """This class represents a translation of a EnumType’s label."""

    enum_type = _dj_models.ForeignKey(
        EnumType,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('enum_type', 'language')


class EnumValue(LabeledModel):
    """This class represents a value of an EnumType"""

    type = _dj_models.ForeignKey(
        EnumType,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('type', 'label')

    def _type_label(self) -> str:
        return self.type.label


class EnumValueTranslation(Translation):
    """This class represents a translation of an EnumValue’s label."""

    enum_value = _dj_models.ForeignKey(
        EnumValue,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('enum_value', 'language')


GEOMETRY_TYPES = choices('Point', 'LineString', 'Polygon')


class ObjectType(UniqueLabeledModel):
    """This class represents the type of an object.
    Types may have property definitions represented by the ObjectProperty class.
    A type with a parent type will inherit all its property definitions.
    Types may also have a geometry type which defines what geospatial properties it has.
    Instances are represented by the Object class.

    A type declared as temporal means that its Object instances have start/end dates
    and thus must have an existence interval.

    Two types are considered equal if they have the same label.
    """

    parent_type = _dj_models.ForeignKey(
        'self',
        on_delete=_dj_models.PROTECT,
        related_name='subtypes',
        null=True,
        blank=True,
        default=None,
    )
    geometry_type = _dj_models.CharField(
        max_length=10,
        choices=((None, 'None'), *GEOMETRY_TYPES),
        null=True,
        blank=True,
        default=None,
    )
    is_deprecated = _dj_models.BooleanField(
        default=False,
    )
    is_temporal = _dj_models.BooleanField(
        default=False,
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'parent_type' not in exclude) and self._detect_type_loop(self):
            raise _dj_exc.ValidationError(
                f'Object type "{self.label}" cannot be its own parent',
                code='ObjectType_own_parent'
            )
        if (not exclude or 'geometry_type' not in exclude) and self._detect_geometry_type_conflict():
            raise _dj_exc.ValidationError(
                f'Geometry type of object type "{self.label}" differs from its parents’',
                code='ObjectType_geometry_type_different_from_parents'
            )

    def _detect_type_loop(self, of: ObjectType) -> bool:
        return self.parent_type and (self.parent_type == of or self.parent_type._detect_type_loop(of))

    def _detect_geometry_type_conflict(self) -> bool:
        return self.geometry_type and self.parent_type and (
                self.parent_type.geometry_type == self.geometry_type
                or self.parent_type._detect_geometry_type_conflict())

    def has_geometry_type(self, geometry_type: str) -> bool:
        """Indicate whether this object type has the given geometry type.

        :param geometry_type: The geometry type to check.
        :return: True if this object type has the given geometry type, False otherwise.
        """
        return (self.geometry_type == geometry_type
                or self.parent_type and self.parent_type.has_geometry_type(geometry_type))

    def get_geometry_type(self) -> str | None:
        """Return the geometry type of this object type.

        :return: A string defined in GEOMETRY_TYPES if this object type has a geometry type, None otherwise.
        """
        return self.geometry_type or self.parent_type and self.parent_type.get_geometry_type()

    def is_same_or_subtype_of(self, a_type: ObjectType) -> bool:
        """Check whether this object type is the same or a subtype of the given one.

        :param a_type: An ObjectType.
        :return: True if this object type is the same or a subtype of the given one.
        """
        return self == a_type or self.parent_type.is_same_or_subtype_of(a_type)

    def __contains__(self, label_or_property: str | ObjectProperty) -> bool:
        """Check whether this object type has a property with the given label or the given ObjectProperty.

        :param label_or_property: The label or ObjectProperty to check.
        :return: True if this object type has a property with the given label or the given ObjectProperty,
            False otherwise.
        """
        if isinstance(label_or_property, str):
            return (self.properties.filter(label=label_or_property) or
                    self.parent_type and label_or_property in self.parent_type)
        elif isinstance(label_or_property, ObjectProperty):
            return (self.properties.contains(label_or_property) or
                    self.parent_type and label_or_property in self.parent_type)
        else:
            raise TypeError(f'Expected either a string or a ObjectProperty instance, got {type(label_or_property)}.')

    def __getitem__(self, prop_label: str) -> ObjectProperty | None:
        """Return the ObjectProperty with the given label.

        :param prop_label: The label of the property to return.
        :return: The ObjectProperty or None if it does not exist.
        """
        prop = self.properties.get(prop_label)
        if not prop and self.parent_type:
            return self.parent_type[prop_label]
        return prop


class ObjectTypeTranslation(Translation):
    """This class represents a translation of an ObjectType’s label."""

    object_type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('object_type', 'language')


class ObjectProperty(LabeledModel):
    """This class represents the definition of an ObjectType’s property.
    A property can only be attached to a single ObjectType.
    Property values are represented by the PropertyValue class.

    A property whose ``is_unique`` field is set to True means that there can be only a single PropertyValue instance
    attached to the corresponding Object instance.
    """

    object_type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.PROTECT,
        related_name='properties',
    )
    is_unique = _dj_models.BooleanField(
        default=True,
    )
    is_deprecated = _dj_models.BooleanField(
        default=False,
    )

    class Meta:
        unique_together = ('object_type', 'label')

    def validate_unique(self, exclude: colabc.Collection[str] = None):
        super().validate_unique(exclude)
        # No need to check on object_type as the Meta class already defines this unicity constraint
        if self.object_type.parent_type and self.label in self.object_type.parent_type:
            raise _dj_exc.ValidationError(
                f'A parent of type "{self.object_type.label}" already has a property named "{self.label}"',
                code='ObjectProperty_parent_duplicate'
            )
        if any(self.label in subtype for subtype in self.object_type.subtypes):
            raise _dj_exc.ValidationError(
                f'A subtype of type "{self.object_type.label}" already has a property named "{self.label}"',
                code='ObjectProperty_subtype_duplicate'
            )

    @property
    def full_name(self) -> str:
        """This property’s full name in the form ``<self.object_type.label>.<self.label>``."""
        return f'{self.object_type.label}.{self.label}'

    def is_value_compatible(self, prop_value: PropertyValue) -> bool:
        """Check whether the given PropertyValue is compatible with this ObjectProperty,
        i.e. whether the PV’s type is this one, their unicity constraints are the same,
        and the PV’s value is compatible with this property.

        This is used by the ``ObjectType.set_type()`` method.

        :param prop_value: The PropertyValue to check.
        :return: True if all the above conditions are True at the same time, False otherwise.
        """
        return (
                self.label == prop_value.property_type.label and
                self.is_unique == prop_value.property_type.is_unique and
                self.is_value_valid(prop_value.value)
        )

    def is_value_valid(self, value) -> bool:
        """Check whether the given value is valid for this ObjectProperty.

        This is used by the ``self.is_value_compatible()`` method.

        :param value: The value to check.
        :return: True if the value is valid for this ObjectProperty, False otherwise.
        """
        raise NotImplementedError()

    def new_value(self, o: Object, value) -> PropertyValue:
        """Create a new PropertyValue instance for this ObjectProperty.

        :param o: The instance Object to attach the new value to.
        :param value: The value to attach to the Object.
        :return: The newly created PropertyValue instance.
        """
        raise NotImplementedError()

    def _type_label(self) -> str:
        return self.object_type.label


class ObjectPropertyTranslation(Translation):
    """This class represents a translation of an ObjectProperty’s label."""

    object_property = _dj_models.ForeignKey(
        ObjectProperty,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('object_property', 'language')


class BooleanProperty(ObjectProperty):
    """This class represents a property that accepts bool values."""

    def is_value_valid(self, value) -> bool:
        return isinstance(value, bool)

    def new_value(self, o: Object, value: bool) -> BooleanPropertyValue:
        return BooleanPropertyValue(
            object=o,
            property_type=self,
            value=value,
        )


class NumberProperty(ObjectProperty):
    """Abstract base class for object properties that accept numbers.

    Number properties may have a min and max bounds.
    """

    unit_type = _dj_models.ForeignKey(
        UnitType,
        on_delete=_dj_models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )
    min: Number  # Implemented in sub-classes
    max: Number  # Implemented in sub-classes

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'min' not in exclude and 'max' not in exclude) and self.min >= self.max:
            raise _dj_exc.ValidationError('Invalid min/max values', code='invalid_number_property_min_max')

    def is_value_valid(self, value) -> bool:
        return (isinstance(value, int | float) and
                (self.min is None or value >= self.min) and
                (self.max is None or value <= self.max))

    def new_value(self, o: Object, value: Number, unit: Unit = None) -> NumberPropertyValue:
        """Create a new NumberPropertyValue instance for this NumberProperty.

        :param o: The instance Object to attach the new value to.
        :param value: The value to attach to the Object.
        :param unit: If this property definition has an associated UnitType,
            a compatible Unit instance to pass to the new NumberPropertyValue instance.
        :return: The newly created NumberPropertyValue instance.
        """
        raise NotImplementedError()


class IntegerProperty(NumberProperty):
    """This class represents a property that accepts int values."""

    min = _dj_models.IntegerField(
        null=True,
        blank=True,
    )
    max = _dj_models.IntegerField(
        null=True,
        blank=True,
    )

    def is_value_valid(self, value) -> bool:
        return super().is_value_valid(value) and isinstance(value, int)

    def new_value(self, o: Object, value: int, unit: Unit = None) -> IntegerPropertyValue:
        return IntegerPropertyValue(
            object=o,
            property_type=self,
            value=value,
            unit=unit,
        )


class FloatProperty(NumberProperty):
    """This class represents a property that accepts float values."""

    min = _dj_models.FloatField(
        null=True,
        blank=True,
    )
    max = _dj_models.FloatField(
        null=True,
        blank=True,
    )

    def new_value(self, o: Object, value: float, unit: Unit = None) -> FloatPropertyValue:
        return FloatPropertyValue(
            object=o,
            property_type=self,
            value=value,
            unit=unit,
        )


class StringProperty(ObjectProperty):
    r"""This class represents a property that accepts string values.
    The is_multiline field indicates whether ``\n`` and ``\r`` characters are allowed.
    If is_translatable is True, all associated StringPropertyValue instances will be translatable.
    """

    is_multiline = _dj_models.BooleanField(
        default=False,
    )
    is_translatable = _dj_models.BooleanField(
        default=False,
    )

    def is_value_valid(self, value) -> bool:
        return (isinstance(value, str) and
                (self.is_multiline or ('\n' not in value and '\r' not in value)))

    def new_value(self, o: Object, value: str) -> StringPropertyValue:
        return StringPropertyValue(
            object=o,
            value=value,
            property_type=self,
        )


class DateIntervalProperty(ObjectProperty):
    """This class represents a property that accepts DateInterval values."""

    def is_value_valid(self, value) -> bool:
        return isinstance(value, _dt.DateInterval)

    def new_value(self, o: Object, value: _dt.DateInterval) -> DateIntervalPropertyValue:
        return DateIntervalPropertyValue(
            object=o,
            property_type=self,
            value=value,
        )


class TypeProperty(ObjectProperty):
    """This class represents a property that accepts Object values."""

    target_type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.PROTECT,
    )

    def is_value_valid(self, value) -> bool:
        return isinstance(value, Object) and value.is_instance_of(self.target_type)

    def new_value(self, o: Object, value: Object) -> TypePropertyValue:
        return TypePropertyValue(
            object=o,
            property_type=self,
            value=value,
        )


class TemporalProperty(TypeProperty):
    """This class represents a property that accepts temporal Object values,
    i.e. Object instances whose ObjectType has a is_temporal field set to True.

    If ``allows_overlaps`` is True, Object values may have overlapping existence intervals. Otherwise, they cannot.
    """

    allows_overlaps = _dj_models.BooleanField(
        default=False,
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'unique' not in exclude) and self.is_unique:
            raise _dj_exc.ValidationError(
                'Temporal properties cannot have "unique" property set to True',
                code='TemporalProperty_unique'
            )

    def is_value_valid(self, value) -> bool:
        return super().is_value_valid(value) and value.type.is_temporal

    def new_value(self, o: Object, value: Object) -> TemporalPropertyValue:
        return TemporalPropertyValue(
            object=o,
            property_type=self,
            value=value,
        )


class EnumProperty(ObjectProperty):
    """This class represents a property that accepts enum values."""

    enum_type = _dj_models.ForeignKey(
        EnumType,
        on_delete=_dj_models.PROTECT,
    )

    def is_value_valid(self, value) -> bool:
        return ((isinstance(value, str) and self.enum_type.has_value(value)) or
                (isinstance(value, EnumValue) and self.enum_type.has_value(value.label)))

    def new_value(self, o: Object, value: EnumValue) -> EnumPropertyValue:
        return EnumPropertyValue(
            object=o,
            property_type=self,
            value=value,
        )


# endregion
# region Instances


class Unit(_dj_models.Model):
    """This class represents a unit of a given type.
    The ``is_default`` field indicates which unit to use by default when creating a new NumberPropertyValue.
    Only one unit per type should have this field set to True.
    """

    symbol = _dj_models.CharField(
        max_length=20,
        validators=[non_empty_str],
        unique=True,
    )
    type = _dj_models.ForeignKey(
        UnitType,
        on_delete=_dj_models.PROTECT,
        related_name='units',
    )
    is_default = _dj_models.BooleanField(
        default=False,
    )

    class Meta:
        unique_together = ('type', 'is_default')


class Object(_dj_models.Model):
    """This class represents an instance of an ObjectType.

    An object’s type should never be modified directly through its ``_type`` field.
    Instead use its ``set_type()`` method that performs important checks and updates the Object’s property values.

    Only Objects whose type’s ``is_temporal`` field is set to True may have an existence inverval.
    """

    _type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.PROTECT,
        related_name='instances',
    )
    existence_interval = _mf.DateIntervalField(
        null=True,
        blank=True,
        default=None,
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if not exclude or 'existence_inverval' not in exclude:
            if self.existence_interval and not self._type.is_temporal:
                raise _dj_exc.ValidationError(
                    'Non-temporal object cannot have an existence interval',
                    code='Object_non_temporal_has_existence_inverval'
                )
            elif not self.existence_interval and self._type.is_temporal:
                raise _dj_exc.ValidationError(
                    'Temporal object must have an existence interval',
                    code='Object_temporal_has_no_existence_inverval'
                )

    @property
    def type(self) -> ObjectType:
        """This Object’s type."""
        return self._type

    def set_type(self, new_type: ObjectType):
        """Set this Object’s type. If the new type is the same as the current one, nothing happens.
        Otherwise, the following checks are performed in that order:

        * The current type’s geometry type and the new type’s are checked.
        * Incompatible property values are deleted, compatible ones are kept.

        :param new_type: The new type.
        :raise TypeError: If the current type’s geometry type and the new type’s differ.
        """
        if self.type == new_type:
            return

        expected_geom_type = self._type.geometry_type
        actual_geom_type = new_type.geometry_type
        if expected_geom_type != actual_geom_type:
            raise TypeError(f'incompatible geometry type, expected {expected_geom_type}, got {actual_geom_type}')

        to_keep: dict[str, tuple[ObjectProperty, list[PropertyValue]]] = {}
        for pv in self.properties.all():
            name = pv.property_type.label
            if (prop := new_type[name]) and prop.is_value_compatible(pv):
                if name not in to_keep:
                    to_keep[name] = prop, []
                to_keep[name][1].append(pv)

        for pv in self.properties.all():
            pv.delete()

        for name, (prop, pvs) in to_keep.items():
            if prop.is_unique:
                self[name] = pvs[0].value
            else:
                self[name] = [pv.value for pv in pvs]

    def is_instance_of(self, a_type: ObjectType) -> bool:
        """Check whether this object is an instance of the given type.

        :param a_type: The type to check.
        :return: True if this Object’s type is the same or a subtype of the given type, False otherwise.
        """
        return self.type.is_same_or_subtype_of(a_type)

    def __contains__(self, prop_name: str) -> bool:
        """Check whether this Object’s type has the given property.

        :param prop_name: The name of the property to check.
        :return: True if this Object’s type has the given property, False otherwise.
        :raise KeyError: If no property with the given name exists for this Object’s type.
        """
        return prop_name in self.type

    def __getitem__(self, prop_name: str) -> typing.Any | None:
        """Return the value(s) of the given property.

        :param prop_name: The name of the property to return the value(s) of.
        :return: If the property’s type is unique, the value of the property, or None if it has no value yet.
            If the property’s type is not unique, a list of the property’s values,
            or an empty list if it has no value yet.
        :raise KeyError: If no property with the given name exists for this Object’s type.
        """
        prop, prop_values = self._get_property_values_or_raise(prop_name)
        if prop.is_unique:
            return prop_values[0].value if prop_values else None
        return [pv.value for pv in prop_values]

    def __setitem__(self, prop_name: str, value) -> None:
        """Set the value(s) of the given property.

        :param prop_name: The name of the property to set the value(s) of.
        :param value: If this property’s type is unique, the value of the property.
            If the property’s type is not unique, a Sequence containing the property’s values.
        :raise KeyError: If no property with the given name exists for this Object’s type.
        :raise ValueError: If the value is None or an empty Sequence.
        """
        prop, prop_values = self._get_property_values_or_raise(prop_name)
        for pv in prop_values:
            pv.delete()
        if isinstance(value, colabc.Sequence):
            if len(value) == 0:
                raise ValueError('Value list is empty')
            for v in value:
                self._create_property_binding(prop, v)
        else:
            if value is None:
                raise ValueError('Value is None')
            self._create_property_binding(prop, value)

    def __delitem__(self, prop_name: str) -> None:
        """Delete the value(s) of the given property from this Object.
        Later calls to ``this_object[prop_name]`` will return an empty value unless it is assigned again.

        :param prop_name: The name of the property to delete the values of.
        :raise KeyError: If no property with the given name exists for this Object’s type.
        """
        prop, prop_values = self._get_property_values_or_raise(prop_name)
        for pv in prop_values:
            pv.delete()

    def _create_property_binding(self, prop: ObjectProperty, value) -> None:
        """Create a new PropertyValue instance for the given ObjectProperty and this Object.

        :param prop: The property to use as a factory.
        :param value: The value of the property.
        :raise ValueError: If the value is incompatible with the ObjectProperty.
        """
        if not prop.is_value_compatible(value):
            raise ValueError(f'Value {value!r} is not compatible with property {prop.full_name}')
        if isinstance(prop, NumberProperty):  # Special case for number properties who take an additional "unit" arg
            # Pick the default unit
            unit = prop.unit_type.units.get(is_default=True) if prop.unit_type else None
            self.properties.add(prop.new_value(self, value, unit))
        else:
            self.properties.add(prop.new_value(self, value))

    def get_property_unit(self, name: str, index: int = 0) -> Unit:
        """Return the unit of the given property’s value.

        :param name: The name of the property to get the unit of.
        :param index: The index of the property value to get the unit of.
        :return: A Unit object.
        :raise KeyError: If no property with the given name exists for this Object’s type.
        :raise TypeError: If the property accepts no unit.
        :raise IndexError: If the property has no value at the given index.
        """
        prop_values: list[NumberPropertyValue]
        prop, prop_values = self._get_property_values_or_raise(name)
        if not isinstance(prop, NumberProperty) or not prop.unit_type:
            raise TypeError(f'Property "{prop.full_name}" does not have a unit')
        i = 0
        for pv in prop_values:
            if i == index:
                return pv.unit
        raise IndexError(f'Property "{prop.full_name}" has no value at index {index}')

    def set_property_unit(self, name: str, unit: Unit, index: int = 0) -> None:
        """Set the unit of the given property.

        :param name: The name of the property to set the unit of.
        :param unit: The new unit.
        :param index: The index of the property value to set the unit of.
        :raise KeyError: If no property with the given name exists for this Object’s type.
        :raise TypeError: If the property accepts no unit.
        :raise IndexError: If the property has no value at the given index.
        """
        prop_values: list[NumberPropertyValue]
        prop, prop_values = self._get_property_values_or_raise(name)
        if not isinstance(prop, NumberProperty) or not prop.unit_type:
            raise TypeError(f'Property "{prop.full_name}" does not have a unit')
        i = 0
        for pv in prop_values:
            if i == index:
                pv.unit = unit
                break
            i += 1
        else:
            raise IndexError(f'Property "{prop.full_name}" has no value at index {index}')

    def _get_property_values_or_raise(self, name: str) -> tuple[ObjectProperty, list[PropertyValue]]:
        """Return the ObjectProperty and its PropertyValue instances for the given name.

        :param name: The name of the property to get.
        :return: A tuple containing the ObjectProperty and a list of its PropertyValue instances.
        :raise KeyError: If no property with the given name exists for this Object’s type.
        """
        prop = self.type[name]
        if not prop:
            raise KeyError(f'Undefined property "{name}" for object of type "{self.type.label}"')
        return prop, list(self.properties.filter(property_type__label=name))


class PropertyValue(_dj_models.Model):  # Cannot use generics with Django models (last checked 2024-01-24)
    """This class represents a value of an ObjectProperty for a given Object instance.

    If the associated ObjectProperty is unique, only one instance of this class can exist for a given Object instance.
    """

    object = _dj_models.ForeignKey(
        Object,
        on_delete=_dj_models.CASCADE,
        related_name='properties',
    )
    property_type = _dj_models.ForeignKey(
        ObjectProperty,
        on_delete=_dj_models.PROTECT,
        related_name='instances',
    )
    value: typing.Any  # Defined in sub-classes

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if self.property_type not in self.object.type:
            prop_name = self.property_type.label
            type_name = self.object.type.label
            raise _dj_exc.ValidationError(
                f'Property "{prop_name}" cannot be bound to object of type "{type_name}"',
                code='PropertyValue_cannot_bind_to_object'
            )

    def validate_unique(self, exclude: colabc.Collection[str] = None):
        super().validate_unique(exclude)
        if self.property_type.is_unique and self.object.properties.filter(property_type=self.property_type).exists():
            type_name = self.object.type.label
            prop_name = self.property_type.label
            raise _dj_exc.ValidationError(
                f'Object #{self.object.id} of type "{type_name}" already has a value'
                f' for its unique property "{prop_name}"',
                code='PropertyValue_duplicate'
            )


class BooleanPropertyValue(PropertyValue):
    """This class represents a boolean property value."""

    value = _dj_models.BooleanField()

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, BooleanProperty):
            raise _dj_exc.ValidationError(
                'Invalid boolean property type',
                code='BooleanPropertyValue_invalid_property_type'
            )


class NumberPropertyValue(PropertyValue):
    """This class represents a number property value."""

    unit = _dj_models.ForeignKey(
        Unit,
        on_delete=_dj_models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, NumberProperty):
            raise _dj_exc.ValidationError(
                'Invalid integer property type',
                code='NumberPropertyValue_invalid_property_type'
            )
        if not exclude or 'value' not in exclude:
            if self.value < self.property_type.min:
                raise _dj_exc.ValidationError('Value cannot be less than min',
                                              code='NumberPropertyValue_less_than_min')
            if self.value > self.property_type.max:
                raise _dj_exc.ValidationError('Value cannot be greater than max',
                                              code='NumberPropertyValue_greater_than_max')
        if not exclude or 'unit' not in exclude:
            if self.unit and self.property_type.unit_type and self.unit.type != self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Invalid unit type, expected {self.property_type.unit_type}, got {self.unit.type}',
                    code='NumberPropertyValue_mismatch_unit_type'
                )
            if self.unit and not self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Unexpected unit for property value',
                    code='NumberPropertyValue_unexpected_unit'
                )
            if not self.unit and self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Missing unit for property value',
                    code='NumberPropertyValue_missing_unit'
                )


class IntegerPropertyValue(PropertyValue):
    """This class represents an int property value."""

    value = _dj_models.IntegerField()

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, IntegerProperty):
            raise _dj_exc.ValidationError(
                'Invalid integer property type',
                code='IntegerPropertyValue_invalid_property_type'
            )


class FloatPropertyValue(PropertyValue):
    """This class represents a float property value."""

    value = _dj_models.FloatField()

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, FloatProperty):
            raise _dj_exc.ValidationError(
                'Invalid float property type',
                code='FloatPropertyValue_invalid_property_type'
            )


class StringPropertyValue(PropertyValue):
    """This class represents a string property value.
    If the property’s definition’s ``is_translatable`` field is True,
    StringPropertyValueTranslation instances may attached in order to provide translations.
    """

    value = _dj_models.TextField(
        validators=[non_empty_str],
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, StringProperty):
            raise _dj_exc.ValidationError(
                'Invalid string property type',
                code='StringPropertyValue_invalid_property_type'
            )
        if ((not exclude or 'value' not in exclude)
                and not self.property_type.is_multiline
                and ('\r' in self.value or '\n' in self.value)):
            raise _dj_exc.ValidationError(
                r'String value cannot contain \n nor \r',
                code='StringPropertyValue_forbidden_new_lines'
            )


class StringPropertyValueTranslation(Translation):
    """This class represents a translation of a StringPropertyValue’s value."""

    property_value = _dj_models.ForeignKey(
        StringPropertyValue,
        on_delete=_dj_models.CASCADE,
        related_name='translations',
    )

    class Meta:
        unique_together = ('property_value', 'language')

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        # noinspection PyTypeChecker
        property_type: StringProperty = self.property_value.property_type
        if not property_type.is_translatable:
            type_name = property_type.object_type.label
            prop_name = property_type.label
            raise _dj_exc.ValidationError(
                f'Cannot translate non-translatable string property "{type_name}.{prop_name}"',
                code='StringPropertyValueTranslation_non_translatable_property'
            )


class DateIntervalPropertyValue(PropertyValue):
    """This class represents a DateInterval property value."""

    value = _mf.DateIntervalField()

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, DateIntervalProperty):
            raise _dj_exc.ValidationError(
                'Invalid date interval property type',
                code='DateIntervalPropertyValue_invalid_property_type'
            )


class TypePropertyValue(PropertyValue):
    """This class represents a property value that accepts Object instances."""

    value = _dj_models.ForeignKey(
        Object,
        on_delete=_dj_models.CASCADE,
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, TypeProperty):
            raise _dj_exc.ValidationError(
                'Invalid type property type',
                code='TypePropertyValue_invalid_property_type'
            )


class TemporalPropertyValue(TypePropertyValue):
    """This class represents a property value that accepts Object instances whose type is temporal."""

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, TemporalProperty):
            raise _dj_exc.ValidationError(
                'Invalid type property type',
                code='TemporalPropertyValue_invalid_property_type'
            )
        if (not exclude or 'value' not in exclude) and not self.value.type.is_temporal:
            raise _dj_exc.ValidationError(
                'Target object is not temporal',
                code='TemporalPropertyValue_non_temporal_target_object'
            )
        if ((not exclude or 'value' not in exclude)
                and not self.property_type.allows_overlaps
                and any(self.object.existence_interval.overlaps(pv.object.existence_interval)
                        for pv in self.property_type.instances.filter(object=self.object))):
            raise _dj_exc.ValidationError(
                'Temporal object existence interval overlap',
                code='TemporalPropertyValue_existence_interval_overlap'
            )


class EnumPropertyValue(PropertyValue):
    """This class represents a property value that accepts EnumValue instances."""

    value = _dj_models.ForeignKey(
        EnumValue,
        on_delete=_dj_models.CASCADE,
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, EnumProperty):
            raise _dj_exc.ValidationError(
                'Invalid enum property type',
                code='EnumPropertyValue_invalid_property_type'
            )
        if (not exclude or 'value' not in exclude) and self.value.type != self.property_type.enum_type:
            raise _dj_exc.ValidationError(
                'Invalid enum property value',
                code='EnumPropertyValue_invalid_value'
            )


# endregion
# region Geometries


class Geometry(_dj_models.Model):
    """This class represents a geometry object, i.e. an object that exists on the Earth’s surface.
    Geometry objects may be attached to a single Object instance that holds data about this geometry.

    The ``layer`` field represents the drawing layer.
    A higher value means that the geometry is above those that have a lower value and vice-versa.
    """

    data_object = _dj_models.OneToOneField(
        Object,
        on_delete=_dj_models.CASCADE,
        null=True,
        blank=True,
        related_name='geometry',
    )
    layer = _dj_models.IntegerField(
        default=0,
    )
    geometry_type: str

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if ((not exclude or 'data_object' not in exclude)
                and not self.data_object.type.has_geometry_type(self.geometry_type)):
            raise _dj_exc.ValidationError(
                f'Expected data object type "point", got "{self.data_object.type.get_geometry_type()}',
                code='Geometry_invalid_data_object_type'
            )


class Point(Geometry):
    """This class represents a single point with a specific latitude and longitude."""

    geometry_type = 'Point'
    latitude = _dj_models.FloatField(
        validators=[latitude_validator],
    )
    longitude = _dj_models.FloatField(
        validators=[longitude_validator],
    )


class LineString(Geometry):
    """This class represents a line with.
    The direction is relative to the way the line was drawn.
    """

    geometry_type = 'LineString'
    vertices = _dj_models.ManyToManyField(
        Point,
        through='LineStringVertex',
        related_name='linestrings',
    )
    direction = _dj_models.IntegerField(
        choices=choices(1, -1, mapper=lambda v: ('Forward', 'Backward')[v]),
        default=1,
    )


class Polygon(Geometry):
    """This class represents a closed area.
    Polygons may have holes represented with the ``ring`` field of PolygonVertex."""

    geometry_type = 'Polygon'
    vertices = _dj_models.ManyToManyField(
        Point,
        through='PolygonVertex',
        related_name='polygons',
    )


class LineStringVertex(_dj_models.Model):
    """This class represents the position of a vertex on a LineString.
    Indices do not need to be contiguous. A point may be associated multiple times on a given LineString
    but it must have a different index each time.
    """

    polyline = _dj_models.ForeignKey(
        LineString,
        on_delete=_dj_models.CASCADE,
    )
    point = _dj_models.ForeignKey(
        Point,
        on_delete=_dj_models.CASCADE,
    )
    index = _dj_models.IntegerField(
        validators=[int_is_positive_or_zero],
    )

    class Meta:
        unique_together = ('polyline', 'point', 'index')


class PolygonVertex(_dj_models.Model):
    """This class represents the position of a vertex on a Polygon.
    Indices do not need to be contiguous. A point may be associated multiple times on a given LineString
    but it must have a different index or ring each time.
    """

    polygon = _dj_models.ForeignKey(
        Polygon,
        on_delete=_dj_models.CASCADE,
    )
    point = _dj_models.ForeignKey(
        Point,
        on_delete=_dj_models.CASCADE,
    )
    ring = _dj_models.IntegerField(
        validators=[int_is_positive_or_zero],
    )
    index = _dj_models.IntegerField(
        validators=[int_is_positive_or_zero],
    )

    class Meta:
        unique_together = ('polygon', 'point', 'ring', 'index')


class Note(_dj_models.Model):
    """This class represents a note left by a user on one or more geometries."""

    geometries = _dj_models.ManyToManyField(
        Geometry,
        related_name='notes',
    )
    author = _dj_models.ForeignKey(
        'CustomUser',
        on_delete=_dj_models.PROTECT,
        related_name='notes',
    )
    date = _dj_models.DateTimeField(
        auto_now_add=True,
    )
    text = _dj_models.TextField(
        validators=[non_empty_str],
    )


# endregion
# region Edit history


class EditGroup(_dj_models.Model):
    author = _dj_models.ForeignKey(
        'CustomUser',
        on_delete=_dj_models.PROTECT,
        related_name='edit_groups',
    )
    date = _dj_models.DateTimeField(
        auto_now_add=True,
    )
    sources = _dj_models.TextField(
        validators=[non_empty_str],
        null=True,
        blank=True,
        default=None,
    )
    comment = _dj_models.TextField(
        validators=[non_empty_str],
    )


class Edit(_dj_models.Model):
    # Internal database ID of object
    edit_group = _dj_models.ForeignKey(
        EditGroup,
        on_delete=_dj_models.CASCADE,
        related_name='edits',
    )
    object_id = _dj_models.IntegerField(
        validators=[int_is_positive],
    )
    model_type = _dj_models.CharField(
        max_length=10,
        choices=choices('Object', 'Point', 'LineString', 'Polygon', 'Note'),
    )

    def get_model_object(self) -> _dj_models.Model | None:
        try:
            return globals()[self.model_type].objects.get(id=self.object_id)
        except _dj_exc.ObjectDoesNotExist:
            return None


class ObjectEdit(Edit):
    object_type = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
    )


class ObjectCreationEdit(ObjectEdit):
    pass


class ObjectDeletionEdit(ObjectEdit):
    pass


class ObjectTypeEdit(ObjectEdit):
    old_type = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
    )


type ValueType = bool | Number | str | _dt.DateInterval | Object | EnumValue


class ObjectPropertyEdit(ObjectEdit):
    property_name = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
    )
    _serialized_value = _dj_models.TextField()

    def get_value(self) -> ValueType:
        return self._deserialize_value(self._serialized_value)

    def set_value(self, v: ValueType):
        self._serialized_value = self._serialize_value(v)

    @classmethod
    def _deserialize_value(cls, s: str) -> ValueType:
        match s.split(';', maxsplit=1):
            case ('b', str(b)):
                return int(b) != 0
            case ('i', str(i)):
                return cls._from_base64(i, 'q')
            case ('f', str(f)):
                return cls._from_base64(f, 'd')
            case ('s', str(s)):
                return s
            case ('D', str(di)):
                return _dt.DateInterval.parse(di)
            case ('O', str(obj_id)):
                return Object.objects.get(id=int(obj_id))
            case ('E', str(ev)):
                type_label, label = ev.split(',', maxsplit=1)
                return EnumValue.objects.get(type__label=type_label, label=label)

    @staticmethod
    def _from_base64(s: str, f: str):
        b = _b64.b64decode(s.encode('ascii'))
        return struct.unpack(f'>{f}', b)[0]

    @classmethod
    def _serialize_value(cls, v: ValueType):
        match v:
            case bool(b):
                return f'b;{int(b)}'
            case int(i):
                return f'i;{cls._to_base_64(i, 'q')}'
            case float(f):
                return f'f;{cls._to_base_64(f, 'd')}'
            case str(s):
                return f's;{s}'
            case di if isinstance(di, _dt.DateInterval):
                return f'D;{di!r}'
            case o if isinstance(o, Object):
                return f'O;{o.id}'
            case ev if isinstance(ev, EnumValue):
                return f'E;{ev.type.label},{ev.label}'
            case _:
                raise TypeError(f'Unexpected type "{type(v)}"')

    @staticmethod
    def _to_base_64(v, f: str) -> str:
        b = struct.pack(f'>{f}', v)
        return _b64.b64encode(b).decode('ascii')


class StringPropertyValueTranslationEdit(ObjectEdit):
    property_name = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
    )
    # Not using foreign key to Language model to keep information in case the language is deleted
    language_code = _dj_models.CharField(
        max_length=20,
    )
    translation = _dj_models.TextField(
        validators=[non_empty_str],
        null=True,  # Only allowed for 'delete' action
        blank=True,
    )
    action = _dj_models.CharField(
        max_length=6,
        choices=choices('add', 'delete', 'edit'),
    )

    def validate_constraints(self, exclude: colabc.Collection[str] = None):
        super().validate_constraints(exclude)
        if (not exclude or 'translation' not in exclude) and self.action != 'delete' and self.translation is None:
            raise _dj_exc.ValidationError(
                'translation field cannot be None unless action is "delete"',
                code='StringPropertyValueTranslationEdit_null_translation'
            )


class GeometryEdit(Edit):
    geometry_type = _dj_models.CharField(
        max_length=10,
        choices=GEOMETRY_TYPES,
    )


class GeometryCreationEdit(GeometryEdit):
    pass


class GeometryDeletionEdit(GeometryEdit):
    pass


class PointEdit(GeometryEdit):
    latitude = _dj_models.FloatField(
        validators=[latitude_validator],
    )
    longitude = _dj_models.FloatField(
        validators=[longitude_validator],
    )


class LineVertexEdit(GeometryEdit):
    action = _dj_models.CharField(
        max_length=6,
        choices=choices('add', 'delete', 'edit'),
    )
    index = _dj_models.IntegerField(
        validators=[int_is_positive_or_zero],
    )


class PolygonVertexEdit(LineVertexEdit):
    ring = _dj_models.IntegerField(
        validators=[int_is_positive_or_zero],
    )


class LayerEdit(GeometryEdit):
    layer = _dj_models.IntegerField()


class NoteEdit(Edit):
    pass


class NoteCreationEdit(NoteEdit):
    pass


class NoteDeletionEdit(NoteEdit):
    pass


class NoteTextEdit(NoteEdit):
    text = _dj_models.TextField(
        validators=[non_empty_str],
    )

# endregion
