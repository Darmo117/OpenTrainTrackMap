from __future__ import annotations

import abc
import datetime
import typing as typ

import django.contrib.auth.models as dj_auth_models
import django.core.exceptions as dj_exc
import django.core.validators as dj_valid
import django.db.models as dj_models
import math

from . import settings, model_fields
from .api import data_types, permissions, constants
from .api.wiki import namespaces, constants as w_cons


def lang_code_validator(value: str):
    if value not in settings.LANGUAGES:
        raise dj_exc.ValidationError(f'invalid language code "{value}"', code='invalid_language')


#########
# Users #
#########


def user_group_label_validator(value: str):
    if not value.isascii() or not value.isalnum():
        raise dj_exc.ValidationError('invalid user group label', code='user_group_invalid_label')


class UserGroup(dj_models.Model):
    label = dj_models.CharField(max_length=20, unique=True, validators=[user_group_label_validator])
    permissions = model_fields.CommaSeparatedStringsField()

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions

    def delete(self, using=None, keep_parents=False):
        if self.label == 'all':
            raise RuntimeError('cannot delete "all" user group')
        super().delete(using=using, keep_parents=keep_parents)


def username_validator(value: str):
    if '/' in value or settings.INVALID_TITLE_REGEX.search(value):
        raise dj_exc.ValidationError('invalid username', code='invalid')
    if CustomUser.objects.filter(username=value).exists():
        raise dj_exc.ValidationError('duplicate username', code='duplicate')


class User:
    """Wrapper class around CustomUser and AnonymousUser classes."""

    def __init__(self, dj_user: CustomUser, anonymous_username: str = None):
        """Create a wrapper around the given user.

        :param dj_user: Either a CustomUser or AnonymousUser.
        :param anonymous_username: If the wrapped user is anonymous,
            the username to use instead of the default empty string.
        """
        self._user = dj_user
        self._anonymous_username = anonymous_username

    @property
    def internal_user(self) -> CustomUser:
        return self._user

    @property
    def is_authenticated(self) -> bool:
        return self._user.is_authenticated

    @property
    def is_anonymous(self) -> bool:
        """Return true if the user is anonymous, false otherwise.
        A user is anonymous if they are not authenticated and their IP address
        has not already been use to edit the wiki at least once."""
        return self._user.is_anonymous

    @property
    def username(self) -> str:
        if self.is_anonymous:
            return self._anonymous_username
        return self._user.username

    @username.setter
    def username(self, value: str):
        self._check_not_anonymous()
        self._user.username = value

    @property
    def password(self) -> str:
        return self._user.password

    @password.setter
    def password(self, value: str):
        self._check_not_anonymous()
        self._user.password = value

    @property
    def email(self) -> str:
        return self._user.email

    @email.setter
    def email(self, value: str):
        self._check_not_anonymous()
        self._user.email = value

    @property
    def prefered_language(self) -> settings.Language:
        if self.is_anonymous:
            return settings.LANGUAGES[settings.DEFAULT_LANGUAGE_CODE]
        return settings.LANGUAGES[self._user.prefered_language_code]

    @prefered_language.setter
    def prefered_language(self, value: settings.Language):
        self._check_not_anonymous()
        self._user.prefered_language_code = value.code

    @property
    def gender(self) -> data_types.UserGender:
        return data_types.GENDERS.get(self._user.gender_code, data_types.GENDER_N)

    @gender.setter
    def gender(self, value: data_types.UserGender):
        self._check_not_anonymous()
        self._user.gender_code = value.label

    @property
    def block(self) -> UserBlock | None:
        return self._user.block if not self.is_anonymous else None

    @block.setter
    def block(self, value: UserBlock | None):
        self._check_not_anonymous()
        self._user.block = value

    @property
    def edits(self) -> dj_models.Manager[EditGroup]:
        return self._user.edit_groups if not self.is_anonymous else dj_auth_models.EmptyManager(EditGroup)

    @property
    def wiki_messages(self) -> dj_models.Manager[Message]:
        return self._user.wiki_messages if not self.is_anonymous else dj_auth_models.EmptyManager(Message)

    @property
    def wiki_topics(self) -> dj_models.Manager[Topic]:
        return self._user.wiki_topics

    def has_permission(self, perm: str) -> bool:
        return any(g.has_permission(perm) for g in self._user.groups.all())

    def notes_count(self) -> int:
        """Return the total number of notes created by this user."""
        if not self.is_anonymous:
            return 0
        return (ObjectEdit.objects  # Get all object creation edits
                # Keep only those made by this user that are of type "Note"
                .filter(edit_group__author=self, operation=constants.OBJECT_CREATED, object_type__label='Note')
                .count())

    def edits_count(self) -> int:
        """Return the total number of edits on objects and relations made by this user."""
        if not self.is_anonymous:
            return 0
        return (self._user.edit_groups  # Get all edit groups for this user
                .annotate(edits_count=dj_models.Count('edits'))  # Count number of edits for each group
                .aggregate(dj_models.Sum('edits_count')))  # Sum all counts

    def edit_groups_count(self) -> int:
        """Return the number of edit groups made by this user."""
        return self._user.edit_groups.count() if not self.is_anonymous else 0

    def wiki_edits_count(self) -> int:
        """Return the number of edits this user made on the wiki."""
        return self._user.wiki_edits.count() if not self.is_anonymous else 0

    def wiki_topics_count(self) -> int:
        """Return the number of topics this user created on the wiki."""
        return self._user.wiki_topics.count() if not self.is_anonymous else 0

    def wiki_messages_count(self) -> int:
        """Return the number of messages this user posted on the wiki."""
        return self._user.wiki_messages.count() if not self.is_anonymous else 0

    def _check_not_anonymous(self):
        if not self.is_anonymous:
            raise RuntimeError('user is anonymous')


