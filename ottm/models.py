from __future__ import annotations

import abc
import typing as typ

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_auth_models
import django.core.exceptions as dj_exc
import django.core.validators as dj_valid
import django.db.models as dj_models

from . import settings, model_fields, data_types


def lang_code_validator(value: str):
    if value not in settings.LANGUAGES:
        raise dj_exc.ValidationError(f'invalid language code "{value}"', code='invalid_language')


#########
# Users #
#########


class UserInfo(dj_models.Model):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), on_delete=dj_models.CASCADE, related_name='ottm_user_info')
    prefered_language_code = dj_models.CharField(max_length=5, validators=[lang_code_validator])
    is_administrator = dj_models.BooleanField(default=False)

    @property
    def prefered_language(self) -> settings.Language:
        return settings.LANGUAGES[self.prefered_language_code]


class User:
    """Simple wrapper class for a Django user and its associated user data."""

    def __init__(self, django_user: dj_auth_models.AbstractUser, data: UserInfo | None):
        self._django_user = django_user
        self._data = data

    @property
    def django_user(self) -> dj_auth_models.AbstractUser:
        return self._django_user

    @property
    def data(self) -> UserInfo | None:
        return self._data

    @property
    def username(self) -> str:
        return self._django_user.username

    @property
    def is_logged_in(self) -> bool:
        return self._django_user.is_authenticated

    @property
    def prefered_language(self) -> settings.Language:
        return self._data.prefered_language if self._data else settings.LANGUAGES[settings.DEFAULT_LANGUAGE]

    @property
    def is_admin(self) -> bool:
        return not self._data or self._data.is_administrator

    def notes_count(self) -> int:
        """Return the total number of notes created by this user."""
        return (ObjectCreatedEdit.objects  # Get all object creation edits
                # Keep only those made by this user that are of type "Note"
                .filter(edit_group__author=self._data, object_type__label='Note')
                .count())

    def edits_count(self) -> int:
        """Return the total number of edits on objects and relations made by this user."""
        return (self._data.edits_groups  # Get all edit groups for this user
                .annotate(edits_count=dj_models.Count('edits'))  # Count number of edits for each group
                .aggregate(dj_models.Sum('edits_count')))  # Sum all counts

    def edit_groups_count(self) -> int:
        """Return the number of edit groups made by this user."""
        return self._data.edits_groups.count()

    def wiki_edits_count(self) -> int:
        import WikiPy.api.users as wpy_api_users
        return len(wpy_api_users.get_user_contributions(wpy_api_users.get_user_from_name(self.username), self.username))

    def __repr__(self):
        return f'User[django_user={self._django_user.username},data={self._data}]'


###################
# Meta-meta-model #
###################


class Structure(dj_models.Model, abc.ABC):
    label = dj_models.CharField(max_length=50)
    deprecated = dj_models.BooleanField()
    wikidata_qid = dj_models.CharField(null=True, blank=True, max_length=15,
                                       validators=[dj_valid.RegexValidator(r'^Q\d+$')])

    class Meta:
        abstract = True

    def __str__(self):
        return self.label

    def __repr__(self):
        return f'Structure[label={self.label},deprecated={self.deprecated},wikidata_qid={self.wikidata_qid}]'


class Type(Structure):
    is_abstract = dj_models.BooleanField()
    enum = dj_models.BooleanField()
    super_type = dj_models.ForeignKey('self', on_delete=dj_models.CASCADE, related_name='sub_types')

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(label=self.label).exists():
            raise dj_exc.ValidationError(f'type with label {self.label} already exist', code='type_duplicate')


