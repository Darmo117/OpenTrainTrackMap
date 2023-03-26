import abc as _abc
import math as _math
import typing as _typ

import django.core.exceptions as _dj_exc
import django.core.validators as _dj_valid
import django.db.models as _dj_models

from . import _i18n_models as _i18n_m
from .. import model_fields as _mf
from ..api import constants as _cons


# region Meta-meta-model


class UnitType(_dj_models.Model):
    label = _dj_models.CharField(unique=True, max_length=30)


class Unit(_dj_models.Model):
    symbol = _dj_models.CharField(unique=True, max_length=10)
    type = _dj_models.ForeignKey(UnitType, on_delete=_dj_models.CASCADE, related_name='units')
    may_be_negative = _dj_models.BooleanField()
    to_base_unit_coef = _dj_models.FloatField()


def structure_label_validator(value: str):
    if not value.isascii() or not value.isalnum():
        raise _dj_exc.ValidationError('invalid structure label', code='structure_invalid_label')


class Structure(_dj_models.Model):
    label = _dj_models.CharField(max_length=50, validators=[structure_label_validator])
    deprecated = _dj_models.BooleanField()
    wikidata_qid = _dj_models.CharField(null=True, blank=True, max_length=15,
                                        validators=[_dj_valid.RegexValidator(r'^Q\d+$')])

    class Meta:
        abstract = True


class Type(Structure):
    is_abstract = _dj_models.BooleanField()
    enum = _dj_models.BooleanField()
    super_type = _dj_models.ForeignKey('self', on_delete=_dj_models.CASCADE, related_name='sub_types')

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if Type.objects.filter(_dj_models.Q(label=self.label) & ~_dj_models.Q(id=self.id)).exists():
            raise _dj_exc.ValidationError(
                f'type with label {self.label} already exist',
                code='type_duplicate'
            )

    def __str__(self):
        return self.label


def property_multiplicity_validator(m: int):
    if m < 0:
        raise _dj_exc.ValidationError(
            'negative property multiplicity',
            code='property_negative_multiplicity'
        )


