from __future__ import annotations

import base64 as _b64
import re
import struct
import typing

import django.core.exceptions as _dj_exc
import django.db.models as _dj_models

from . import _i18n_models as _i18n
from .. import model_fields as _mf
from ..api import data_types as _dt

# TODO check temporal states overlaps in API

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


class Translation(_dj_models.Model):
    language = _dj_models.ForeignKey(
        _i18n.Language,
        on_delete=_dj_models.PROTECT,
    )
    name = _dj_models.TextField(
        validators=[non_empty_str],
    )
    description = _dj_models.TextField(
        null=True,
        blank=True,
        default=None,
    )

    class Meta:
        abstract = True


class UnitType(_dj_models.Model):
    label = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
        unique=True,
    )


class UnitTypeTranslation(Translation):
    unit_type = _dj_models.ForeignKey(
        UnitType,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('unit_type', 'language')


class EnumType(_dj_models.Model):
    label = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
        unique=True,
    )

    def get_values(self) -> list[str]:
        return [v.label for v in EnumValue.objects.filter(type=self)]

    def has_value(self, v: str | EnumValue) -> bool:
        if isinstance(v, str):
            return self._value_exists(v)
        return v.type == self and self._value_exists(v.label)

    def _value_exists(self, v):
        return self.enumvalue_set.filter(type=self, label=v).exists()


class EnumTypeTranslation(Translation):
    enum_type = _dj_models.ForeignKey(
        EnumType,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('enum_type', 'language')


class EnumValue(_dj_models.Model):
    type = _dj_models.ForeignKey(
        EnumType,
        on_delete=_dj_models.CASCADE,
    )
    label = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
    )

    class Meta:
        unique_together = ('type', 'label')


class EnumValueTranslation(Translation):
    enum_value = _dj_models.ForeignKey(
        EnumValue,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('enum_value', 'language')


GEOMETRY_TYPES = choices('Point', 'LineString', 'Polygon')


class ObjectType(_dj_models.Model):
    label = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
        unique=True,
    )
    geometry_type = _dj_models.CharField(
        max_length=10,
        choices=((None, 'None'), *GEOMETRY_TYPES),
        null=True,
        blank=True,
        default=None,
    )
    parent_type = _dj_models.ForeignKey(
        'self',
        on_delete=_dj_models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )

    def validate_constraints(self, exclude=None):
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
        return self.parent_type and (
                self.parent_type is of or self.parent_type._detect_type_loop(of))

    def _detect_geometry_type_conflict(self) -> bool:
        return self.geometry_type and (self.parent_type and self.parent_type.geometry_type == self.geometry_type
                                       or self.parent_type._detect_geometry_type_conflict())

    def has_property_with_label(self, label: str) -> bool:
        return (self.properties.filter(label=label) or
                self.parent_type and self.parent_type.has_property_with_label(label))

    def has_property(self, object_property: ObjectProperty) -> bool:
        return (self.properties.contains(object_property) or
                self.parent_type and self.parent_type.has_property(object_property))

    def has_geometry_type(self, geometry_type: str) -> bool:
        return (self.geometry_type == geometry_type
                or self.parent_type and self.parent_type.has_geometry_type(geometry_type))

    def get_geometry_type(self) -> str | None:
        return self.geometry_type or self.parent_type and self.parent_type.get_geometry_type()


class ObjectTypeTranslation(Translation):
    object_type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.CASCADE,
    )
    deprecated = _dj_models.BooleanField(
        default=False,
    )

    class Meta:
        unique_together = ('object_type', 'language')


class ObjectProperty(_dj_models.Model):
    object_type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.PROTECT,
        related_name='properties',
    )
    label = _dj_models.CharField(
        max_length=IDENTIFIER_LENGTH,
        validators=[identifier_str],
    )
    unique = _dj_models.BooleanField(
        default=True,
    )
    deprecated = _dj_models.BooleanField(
        default=False,
    )

    class Meta:
        unique_together = ('object_type', 'label')

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)
        # No need to check on object_type as the meta class already defines this unicity constraint
        if self.object_type.parent_type and self.object_type.parent_type.has_property_with_label(self.label):
            raise _dj_exc.ValidationError(
                f'A parent of type "{self.object_type.label}" already has a property named "{self.label}"',
                code='ObjectProperty_duplicate'
            )


class ObjectPropertyTranslation(Translation):
    object_property = _dj_models.ForeignKey(
        ObjectProperty,
        on_delete=_dj_models.CASCADE,
    )

    class Meta:
        unique_together = ('object_property', 'language')