class Property(Structure, abc.ABC):
    @staticmethod
    def _multiplicity_validator(m: int):
        if m < 0:
            raise dj_exc.ValidationError('negative property multiplicity', code='property_negative_multiplicity')

    multiplicity_min = dj_models.IntegerField(validators=[_multiplicity_validator])
    multiplicity_max = dj_models.IntegerField(validators=[_multiplicity_validator])
    is_temporal = dj_models.BooleanField()
    absent_means_unknown_value = dj_models.BooleanField(null=True, blank=True)
    is_value_unique = dj_models.BooleanField()
    host_type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE, related_name='properties')

    class Meta:
        abstract = True

    @classmethod
    @abc.abstractmethod
    def relation_class(cls) -> typ.Type[Relation]:
        pass

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(label=self.label, host_type__label=self.host_type.label).exists():
            raise ValueError(f'property with name {self.label} already exists for class {self.host_type}')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.multiplicity_min > self.multiplicity_max:
            raise dj_exc.ValidationError('invalid property multiplicities', code='property_invalid_multiplicities')
        if not self.is_temporal and self.absent_means_unknown_value is not None:
            raise dj_exc.ValidationError('property is not temporal', code='property_not_temporal')
        if self.is_temporal:
            if self.multiplicity_min > 0:
                raise dj_exc.ValidationError('temporal property must have a min multipliticy of 0',
                                             code='temporal_property_invalid_min_multiplicity')
            if self.absent_means_unknown_value is None:
                raise dj_exc.ValidationError('property is temporal', code='property_is_temporal')


class TypeProperty(Property):
    target_type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE, related_name='targetting_properties')
    allows_itself = dj_models.BooleanField()

    @classmethod
    def relation_class(cls):
        return ObjectRelation


class PrimitiveProperty(Property, abc.ABC):
    class Meta:
        abstract = True


class StringProperty(PrimitiveProperty):
    @classmethod
    def relation_class(cls) -> typ.Type[StringRelation]:
        return StringRelation


class LocalizedProperty(PrimitiveProperty):
    @classmethod
    def relation_class(cls) -> typ.Type[LocalizedRelation]:
        return LocalizedRelation


class IntProperty(PrimitiveProperty):
    min = dj_models.IntegerField(null=True, blank=True)
    max = dj_models.IntegerField(null=True, blank=True)

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise dj_exc.ValidationError('max should be greater than min', code='int_property_invalid_bounds')
            if self.min == self.max:
                raise dj_exc.ValidationError('min and max must be different', code='int_property_same_bounds')

    @classmethod
    def relation_class(cls) -> typ.Type[IntRelation]:
        return IntRelation


class FloatProperty(PrimitiveProperty):
    min = dj_models.FloatField()
    max = dj_models.FloatField()

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise dj_exc.ValidationError('max should be greater than min', code='float_property_invalid_bounds')
            if self.min == self.max:
                raise dj_exc.ValidationError('min and max must be different', code='float_property_same_bounds')

    @classmethod
    def relation_class(cls) -> typ.Type[FloatRelation]:
        return FloatRelation


class BooleanProperty(PrimitiveProperty):
    @classmethod
    def relation_class(cls) -> typ.Type[BooleanRelation]:
        return BooleanRelation


class UnitType(dj_models.Model):
    label = dj_models.CharField(unique=True, max_length=30)


class Unit(dj_models.Model):
    symbol = dj_models.CharField(unique=True, max_length=10)
    type = dj_models.ForeignKey(UnitType, on_delete=dj_models.CASCADE, related_name='units')
    may_be_negative = dj_models.BooleanField()
    to_base_unit_coef = dj_models.FloatField()


class UnitProperty(PrimitiveProperty):
    unit_type = dj_models.ForeignKey(UnitType, on_delete=dj_models.CASCADE, related_name='properties')

    @classmethod
    def relation_class(cls) -> typ.Type[UnitRelation]:
        return UnitRelation


class DateIntervalProperty(PrimitiveProperty):
    @classmethod
    def relation_class(cls) -> typ.Type[DateIntervalRelation]:
        return DateIntervalRelation


##############
# Meta-model #
##############


class Object(dj_models.Model):
    type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE, related_name='instances')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.type.is_abstract:
            raise dj_exc.ValidationError('abstract types cannot have instances', code='object_with_abstract_type')