class CustomUser(dj_auth_models.AbstractUser):
    """Custom user class to override the default username validator and add additional data."""
    username_validator = username_validator
    hide_username = dj_models.BooleanField(default=False)
    # IP for anonymous accounts
    ip = dj_models.CharField(max_length=39, null=True, blank=True)
    prefered_language_code = dj_models.CharField(max_length=5, validators=[lang_code_validator],
                                                 default=settings.DEFAULT_LANGUAGE_CODE)
    groups = dj_models.ManyToManyField(UserGroup, related_name='users')
    gender_code = dj_models.CharField(max_length=10, choices=tuple((v, v) for v in data_types.GENDERS.keys()),
                                      default=data_types.GENDER_N.label)


class UserBlock(dj_models.Model):
    user = dj_models.OneToOneField(CustomUser, on_delete=dj_models.CASCADE, related_name='block')
    performer = dj_models.ForeignKey(CustomUser, on_delete=dj_models.SET_NULL, related_name='blocks_given', null=True)
    reason = dj_models.CharField(max_length=200)
    end_date = dj_models.DateTimeField(null=True, blank=True)
    allow_messages_on_own_user_page = dj_models.BooleanField()
    allow_editing_own_settings = dj_models.BooleanField()


###################
# Meta-meta-model #
###################


class UnitType(dj_models.Model):
    label = dj_models.CharField(unique=True, max_length=30)


class Unit(dj_models.Model):
    symbol = dj_models.CharField(unique=True, max_length=10)
    type = dj_models.ForeignKey(UnitType, on_delete=dj_models.CASCADE, related_name='units')
    may_be_negative = dj_models.BooleanField()
    to_base_unit_coef = dj_models.FloatField()


def structure_label_validator(value: str):
    if not value.isascii() or not value.isalnum():
        raise dj_exc.ValidationError('invalid structure label', code='structure_invalid_label')


class Structure(dj_models.Model):
    label = dj_models.CharField(max_length=50, validators=[structure_label_validator])
    deprecated = dj_models.BooleanField()
    wikidata_qid = dj_models.CharField(null=True, blank=True, max_length=15,
                                       validators=[dj_valid.RegexValidator(r'^Q\d+$')])

    class Meta:
        abstract = True