class Property(Structure):
    # Common fields
    host_type = _dj_models.ForeignKey(Type, on_delete=_dj_models.CASCADE, related_name='properties')
    multiplicity_min = _dj_models.IntegerField(validators=[property_multiplicity_validator])
    multiplicity_max = _dj_models.IntegerField(validators=[property_multiplicity_validator], null=True, blank=True)
    is_temporal = _dj_models.BooleanField()
    absent_means_unknown_value = _dj_models.BooleanField(null=True, blank=True)
    is_value_unique = _dj_models.BooleanField()
    property_type = _dj_models.CharField(max_length=20, choices=tuple((v, v) for v in _cons.PROPERTY_TYPES))
    # Type property fields
    target_type = _dj_models.ForeignKey(Type, on_delete=_dj_models.PROTECT, related_name='targetting_properties',
                                        null=True, blank=True)
    allows_itself = _dj_models.BooleanField(null=True, blank=True)
    # Int property fields
    min_int = _dj_models.IntegerField(null=True, blank=True)
    max_int = _dj_models.IntegerField(null=True, blank=True)
    # Float property fields
    min_float = _dj_models.FloatField(null=True, blank=True)
    max_float = _dj_models.FloatField(null=True, blank=True)
    # Unit type property fields
    unit_type = _dj_models.ForeignKey(UnitType, on_delete=_dj_models.PROTECT, related_name='properties',
                                      null=True, blank=True)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if Property.objects.filter(_dj_models.Q(label=self.label, host_type__label=self.host_type.label)
                                   & ~_dj_models.Q(id=self.id)).exists():
            raise _dj_exc.ValidationError(
                f'property with name {self.label} already exists for type {self.host_type}',
                code='duplicate_property'
            )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        match self.property_type:
            case _cons.PROPERTY_TYPE:
                self._check_type_property()
            case _cons.PROPERTY_LOCALIZED:
                self._check_localized_property()
            case _cons.PROPERTY_STRING:
                self._check_string_property()
            case _cons.PROPERTY_INT:
                self._check_int_property()
            case _cons.PROPERTY_FLOAT:
                self._check_float_property()
            case _cons.PROPERTY_BOOLEAN:
                self._check_boolean_property()
            case _cons.PROPERTY_UNIT:
                self._check_unit_property()
            case _cons.PROPERTY_DATE_INTERVAL:
                self._check_date_interval_property()

        if self.multiplicity_min > self.multiplicity_max:
            raise _dj_exc.ValidationError('invalid property multiplicities', code='property_invalid_multiplicities')
        if not self.is_temporal and self.absent_means_unknown_value is not None:
            raise _dj_exc.ValidationError('property is not temporal', code='property_not_temporal')
        if self.is_temporal:
            if self.multiplicity_min > 0:
                raise _dj_exc.ValidationError('temporal property must have a min multipliticy of 0',
                                              code='temporal_property_invalid_min_multiplicity')
            if self.absent_means_unknown_value is None:
                raise _dj_exc.ValidationError('property is temporal', code='property_is_temporal')

    @staticmethod
    def _any_not_null(*fields) -> bool:
        return any(f is not None for f in fields)

    def _check_type_property(self):
        if self._any_not_null(self.min_int, self.max_int, self.min_float, self.max_float, self.unit_type):
            raise _dj_exc.ValidationError(
                'type property should only have common fields set',
                code='type_property_invalid_fields'
            )
        if self.target_type is None:
            raise _dj_exc.ValidationError(
                'missing target_type field',
                code='type_property_missing_target_type_field'
            )
        if self.allows_itself is None:
            raise _dj_exc.ValidationError(
                'missing allows_itself field',
                code='type_property_missing_allows_itself_field'
            )

    def _check_localized_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise _dj_exc.ValidationError(
                'localized property should only have common fields set',
                code='localized_property_invalid_fields'
            )
        if self.is_temporal:
            raise _dj_exc.ValidationError(
                'localized property cannot be temporal',
                code='localized_property_temporal'
            )

    def _check_string_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise _dj_exc.ValidationError(
                'string property should only have common fields set',
                code='string_property_invalid_fields'
            )

    def _check_int_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_float, self.max_float,
                              self.unit_type):
            raise _dj_exc.ValidationError(
                'int property should only have min_int and min_max fields set',
                code='int_property_invalid_fields'
            )
        if self.min_int is not None and self.max_int is not None:
            if self.min_int > self.max_int:
                raise _dj_exc.ValidationError(
                    'max should be greater than min',
                    code='int_property_invalid_bounds'
                )
            if self.min_int == self.max_int:
                raise _dj_exc.ValidationError(
                    'min and max must be different',
                    code='int_property_same_bounds'
                )

    def _check_float_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.unit_type):
            raise _dj_exc.ValidationError(
                'string property should only have min_float and max_float fields set',
                code='float_property_invalid_fields'
            )
        if self.min_float is not None and self.max_float is not None:
            if self.min_float > self.max_float:
                raise _dj_exc.ValidationError(
                    'max should be greater than min',
                    code='float_property_invalid_bounds'
                )
            if self.min_float == self.max_float:
                raise _dj_exc.ValidationError(
                    'min and max must be different',
                    code='float_property_same_bounds'
                )

    def _check_boolean_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise _dj_exc.ValidationError(
                'boolean property should only have common fields set',
                code='boolean_property_invalid_fields'
            )

    def _check_unit_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise _dj_exc.ValidationError(
                'unit property should only have unit_type field set',
                code='unit_property_invalid_fields'
            )
        if self.unit_type is None:
            raise _dj_exc.ValidationError(
                f'missing unit type for unit property {self.label}',
                code='unit_property_missing_unit_type'
            )

    def _check_date_interval_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise _dj_exc.ValidationError(
                'date interval property should only have common fields set',
                code='date_interval_property_invalid_fields'
            )
        if self.is_temporal:
            raise _dj_exc.ValidationError(
                'date interval property cannot be temporal',
                code='date_interval_property_temporal'
            )

    def __str__(self):
        return f'{self.host_type.label}.{self.label}'


# endregion
# region Meta-model


class Object(_dj_models.Model):
    type = _dj_models.ForeignKey(Type, on_delete=_dj_models.PROTECT, related_name='instances')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.type.is_abstract:
            raise _dj_exc.ValidationError('abstract types cannot have instances', code='object_with_abstract_type')