class Relation(dj_models.Model, abc.ABC):
    left_object = dj_models.ForeignKey(Object, on_delete=dj_models.CASCADE, related_name='relations_left')
    existence_interval = model_fields.DateIntervalField()
    property: Property

    class Meta:
        abstract = True

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.property.is_value_unique:
            k = self._get_right_value_attribute_name()
            filters = {
                'property': self.property,
                'left_object': self.left_object,
                k: getattr(self, k),
            }
            if self.objects.filter(**filters).exists():
                raise dj_exc.ValidationError(f'duplicate value for property {self.property}',
                                             code='relation_duplicate_for_unique_property')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.property.is_temporal and self.existence_interval is None:
            raise dj_exc.ValidationError('temporal relation must have an associated date interval',
                                         code='temporal_relation_without_date_interval')
        maxi = self.property.multiplicity_max
        if not self.property.is_temporal:
            if self.objects.filter(left_object=self.left_object, property=self.property).count() >= maxi:
                raise dj_exc.ValidationError(
                    f'too many relations for property {self.property} on object {self.left_object}',
                    code='too_many_relations'
                )
        else:
            def overlaps(f: tuple[str, typ.Any] = None):
                filters = {
                    'property': self.property,
                    'left_object': self.left_object,
                    **({f[0]: f[1]} if f else {})
                }
                # TODO if possible, delegate to SQL
                return any(relation.existence_interval.overlaps(self.existence_interval)
                           for relation in self.objects.filter(**filters))

            if self.property.multiplicity_max == 1 and overlaps():
                raise dj_exc.ValidationError(
                    f'overlapping date intervals for temporal property {self.property}',
                    code='temporal_relation_overlap_single_value'
                )
            elif self.property.multiplicity_max > 1:
                k = self._get_right_value_attribute_name()
                v = getattr(self, k)
                if overlaps((k, v)):
                    raise dj_exc.ValidationError(
                        f'overlapping date intervals for property {self.property} and value {v}',
                        code='temporal_relation_overlap_many_values'
                    )

    @classmethod
    @abc.abstractmethod
    def _get_right_value_attribute_name(cls) -> str:
        pass


class ObjectRelation(Relation):
    right_object = dj_models.ForeignKey(Object, on_delete=dj_models.CASCADE, related_name='relations_right')
    property = dj_models.ForeignKey(TypeProperty, on_delete=dj_models.CASCADE, related_name='instances')

    @classmethod
    def _get_right_value_attribute_name(cls) -> str:
        return 'right_object'

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if not self.property.allows_itself and self.left_object == self.right_object:
            raise dj_exc.ValidationError('relation not allowed to have same object on both sides',
                                         code='object_relation_same_object_on_both_sides')


_RT = typ.TypeVar('_RT')


class PrimitiveRelation(Relation, abc.ABC, typ.Generic[_RT]):
    value: _RT

    class Meta:
        abstract = True

    @classmethod
    def _get_right_value_attribute_name(cls) -> str:
        return 'value'


class LocalizedRelation(PrimitiveRelation[str]):
    property = dj_models.ForeignKey(LocalizedProperty, on_delete=dj_models.CASCADE, related_name='instances')
    language_code = dj_models.CharField(max_length=5, validators=[lang_code_validator])
    value = dj_models.TextField()

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(language_code=self.language_code, left_object=self.left_object).exists():
            raise dj_exc.ValidationError(
                f'duplicate localization for language {self.language_code} and object {self.left_object}',
                code='localized_relation_duplicate'
            )


class StringRelation(PrimitiveRelation[str]):
    property = dj_models.ForeignKey(StringProperty, on_delete=dj_models.CASCADE, related_name='instances')
    value = dj_models.CharField(max_length=200)


class IntRelation(PrimitiveRelation[int]):
    property = dj_models.ForeignKey(IntProperty, on_delete=dj_models.CASCADE, related_name='instances')
    value = dj_models.IntegerField()

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if (self.property.min is not None and self.value < self.property.min
                or self.property.max is not None and self.value > self.property.max):
            raise dj_exc.ValidationError(f'{self.value} outside of [{self.property.min}, {self.property.max}]',
                                         code='int_relation_invalid_value')


class FloatRelation(PrimitiveRelation[float]):
    property = dj_models.ForeignKey(FloatProperty, on_delete=dj_models.CASCADE, related_name='instances')
    value = dj_models.FloatField()

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if (self.property.min is not None and self.value < self.property.min
                or self.property.max is not None and self.value > self.property.max):
            raise dj_exc.ValidationError(f'{self.value} outside of [{self.property.min}, {self.property.max}]',
                                         code='float_relation_invalid_value')