class BooleanProperty(ObjectProperty):
    pass


class IntegerProperty(ObjectProperty):
    min = _dj_models.IntegerField()
    max = _dj_models.IntegerField()
    unit_type = _dj_models.ForeignKey(
        UnitType,
        on_delete=_dj_models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'min' not in exclude and 'max' not in exclude) and self.min >= self.max:
            raise _dj_exc.ValidationError('Invalid min/max values', code='invalid_int_property_min_max')


class FloatProperty(ObjectProperty):
    min = _dj_models.FloatField()
    max = _dj_models.FloatField()
    unit_type = _dj_models.ForeignKey(
        UnitType,
        on_delete=_dj_models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'min' not in exclude and 'max' not in exclude) and self.min >= self.max:
            raise _dj_exc.ValidationError('Invalid min/max values', code='invalid_float_property_min_max')


class StringProperty(ObjectProperty):
    translatable = _dj_models.BooleanField(
        default=False,
    )


class DateIntervalProperty(ObjectProperty):
    pass


class TypeProperty(ObjectProperty):
    target_type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.PROTECT,
    )


class EnumProperty(ObjectProperty):
    enum_type = _dj_models.ForeignKey(
        EnumType,
        on_delete=_dj_models.PROTECT,
    )


# endregion
# region Instances


class Unit(_dj_models.Model):
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


class Object(_dj_models.Model):
    type = _dj_models.ForeignKey(
        ObjectType,
        on_delete=_dj_models.PROTECT,
        related_name='instances',
    )


class ObjectPropertyValue(_dj_models.Model):  # Cannot use generics with Django models (last checked 2024-01-24)
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
    date_interval = _mf.DateIntervalField(
        null=True,
        blank=True,
    )
    value: typing.Any  # Implemented in sub-classes

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if not self.object.type.has_property(self.property_type):
            prop_name = self.property_type.label
            type_name = self.object.type.label
            raise _dj_exc.ValidationError(
                f'Property "{prop_name}" cannot be bound to object of type "{type_name}"',
                code='ObjectPropertyValue_cannot_bind_to_object'
            )

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)
        if self.property_type.unique and self.object.properties.filter(property_type=self.property_type).exists():
            type_name = self.object.type.label
            prop_name = self.property_type.label
            raise _dj_exc.ValidationError(
                f'Object #{self.object.id} of type "{type_name}" already has a value'
                f' for its unique property "{prop_name}"',
                code='ObjectPropertyValue_duplicate'
            )


class BooleanPropertyValue(ObjectPropertyValue):
    value = _dj_models.BooleanField()

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, BooleanProperty):
            raise _dj_exc.ValidationError(
                'Invalid boolean property type',
                code='BooleanPropertyValue_invalid_property_type'
            )


class IntegerPropertyValue(ObjectPropertyValue):
    value = _dj_models.IntegerField()
    unit = _dj_models.ForeignKey(
        Unit,
        on_delete=_dj_models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, IntegerProperty):
            raise _dj_exc.ValidationError(
                'Invalid integer property type',
                code='IntegerPropertyValue_invalid_property_type'
            )
        if not exclude or 'value' not in exclude:
            if self.value < self.property_type.min:
                raise _dj_exc.ValidationError('Value cannot be less than min',
                                              code='IntegerPropertyValue_less_than_min')
            if self.value > self.property_type.max:
                raise _dj_exc.ValidationError('Value cannot be greater than max',
                                              code='IntegerPropertyValue_greater_than_max')
        if not exclude or 'unit' not in exclude:
            if self.unit and self.property_type.unit_type and self.unit.type != self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Invalid unit type, expected {self.property_type.unit_type}, got {self.unit.type}',
                    code='IntegerPropertyValue_mismatch_unit_type'
                )
            if self.unit and not self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Unexpected unit for property value',
                    code='IntegerPropertyValue_unexpected_unit'
                )
            if not self.unit and self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Missing unit for property value',
                    code='IntegerPropertyValue_missing_unit'
                )