class Relation(_dj_models.Model):
    # Common fields
    property = _dj_models.ForeignKey(Property, on_delete=_dj_models.PROTECT, related_name='instances')
    left_object = _dj_models.ForeignKey(Object, on_delete=_dj_models.CASCADE, related_name='relations_left')
    existence_interval = _mf.DateIntervalField()
    # Object relation fields
    right_object = _dj_models.ForeignKey(Object, on_delete=_dj_models.CASCADE, related_name='relations_right',
                                         null=True, blank=True)
    # Localized relation fields
    language_code = _dj_models.ForeignKey(_i18n_m.Language, on_delete=_dj_models.PROTECT, null=True, blank=True)
    value_localized_p = _dj_models.TextField(null=True, blank=True)
    # String relation fields
    value_string_p = _dj_models.CharField(max_length=200, null=True, blank=True)
    # Int relation fields
    value_int_p = _dj_models.IntegerField(null=True, blank=True)
    # Float relation fields
    value_float_p = _dj_models.FloatField(null=True, blank=True)
    # Boolean relation fields
    value_boolean_p = _dj_models.BooleanField(null=True, blank=True)
    # Unit relation fields
    value_unit_p = _dj_models.FloatField(null=True, blank=True)
    unit = _dj_models.ForeignKey(Unit, on_delete=_dj_models.PROTECT, related_name='relations', null=True, blank=True)
    # Date interval relation fields
    value_date_interval_p = _mf.DateIntervalField(null=True, blank=True)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.property.is_value_unique:
            k = self._get_right_value_attribute_name()
            filters = _dj_models.Q(**{
                'property': self.property,
                'left_object': self.left_object,
                k: getattr(self, k),
            })
            if Relation.objects.filter(filters & ~_dj_models.Q(id=self.id)).exists():
                raise _dj_exc.ValidationError(
                    f'duplicate value for property {self.property}',
                    code='relation_duplicate_for_unique_property'
                )

        match self.property.property_type:
            case _cons.PROPERTY_LOCALIZED:
                if Relation.objects.filter(_dj_models.Q(language_code=self.language_code, left_object=self.left_object)
                                           & ~_dj_models.Q(id=self.id)).exists():
                    raise _dj_exc.ValidationError(
                        f'duplicate localization for language {self.language_code} and object {self.left_object}',
                        code='localized_relation_duplicate'
                    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        match self.property.property_type:
            case _cons.PROPERTY_TYPE:
                self._check_object_relation()
            case _cons.PROPERTY_LOCALIZED:
                self._check_localized_relation()
            case _cons.PROPERTY_STRING:
                self._check_string_relation()
            case _cons.PROPERTY_INT:
                self._check_int_relation()
            case _cons.PROPERTY_FLOAT:
                self._check_float_relation()
            case _cons.PROPERTY_BOOLEAN:
                self._check_boolean_relation()
            case _cons.PROPERTY_UNIT:
                self._check_unit_relation()
            case _cons.PROPERTY_DATE_INTERVAL:
                self._check_date_interval_relation()

        if self.property.is_temporal and self.existence_interval is None:
            raise _dj_exc.ValidationError(
                'temporal relation must have an associated date interval',
                code='temporal_relation_without_date_interval'
            )

        maxi = self.property.multiplicity_max or _math.inf
        if not self.property.is_temporal:
            if Relation.objects.filter(left_object=self.left_object, property=self.property).count() >= maxi:
                raise _dj_exc.ValidationError(
                    f'too many relations for property {self.property} on object {self.left_object}',
                    code='too_many_relations'
                )
        else:
            def overlaps(f: tuple[str, _typ.Any] = None):
                filters = {
                    'property': self.property,
                    'left_object': self.left_object,
                    **({f[0]: f[1]} if f else {})
                }
                # TODO if possible, delegate to SQL
                return any(relation.existence_interval.overlaps(self.existence_interval)
                           for relation in Relation.objects.filter(**filters))

            if maxi == 1 and overlaps():
                raise _dj_exc.ValidationError(
                    f'overlapping date intervals for temporal property {self.property}',
                    code='temporal_relation_overlap_single_value'
                )
            elif maxi > 1:
                k = self._get_right_value_attribute_name()
                v = getattr(self, k)
                if overlaps((k, v)):
                    raise _dj_exc.ValidationError(
                        f'overlapping date intervals for property {self.property} and value {v}',
                        code='temporal_relation_overlap_many_values'
                    )

    def _get_right_value_attribute_name(self) -> str:
        match self.property.property_type:
            case _cons.PROPERTY_TYPE:
                return 'right_object'
            case _cons.PROPERTY_LOCALIZED:
                return 'value_localized_p'
            case _cons.PROPERTY_STRING:
                return 'value_string_p'
            case _cons.PROPERTY_INT:
                return 'value_int_p'
            case _cons.PROPERTY_FLOAT:
                return 'value_float_p'
            case _cons.PROPERTY_BOOLEAN:
                return 'value_boolean_p'
            case _cons.PROPERTY_UNIT:
                return 'value_unit_p'
            case _cons.PROPERTY_DATE_INTERVAL:
                return 'value_date_interval_p'

    @staticmethod
    def _any_not_null(*fields) -> bool:
        return any(f is not None for f in fields)

    def _check_object_relation(self):
        if self._any_not_null(
                self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p, self.value_float_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise _dj_exc.ValidationError(
                'object relation should only have right_object field set',
                code='object_relation_invalid_fields'
            )
        if self.right_object is None:
            raise _dj_exc.ValidationError(
                'missing right object',
                code='object_relation_missing_right_object'
            )
        if not self.property.allows_itself and self.left_object == self.right_object:
            raise _dj_exc.ValidationError(
                'relation not allowed to have same object on both sides',
                code='object_relation_same_object_on_both_sides'
            )

    def _check_localized_relation(self):
        if self._any_not_null(
                self.right_object, self.value_string_p, self.value_int_p, self.value_float_p, self.value_boolean_p,
                self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise _dj_exc.ValidationError(
                'localized relation should only have language_code and value_localized_p fields set',
                code='localized_relation_invalid_fields'
            )
        if self.language_code is None:
            raise _dj_exc.ValidationError(
                'missing language code',
                code='localized_relation_missing_language_code'
            )
        if self.value_localized_p is None:
            raise _dj_exc.ValidationError(
                'missing localized value',
                code='localized_relation_missing_language_code'
            )

    def _check_string_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_int_p, self.value_float_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise _dj_exc.ValidationError(
                'string relation should only have value_string_p field set',
                code='string_relation_invalid_fields'
            )
        if self.value_string_p is None:
            raise _dj_exc.ValidationError(
                'missing string value',
                code='string_relation_missing_value'
            )

    def _check_int_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_float_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise _dj_exc.ValidationError(
                'int relation should only have value_int_p field set',
                code='int_relation_invalid_fields'
            )
        if self.value_int_p is None:
            raise _dj_exc.ValidationError(
                'missing int value',
                code='int_relation_missing_value'
            )
        if (self.property.min_int is not None and self.value_int_p < self.property.min_int
                or self.property.max_int is not None and self.value_int_p > self.property.max_int):
            raise _dj_exc.ValidationError(
                f'{self.value_int_p} outside of [{self.property.min_int}, {self.property.max_int}]',
                code='int_relation_invalid_value'
            )

    def _check_float_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise _dj_exc.ValidationError(
                'float relation should only have value_float_p field set',
                code='float_relation_invalid_fields'
            )
        if self.value_int_p is None:
            raise _dj_exc.ValidationError(
                'missing float value',
                code='float_relation_missing_value'
            )
        if (self.property.min_float is not None and self.value_float_p < self.property.min_float
                or self.property.max_float is not None and self.value_float_p > self.property.max_float):
            raise _dj_exc.ValidationError(
                f'{self.value_float_p} outside of [{self.property.min_float}, {self.property.max_float}]',
                code='float_relation_invalid_value'
            )

    def _check_boolean_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_float_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise _dj_exc.ValidationError(
                'boolean relation should only have value_boolean_p field set',
                code='boolean_relation_invalid_fields'
            )
        if self.value_boolean_p is None:
            raise _dj_exc.ValidationError(
                'missing boolean value',
                code='boolean_relation_missing_value'
            )

    def _check_unit_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_float_p, self.value_boolean_p, self.value_date_interval_p
        ):
            raise _dj_exc.ValidationError(
                'unit relation should only have value_boolean_p field set',
                code='unit_relation_invalid_fields'
            )
        if self.value_unit_p is None:
            raise _dj_exc.ValidationError(
                'missing unit value',
                code='unit_relation_missing_value'
            )
        if self.unit is None:
            raise _dj_exc.ValidationError(
                'missing unit',
                code='unit_relation_missing_unit'
            )
        if not self.unit.may_be_negative and self.value_unit_p < 0:
            raise _dj_exc.ValidationError(
                'value cannot be negative',
                code='unit_relation_negative_value'
            )

    def _check_date_interval_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_float_p, self.value_boolean_p, self.value_unit_p, self.unit
        ):
            raise _dj_exc.ValidationError(
                'date interval relation should only have value_date_interval_p field set',
                code='date_interval_relation_invalid_fields'
            )
        if self.value_date_interval_p is None:
            raise _dj_exc.ValidationError(
                'missing date interval',
                code='date_interval_missing_value'
            )
        if self.property.is_temporal:
            raise _dj_exc.ValidationError(
                'date interval relation cannot be temporal',
                code='temporal_date_interval_relation'
            )


# endregion
# region Edit System


class EditGroup(_dj_models.Model):
    date = _dj_models.DateTimeField()
    author = _dj_models.ForeignKey('CustomUser', on_delete=_dj_models.PROTECT, related_name='edit_groups')

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if EditGroup.objects.filter(_dj_models.Q(date=self.date, author=self.author)
                                    & ~_dj_models.Q(id=self.id)).exists():
            # noinspection PyUnresolvedReferences
            raise _dj_exc.ValidationError(
                f'user {self.user.user.username} cannot make multiple edits at the exact same time',
                code='edit_group_duplicate_date'
            )


def _edit_validate_object_id(i: int):
    if i < 0:
        raise _dj_exc.ValidationError(
            f'invalid object ID {i}',
            code='edit_invalid_object_id'
        )


class Edit(_dj_models.Model):
    edit_group = _dj_models.ForeignKey(EditGroup, on_delete=_dj_models.CASCADE)
    object_id = _dj_models.IntegerField(validators=[_edit_validate_object_id])

    class Meta:
        abstract = True


class ObjectEdit(Edit):
    object_type = _dj_models.ForeignKey(Type, on_delete=_dj_models.CASCADE)
    operation = _dj_models.CharField(max_length=10, choices=tuple((v, v) for v in _cons.OBJECT_EDIT_ACTIONS))


class RelationEdit(Edit):
    property_name = _dj_models.ForeignKey(Relation, on_delete=_dj_models.CASCADE, related_name='edits')
    old_value = _dj_models.JSONField(null=True, blank=True)
    new_value = _dj_models.JSONField(null=True, blank=True)
    operation = _dj_models.CharField(max_length=10, choices=tuple((v, v) for v in _cons.RELATION_EDIT_ACTIONS))

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.old_value is None and self.new_value is None:
            raise _dj_exc.ValidationError(
                'old and new value cannot both be None',
                code='relation_edit_missing_values'
            )


# endregion
# region Translations


class Translation(_dj_models.Model):
    language_code = _dj_models.ForeignKey(_i18n_m.Language, on_delete=_dj_models.PROTECT)
    label = _dj_models.CharField(max_length=100)

    class Meta:
        abstract = True

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        k = self._get_object_attr_name()
        obj = getattr(self, k)
        filters = _dj_models.Q(**{
            'language_code': self.language_code,
            'label': self.label,
            k: obj,
        })
        if Translation.objects.filter(filters & ~_dj_models.Q(id=self.id)).exists():
            raise _dj_exc.ValidationError(f'duplicate translation for object {obj} and language {self.language_code}',
                                          code='duplicate_translation')

    @classmethod
    @_abc.abstractmethod
    def _get_object_attr_name(cls) -> str:
        pass


class TypeTranslation(Translation):
    type = _dj_models.ForeignKey(Type, on_delete=_dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'type'


class PropertyTranslation(Translation):
    property = _dj_models.ForeignKey(Property, on_delete=_dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'property'


class UnitTypeTranslation(Translation):
    unit_type = _dj_models.ForeignKey(UnitType, on_delete=_dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'unit_type'


class UnitTranslation(Translation):
    unit = _dj_models.ForeignKey(Unit, on_delete=_dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'unit'

# endregion