class BooleanRelation(PrimitiveRelation[bool]):
    property = dj_models.ForeignKey(BooleanProperty, on_delete=dj_models.CASCADE, related_name='instances')
    value = dj_models.BooleanField()


class UnitRelation(PrimitiveRelation[float]):
    property = dj_models.ForeignKey(UnitProperty, on_delete=dj_models.CASCADE, related_name='instances')
    value = dj_models.FloatField()
    unit = dj_models.ForeignKey(Unit, on_delete=dj_models.CASCADE, related_name='relations')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if not self.unit.may_be_negative and self.value < 0:
            raise dj_exc.ValidationError('value cannot be negative', code='unit_relation_negative_value')


class DateIntervalRelation(PrimitiveRelation[data_types.DateInterval]):
    property = dj_models.ForeignKey(DateIntervalProperty, on_delete=dj_models.CASCADE, related_name='instances')
    value = model_fields.DateIntervalField()

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.property.is_temporal:
            raise dj_exc.ValidationError('date interval relation cannot be temporal',
                                         code='temporal_date_interval_relation')


###############
# Edit System #
###############


class EditGroup(dj_models.Model):
    date = dj_models.DateTimeField()
    author = dj_models.ForeignKey(UserInfo, on_delete=dj_models.SET_NULL, related_name='edits_groups',
                                  null=True, blank=True)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(date=self.date, author=self.author).exists():
            # noinspection PyUnresolvedReferences
            raise dj_exc.ValidationError(
                f'user {self.user.user.username} cannot make multiple edits at the exact same time',
                code='edit_group_duplicate_date'
            )


class Edit(dj_models.Model, abc.ABC):
    @staticmethod
    def _validate_object_id(i: int):
        if i < 0:
            raise dj_exc.ValidationError(f'invalid object ID {i}', code='edit_invalid_object_id')

    edit_group = dj_models.ForeignKey(EditGroup, on_delete=dj_models.CASCADE, related_name='edits')
    object_id = dj_models.IntegerField(validators=[_validate_object_id])

    class Meta:
        abstract = True


class ObjectEdit(Edit, abc.ABC):
    object_type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE, related_name='object_edits')

    class Meta:
        abstract = True


class ObjectCreatedEdit(ObjectEdit):
    pass


class ObjectDeletedEdit(ObjectEdit):
    pass


class RelationEdit(Edit, abc.ABC):
    property = dj_models.ForeignKey(Property, on_delete=dj_models.CASCADE, related_name='relation_edits')

    class Meta:
        abstract = True


class RelationValueEdit(RelationEdit):
    old_value = dj_models.JSONField()
    new_value = dj_models.JSONField()


class RelationCreatedEdit(RelationEdit):
    value = dj_models.JSONField()


class RelationDeletedEdit(RelationEdit):
    value = dj_models.JSONField()


################
# Translations #
################


class Translation(dj_models.Model, abc.ABC):
    language_code = dj_models.CharField(max_length=5, validators=[lang_code_validator])
    label = dj_models.CharField(max_length=100)

    class Meta:
        abstract = True

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        k = self._get_object_attr_name()
        obj = getattr(self, k)
        filters = {
            'language_code': self.language_code,
            'label': self.label,
            k: obj,
        }
        if self.objects.filter(**filters).exists():
            raise dj_exc.ValidationError(f'duplicate translation for object {obj} and language {self.language_code}',
                                         code='duplicate_translation')

    @classmethod
    @abc.abstractmethod
    def _get_object_attr_name(cls) -> str:
        pass


class StructureTranslation(Translation):
    structure = dj_models.ForeignKey(Structure, on_delete=dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'structure'


class UnitTypeTranslation(Translation):
    unit_type = dj_models.ForeignKey(UnitType, on_delete=dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'unit_type'


class UnitTranslation(Translation):
    unit = dj_models.ForeignKey(Unit, on_delete=dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'unit'