class FloatPropertyValue(ObjectPropertyValue):
    value = _dj_models.FloatField()
    unit = _dj_models.ForeignKey(
        Unit,
        on_delete=_dj_models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, FloatProperty):
            raise _dj_exc.ValidationError(
                'Invalid float property type',
                code='FloatPropertyValue_invalid_property_type'
            )
        if not exclude or 'value' not in exclude:
            if self.value < self.property_type.min:
                raise _dj_exc.ValidationError('Value cannot be less than min',
                                              code='FloatPropertyValue_less_than_min')
            if self.value > self.property_type.max:
                raise _dj_exc.ValidationError('Value cannot be greater than max',
                                              code='FloatPropertyValue_greater_than_max')
        if not exclude or 'unit' not in exclude:
            if self.unit and self.property_type.unit_type and self.unit.type != self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Invalid unit type, expected {self.property_type.unit_type}, got {self.unit.type}',
                    code='FloatPropertyValue_mismatch_unit_type'
                )
            if self.unit and not self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Unexpected unit for property value',
                    code='FloatPropertyValue_unexpected_unit'
                )
            if not self.unit and self.property_type.unit_type:
                raise _dj_exc.ValidationError(
                    f'Missing unit for property value',
                    code='FloatPropertyValue_missing_unit'
                )


class StringPropertyValue(ObjectPropertyValue):
    value = _dj_models.TextField(
        validators=[non_empty_str],
    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, StringProperty):
            raise _dj_exc.ValidationError(
                'Invalid string property type',
                code='StringPropertyValue_invalid_property_type'
            )


class StringPropertyValueTranslation(_dj_models.Model):
    property_value = _dj_models.ForeignKey(
        StringPropertyValue,
        on_delete=_dj_models.CASCADE,
        related_name='translations',
    )
    language = _dj_models.ForeignKey(
        _i18n.Language,
        on_delete=_dj_models.PROTECT,
    )
    text = _dj_models.TextField(
        validators=[non_empty_str],
    )

    class Meta:
        unique_together = ('property_value', 'language')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        # noinspection PyUnresolvedReferences
        if not self.property_value.property_type.translatable:
            type_name = self.property_value.property_type.object_type.label
            prop_name = self.property_value.property_type.label
            raise _dj_exc.ValidationError(
                f'Cannot translate non-translatable string property "{type_name}.{prop_name}"',
                code='StringPropertyValueTranslation_non_translatable_property'
            )


class DateIntervalPropertyValue(ObjectPropertyValue):
    value = _mf.DateIntervalField()

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, DateIntervalProperty):
            raise _dj_exc.ValidationError(
                'Invalid date interval property type',
                code='DateIntervalPropertyValue_invalid_property_type'
            )


class TypePropertyValue(ObjectPropertyValue):
    value = _dj_models.ForeignKey(
        Object,
        on_delete=_dj_models.CASCADE,
    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, TypeProperty):
            raise _dj_exc.ValidationError(
                'Invalid type property type',
                code='TypePropertyValue_invalid_property_type'
            )


class EnumPropertyValue(ObjectPropertyValue):
    value = _dj_models.ForeignKey(
        EnumValue,
        on_delete=_dj_models.CASCADE,
    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if (not exclude or 'property_type' not in exclude) and not isinstance(self.property_type, EnumProperty):
            raise _dj_exc.ValidationError(
                'Invalid enum property type',
                code='EnumPropertyValue_invalid_property_type'
            )
        if (not exclude or 'value' not in exclude) and not self.property_type.enum_type.has_value(self.value):
            raise _dj_exc.ValidationError(
                'Invalid enum property value',
                code='EnumPropertyValue_invalid_value'
            )


# endregion
# region Geometries


class Geometry(_dj_models.Model):
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

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if ((not exclude or 'data_object' not in exclude)
                and not self.data_object.type.has_geometry_type(self.geometry_type)):
            raise _dj_exc.ValidationError(
                f'Expected data object type "point", got "{self.data_object.type.get_geometry_type()}',
                code='Geometry_invalid_data_object_type'
            )


class Point(Geometry):
    geometry_type = 'Point'
    latitude = _dj_models.FloatField(
        validators=[latitude_validator],
    )
    longitude = _dj_models.FloatField(
        validators=[longitude_validator],
    )


class LineString(Geometry):
    geometry_type = 'LineString'
    vertices = _dj_models.ManyToManyField(
        Point,
        through='LineStringVertex',
        related_name='linestrings',
    )
    # direction = _dj_models.IntegerField(
    #     choices=choices(1, -1, mapper=lambda v: [None, 'Forward', 'Backward'][v]),
    #     default=1,
    # )


class Polygon(Geometry):
    geometry_type = 'Polygon'
    vertices = _dj_models.ManyToManyField(
        Point,
        through='PolygonVertex',
        related_name='polygons',
    )


class LineStringVertex(_dj_models.Model):
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


class PolygonVertex(_dj_models.Model):
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


class Note(_dj_models.Model):
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

    def validate_constraints(self, exclude=None):
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