class Type(Structure):
    is_abstract = dj_models.BooleanField()
    enum = dj_models.BooleanField()
    super_type = dj_models.ForeignKey('self', on_delete=dj_models.CASCADE, related_name='sub_types')

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(label=self.label).exists():
            raise dj_exc.ValidationError(
                f'type with label {self.label} already exist',
                code='type_duplicate'
            )

    def __str__(self):
        return self.label


def property_multiplicity_validator(m: int):
    if m < 0:
        raise dj_exc.ValidationError(
            'negative property multiplicity',
            code='property_negative_multiplicity'
        )


class Property(Structure):
    # Common fields
    host_type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE, related_name='properties')
    multiplicity_min = dj_models.IntegerField(validators=[property_multiplicity_validator])
    multiplicity_max = dj_models.IntegerField(validators=[property_multiplicity_validator], null=True, blank=True)
    is_temporal = dj_models.BooleanField()
    absent_means_unknown_value = dj_models.BooleanField(null=True, blank=True)
    is_value_unique = dj_models.BooleanField()
    property_type = dj_models.CharField(max_length=20, choices=tuple((v, v) for v in constants.PROPERTY_TYPES))
    # Type property fields
    target_type = dj_models.ForeignKey(Type, on_delete=dj_models.SET_NULL, related_name='targetting_properties',
                                       null=True, blank=True)
    allows_itself = dj_models.BooleanField(null=True, blank=True)
    # Int property fields
    min_int = dj_models.IntegerField(null=True, blank=True)
    max_int = dj_models.IntegerField(null=True, blank=True)
    # Float property fields
    min_float = dj_models.FloatField(null=True, blank=True)
    max_float = dj_models.FloatField(null=True, blank=True)
    # Unit type property fields
    unit_type = dj_models.ForeignKey(UnitType, on_delete=dj_models.SET_NULL, related_name='properties',
                                     null=True, blank=True)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(label=self.label, host_type__label=self.host_type.label).exists():
            raise dj_exc.ValidationError(
                f'property with name {self.label} already exists for type {self.host_type}',
                code='duplicate_property'
            )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        match self.property_type:
            case constants.PROPERTY_TYPE:
                self._check_type_property()
            case constants.PROPERTY_LOCALIZED:
                self._check_localized_property()
            case constants.PROPERTY_STRING:
                self._check_string_property()
            case constants.PROPERTY_INT:
                self._check_int_property()
            case constants.PROPERTY_FLOAT:
                self._check_float_property()
            case constants.PROPERTY_BOOLEAN:
                self._check_boolean_property()
            case constants.PROPERTY_UNIT:
                self._check_unit_property()
            case constants.PROPERTY_DATE_INTERVAL:
                self._check_date_interval_property()

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

    @staticmethod
    def _any_not_null(*fields) -> bool:
        return any(f is not None for f in fields)

    def _check_type_property(self):
        if self._any_not_null(self.min_int, self.max_int, self.min_float, self.max_float, self.unit_type):
            raise dj_exc.ValidationError(
                'type property should only have common fields set',
                code='type_property_invalid_fields'
            )
        if self.target_type is None:
            raise dj_exc.ValidationError(
                'missing target_type field',
                code='type_property_missing_target_type_field'
            )
        if self.allows_itself is None:
            raise dj_exc.ValidationError(
                'missing allows_itself field',
                code='type_property_missing_allows_itself_field'
            )

    def _check_localized_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise dj_exc.ValidationError(
                'localized property should only have common fields set',
                code='localized_property_invalid_fields'
            )
        if self.is_temporal:
            raise dj_exc.ValidationError(
                'localized property cannot be temporal',
                code='localized_property_temporal'
            )

    def _check_string_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise dj_exc.ValidationError(
                'string property should only have common fields set',
                code='string_property_invalid_fields'
            )

    def _check_int_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_float, self.max_float,
                              self.unit_type):
            raise dj_exc.ValidationError(
                'int property should only have min_int and min_max fields set',
                code='int_property_invalid_fields'
            )
        if self.min_int is not None and self.max_int is not None:
            if self.min_int > self.max_int:
                raise dj_exc.ValidationError(
                    'max should be greater than min',
                    code='int_property_invalid_bounds'
                )
            if self.min_int == self.max_int:
                raise dj_exc.ValidationError(
                    'min and max must be different',
                    code='int_property_same_bounds'
                )

    def _check_float_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.unit_type):
            raise dj_exc.ValidationError(
                'string property should only have min_float and max_float fields set',
                code='float_property_invalid_fields'
            )
        if self.min_float is not None and self.max_float is not None:
            if self.min_float > self.max_float:
                raise dj_exc.ValidationError(
                    'max should be greater than min',
                    code='float_property_invalid_bounds'
                )
            if self.min_float == self.max_float:
                raise dj_exc.ValidationError(
                    'min and max must be different',
                    code='float_property_same_bounds'
                )

    def _check_boolean_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise dj_exc.ValidationError(
                'boolean property should only have common fields set',
                code='boolean_property_invalid_fields'
            )

    def _check_unit_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise dj_exc.ValidationError(
                'unit property should only have unit_type field set',
                code='unit_property_invalid_fields'
            )
        if self.unit_type is None:
            raise dj_exc.ValidationError(
                f'missing unit type for unit property {self.label}',
                code='unit_property_missing_unit_type'
            )

    def _check_date_interval_property(self):
        if self._any_not_null(self.target_type, self.allows_itself, self.min_int, self.max_int,
                              self.min_float, self.max_float, self.unit_type):
            raise dj_exc.ValidationError(
                'date interval property should only have common fields set',
                code='date_interval_property_invalid_fields'
            )
        if self.is_temporal:
            raise dj_exc.ValidationError(
                'date interval property cannot be temporal',
                code='date_interval_property_temporal'
            )

    def __str__(self):
        return f'{self.host_type.label}.{self.label}'


##############
# Meta-model #
##############


class Object(dj_models.Model):
    type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE, related_name='instances')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.type.is_abstract:
            raise dj_exc.ValidationError('abstract types cannot have instances', code='object_with_abstract_type')


class Relation(dj_models.Model):
    # Common fields
    property = dj_models.ForeignKey(Property, on_delete=dj_models.CASCADE, related_name='instances')
    left_object = dj_models.ForeignKey(Object, on_delete=dj_models.CASCADE, related_name='relations_left')
    existence_interval = model_fields.DateIntervalField()
    # Object relation fields
    right_object = dj_models.ForeignKey(Object, on_delete=dj_models.CASCADE, related_name='relations_right',
                                        null=True, blank=True)
    # Localized relation fields
    language_code = dj_models.CharField(max_length=5, validators=[lang_code_validator], null=True, blank=True)
    value_localized_p = dj_models.TextField(null=True, blank=True)
    # String relation fields
    value_string_p = dj_models.CharField(max_length=200, null=True, blank=True)
    # Int relation fields
    value_int_p = dj_models.IntegerField(null=True, blank=True)
    # Float relation fields
    value_float_p = dj_models.FloatField(null=True, blank=True)
    # Boolean relation fields
    value_boolean_p = dj_models.BooleanField(null=True, blank=True)
    # Unit relation fields
    value_unit_p = dj_models.FloatField(null=True, blank=True)
    unit = dj_models.ForeignKey(Unit, on_delete=dj_models.CASCADE, related_name='relations', null=True, blank=True)
    # Date interval relation fields
    value_date_interval_p = model_fields.DateIntervalField(null=True, blank=True)

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
                raise dj_exc.ValidationError(
                    f'duplicate value for property {self.property}',
                    code='relation_duplicate_for_unique_property'
                )

        match self.property.property_type:
            case constants.PROPERTY_LOCALIZED:
                if self.objects.filter(language_code=self.language_code, left_object=self.left_object).exists():
                    raise dj_exc.ValidationError(
                        f'duplicate localization for language {self.language_code} and object {self.left_object}',
                        code='localized_relation_duplicate'
                    )

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        match self.property.property_type:
            case constants.PROPERTY_TYPE:
                self._check_object_relation()
            case constants.PROPERTY_LOCALIZED:
                self._check_localized_relation()
            case constants.PROPERTY_STRING:
                self._check_string_relation()
            case constants.PROPERTY_INT:
                self._check_int_relation()
            case constants.PROPERTY_FLOAT:
                self._check_float_relation()
            case constants.PROPERTY_BOOLEAN:
                self._check_boolean_relation()
            case constants.PROPERTY_UNIT:
                self._check_unit_relation()
            case constants.PROPERTY_DATE_INTERVAL:
                self._check_date_interval_relation()

        if self.property.is_temporal and self.existence_interval is None:
            raise dj_exc.ValidationError(
                'temporal relation must have an associated date interval',
                code='temporal_relation_without_date_interval'
            )

        maxi = self.property.multiplicity_max or math.inf
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

            if maxi == 1 and overlaps():
                raise dj_exc.ValidationError(
                    f'overlapping date intervals for temporal property {self.property}',
                    code='temporal_relation_overlap_single_value'
                )
            elif maxi > 1:
                k = self._get_right_value_attribute_name()
                v = getattr(self, k)
                if overlaps((k, v)):
                    raise dj_exc.ValidationError(
                        f'overlapping date intervals for property {self.property} and value {v}',
                        code='temporal_relation_overlap_many_values'
                    )

    def _get_right_value_attribute_name(self) -> str:
        match self.property.property_type:
            case constants.PROPERTY_TYPE:
                return 'right_object'
            case constants.PROPERTY_LOCALIZED:
                return 'value_localized_p'
            case constants.PROPERTY_STRING:
                return 'value_string_p'
            case constants.PROPERTY_INT:
                return 'value_int_p'
            case constants.PROPERTY_FLOAT:
                return 'value_float_p'
            case constants.PROPERTY_BOOLEAN:
                return 'value_boolean_p'
            case constants.PROPERTY_UNIT:
                return 'value_unit_p'
            case constants.PROPERTY_DATE_INTERVAL:
                return 'value_date_interval_p'

    @staticmethod
    def _any_not_null(*fields) -> bool:
        return any(f is not None for f in fields)

    def _check_object_relation(self):
        if self._any_not_null(
                self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p, self.value_float_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise dj_exc.ValidationError(
                'object relation should only have right_object field set',
                code='object_relation_invalid_fields'
            )
        if self.right_object is None:
            raise dj_exc.ValidationError(
                'missing right object',
                code='object_relation_missing_right_object'
            )
        if not self.property.allows_itself and self.left_object == self.right_object:
            raise dj_exc.ValidationError(
                'relation not allowed to have same object on both sides',
                code='object_relation_same_object_on_both_sides'
            )

    def _check_localized_relation(self):
        if self._any_not_null(
                self.right_object, self.value_string_p, self.value_int_p, self.value_float_p, self.value_boolean_p,
                self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise dj_exc.ValidationError(
                'localized relation should only have language_code and value_localized_p fields set',
                code='localized_relation_invalid_fields'
            )
        if self.language_code is None:
            raise dj_exc.ValidationError(
                'missing language code',
                code='localized_relation_missing_language_code'
            )
        if self.value_localized_p is None:
            raise dj_exc.ValidationError(
                'missing localized value',
                code='localized_relation_missing_language_code'
            )

    def _check_string_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_int_p, self.value_float_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise dj_exc.ValidationError(
                'string relation should only have value_string_p field set',
                code='string_relation_invalid_fields'
            )
        if self.value_string_p is None:
            raise dj_exc.ValidationError(
                'missing string value',
                code='string_relation_missing_value'
            )

    def _check_int_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_float_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise dj_exc.ValidationError(
                'int relation should only have value_int_p field set',
                code='int_relation_invalid_fields'
            )
        if self.value_int_p is None:
            raise dj_exc.ValidationError(
                'missing int value',
                code='int_relation_missing_value'
            )
        if (self.property.min_int is not None and self.value_int_p < self.property.min_int
                or self.property.max_int is not None and self.value_int_p > self.property.max_int):
            raise dj_exc.ValidationError(
                f'{self.value_int_p} outside of [{self.property.min_int}, {self.property.max_int}]',
                code='int_relation_invalid_value'
            )

    def _check_float_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_boolean_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise dj_exc.ValidationError(
                'float relation should only have value_float_p field set',
                code='float_relation_invalid_fields'
            )
        if self.value_int_p is None:
            raise dj_exc.ValidationError(
                'missing float value',
                code='float_relation_missing_value'
            )
        if (self.property.min_float is not None and self.value_float_p < self.property.min_float
                or self.property.max_float is not None and self.value_float_p > self.property.max_float):
            raise dj_exc.ValidationError(
                f'{self.value_float_p} outside of [{self.property.min_float}, {self.property.max_float}]',
                code='float_relation_invalid_value'
            )

    def _check_boolean_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_float_p, self.value_unit_p, self.unit, self.value_date_interval_p
        ):
            raise dj_exc.ValidationError(
                'boolean relation should only have value_boolean_p field set',
                code='boolean_relation_invalid_fields'
            )
        if self.value_boolean_p is None:
            raise dj_exc.ValidationError(
                'missing boolean value',
                code='boolean_relation_missing_value'
            )

    def _check_unit_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_float_p, self.value_boolean_p, self.value_date_interval_p
        ):
            raise dj_exc.ValidationError(
                'unit relation should only have value_boolean_p field set',
                code='unit_relation_invalid_fields'
            )
        if self.value_unit_p is None:
            raise dj_exc.ValidationError(
                'missing unit value',
                code='unit_relation_missing_value'
            )
        if self.unit is None:
            raise dj_exc.ValidationError(
                'missing unit',
                code='unit_relation_missing_unit'
            )
        if not self.unit.may_be_negative and self.value_unit_p < 0:
            raise dj_exc.ValidationError(
                'value cannot be negative',
                code='unit_relation_negative_value'
            )

    def _check_date_interval_relation(self):
        if self._any_not_null(
                self.right_object, self.language_code, self.value_localized_p, self.value_string_p, self.value_int_p,
                self.value_float_p, self.value_boolean_p, self.value_unit_p, self.unit
        ):
            raise dj_exc.ValidationError(
                'date interval relation should only have value_date_interval_p field set',
                code='date_interval_relation_invalid_fields'
            )
        if self.value_date_interval_p is None:
            raise dj_exc.ValidationError(
                'missing date interval',
                code='date_interval_missing_value'
            )
        if self.property.is_temporal:
            raise dj_exc.ValidationError(
                'date interval relation cannot be temporal',
                code='temporal_date_interval_relation'
            )


###############
# Edit System #
###############


class EditGroup(dj_models.Model):
    date = dj_models.DateTimeField()
    author = dj_models.ForeignKey(CustomUser, on_delete=dj_models.SET_NULL, related_name='edit_groups', null=True)

    class Meta:
        get_latest_by = 'date'

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(date=self.date, author=self.author).exists():
            # noinspection PyUnresolvedReferences
            raise dj_exc.ValidationError(
                f'user {self.user.user.username} cannot make multiple edits at the exact same time',
                code='edit_group_duplicate_date'
            )


def _edit_validate_object_id(i: int):
    if i < 0:
        raise dj_exc.ValidationError(
            f'invalid object ID {i}',
            code='edit_invalid_object_id'
        )


class Edit(dj_models.Model):
    edit_group = dj_models.ForeignKey(EditGroup, on_delete=dj_models.CASCADE)
    object_id = dj_models.IntegerField(validators=[_edit_validate_object_id])

    class Meta:
        abstract = True


class ObjectEdit(Edit):
    object_type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE)
    operation = dj_models.CharField(max_length=10, choices=tuple((v, v) for v in constants.OBJECT_EDIT_ACTIONS))


class RelationEdit(Edit):
    property_name = dj_models.ForeignKey(Relation, on_delete=dj_models.CASCADE, related_name='edits')
    old_value = dj_models.JSONField(null=True, blank=True)
    new_value = dj_models.JSONField(null=True, blank=True)
    operation = dj_models.CharField(max_length=10, choices=tuple((v, v) for v in constants.RELATION_EDIT_ACTIONS))

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.old_value is None and self.new_value is None:
            raise dj_exc.ValidationError(
                'old and new value cannot both be None',
                code='relation_edit_missing_values'
            )


################
# Translations #
################


class Translation(dj_models.Model):
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


class TypeTranslation(Translation):
    type = dj_models.ForeignKey(Type, on_delete=dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'type'


class PropertyTranslation(Translation):
    property = dj_models.ForeignKey(Property, on_delete=dj_models.CASCADE, related_name='translations')

    @classmethod
    def _get_object_attr_name(cls) -> str:
        return 'property'


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


########
# Wiki #
########


class RevisionMixin:
    date = dj_models.DateTimeField(auto_now_add=True)
    author = dj_models.ForeignKey(CustomUser, on_delete=dj_models.CASCADE, related_name='wiki_edits', null=True)
    comment = dj_models.CharField(max_length=200, null=True, blank=True)
    comment_hidden = dj_models.BooleanField(default=False)
    hidden = dj_models.BooleanField(default=False)
    is_minor = dj_models.BooleanField(default=False)


#########
# Pages #
#########


def page_title_validator(value: str):
    if settings.INVALID_TITLE_REGEX.match(value):
        raise dj_exc.ValidationError('invalid page title', code='page_invalid_title')


class Page(dj_models.Model):
    namespace_id = dj_models.IntegerField()
    title = dj_models.CharField(max_length=200, validators=[page_title_validator])
    content_type = dj_models.CharField(max_length=20, choices=tuple((v, v) for v in w_cons.CONTENT_TYPES),
                                       default=w_cons.CT_WIKIPAGE)
    deleted = dj_models.BooleanField(default=False)
    is_category_hidden = dj_models.BooleanField(null=True, blank=True)
    content_language_code = dj_models.CharField(max_length=5, validators=[lang_code_validator],
                                                default=settings.DEFAULT_LANGUAGE_CODE)

    class Meta:
        unique_together = ('namespace_id', 'title')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.namespace == namespaces.NS_CATEGORY and self.is_category_hidden is not None:
            raise dj_exc.ValidationError(
                'page is not a category',
                code='page_not_category'
            )

    @property
    def namespace(self) -> namespaces.Namespace:
        return namespaces.NAMESPACES[self.namespace_id]

    @property
    def full_title(self) -> str:
        return self.namespace.get_full_page_title(self.title)

    @property
    def base_name(self) -> str:
        if '/' in self.title and self.namespace.allows_subpages:
            return self.title.split('/')[0]
        return self.title

    @property
    def page_name(self) -> str:
        if '/' in self.title and self.namespace.allows_subpages:
            return self.title.split('/')[-1]
        return self.title

    @property
    def exists(self) -> bool:
        return self.pk is not None

    @property
    def content_language(self) -> settings.Language:
        return settings.LANGUAGES[self.content_language_code]

    def can_user_edit(self, user: User) -> bool:
        return (self.namespace.can_user_edit_pages(user)
                and (user.block is None
                     or user.block.end_date >= datetime.datetime.now())
                and (self.namespace != namespaces.NS_USER
                     or self.base_name == user.username
                     or user.has_permission(permissions.PERM_WIKI_EDIT_USER_PAGES)))

    def can_user_post_messages(self, user: User) -> bool:
        return self.namespace.is_editable and (
                user.block is None
                or user.block.end_date < datetime.datetime.now()
                or (user.block.allow_messages_on_own_user_page and self.namespace == namespaces.NS_USER)
        )

    def is_user_following(self, user: User) -> bool:
        return not user.is_anonymous and user.internal_user.watched_pages.filter(page_namespace_id=self.namespace_id,
                                                                                 page_title=self.title).exists()

    def get_content(self) -> str:
        if self.exists and (revision := self.revisions.latest()):
            return revision.text
        return ''

    def get_edit_protection(self) -> PageProtection | None:
        try:
            return PageProtection.objects.get(page_namespace_id=self.namespace_id, page_title=self.title)
        except PageProtection.DoesNotExist:
            return None


class PageCategory(dj_models.Model):
    page = dj_models.ForeignKey(Page, on_delete=dj_models.CASCADE, related_name='categories')
    cat_title = dj_models.CharField(max_length=200, validators=[page_title_validator])
    sort_key = dj_models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        unique_together = ('page', 'cat_title')

    @staticmethod
    def subcategories_for_category(cat_title: str) -> dj_models.QuerySet[Page]:
        return Page.objects.filter(categories__cat_title=cat_title, namespace_id=namespaces.NS_CATEGORY)

    @staticmethod
    def pages_for_category(cat_title: str) -> dj_models.QuerySet[Page]:
        return Page.objects.filter(dj_models.Q(categories__cat_title=cat_title)
                                   & ~dj_models.Q(namespace_id=namespaces.NS_CATEGORY))


class PageProtection(dj_models.Model):
    # No foreign key to Page as it allows protecting non-existent pages.
    page_namespace_id = dj_models.IntegerField()
    page_title = dj_models.CharField(max_length=200, validators=[page_title_validator])
    end_date = dj_models.DateTimeField()
    reason = dj_models.TextField(null=True, blank=True)
    protection_level = dj_models.CharField(max_length=20, unique=True, validators=[user_group_label_validator])


class PageWatchlist(dj_models.Model):
    user = dj_models.ForeignKey(CustomUser, on_delete=dj_models.CASCADE, related_name='watched_pages')
    # No foreign key to Page as it allows following non-existent pages.
    page_namespace_id = dj_models.IntegerField()
    page_title = dj_models.CharField(max_length=200, validators=[page_title_validator])
    end_date = dj_models.DateTimeField(null=True, blank=True)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if self.objects.filter(user=self.user, page_namespace_id=self.page_namespace_id,
                               page_title=self.page_title).exists():
            raise dj_exc.ValidationError(
                'duplicate watchlist entry',
                code='page_watchlist_duplicate_entry'
            )


def tag_label_validator(value: str):
    if not value.isascii() or not value.isalnum():
        raise dj_exc.ValidationError('invalid tag label', code='tag_invalid_label')


class Tag(dj_models.Model):
    label = dj_models.CharField(max_length=20, validators=[tag_label_validator])


class PageRevision(dj_models.Model, RevisionMixin):
    page = dj_models.ForeignKey(Page, on_delete=dj_models.CASCADE, related_name='revisions')
    tags = dj_models.ManyToManyField(Tag, related_name='revisions')
    content = dj_models.TextField(blank=True)

    class Meta:
        get_latest_by = 'date'


###############
# Discussions #
###############


class Topic(dj_models.Model):
    page = dj_models.ForeignKey(Page, on_delete=dj_models.CASCADE, related_name='topics')
    author = dj_models.ForeignKey(CustomUser, on_delete=dj_models.CASCADE, related_name='wiki_topics', null=True)
    date = dj_models.DateTimeField(auto_now_add=True)

    def get_title(self) -> str:
        return revision.title if (revision := self.revisions.latest()) else ''


class TopicRevision(dj_models.Model, RevisionMixin):
    topic = dj_models.ForeignKey(Topic, on_delete=dj_models.CASCADE, related_name='revisions')
    title = dj_models.CharField(max_length=200)

    class Meta:
        get_latest_by = 'date'


class Message(dj_models.Model):
    topic = dj_models.ForeignKey(Topic, on_delete=dj_models.CASCADE, related_name='messages')
    author = dj_models.ForeignKey(CustomUser, on_delete=dj_models.CASCADE, related_name='wiki_messages', null=True)
    date = dj_models.DateTimeField(auto_now_add=True)
    response_to = dj_models.ForeignKey('self', on_delete=dj_models.SET_NULL, related_name='responses', null=True)

    def get_content(self) -> str:
        return revision.text if (revision := self.revisions.latest()) else ''


class MessageRevision(dj_models.Model, RevisionMixin):
    message = dj_models.ForeignKey(Message, on_delete=dj_models.CASCADE, related_name='revisions')
    text = dj_models.TextField(blank=True)

    class Meta:
        get_latest_by = 'date'
