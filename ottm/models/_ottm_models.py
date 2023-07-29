from __future__ import annotations

import json as _json

import django.core.exceptions as _dj_exc
import django.db.models as _dj_models

from .. import model_fields as _mf
from ..api import constants as _cons, data_types as _dt


class Serializable(_dj_models.Model):
    @classmethod
    def deserialize_full(cls, json_object: dict) -> Serializable:
        kwargs = {}
        many2many_args = {}
        for k, v in json_object.items():
            if isinstance(v, list):
                many2many_args[k] = v
            else:
                kwargs[k] = v
        o = cls(**kwargs)
        for k, v in many2many_args.items():
            for value in v:
                class_ = globals()[value['class']]
                if not issubclass(class_, Serializable):
                    raise TypeError(f'expected Serializable subclass, got {class_}')
                getattr(o, k).add(class_.deserialize_reference(value['id']))
        return o

    def serialize_full(self) -> dict:
        data = {}
        for k, v in self.__dict__.items():
            if isinstance(v, Serializable):
                data[k] = v.serialize_reference()
            elif isinstance(v, _dj_models.Manager):
                data[k] = [o.serialize_reference() for o in v.all()]
            else:
                data[k] = v
        return data

    @classmethod
    def deserialize_reference(cls, id_: int) -> Serializable:
        # noinspection PyUnresolvedReferences
        return cls.objects.get(id=id_)

    def serialize_reference(self) -> dict:
        # noinspection PyUnresolvedReferences
        return {
            'class': self.__class__.__name__,
            'id': self.id,
        }

    class Meta:
        abstract = True


# region Validators


def positive_validator(v):
    if v < 0:
        raise _dj_exc.ValidationError(f'negative value: {v}')


def degrees_angle_validator(v):
    if not (0 <= v <= 360):
        raise _dj_exc.ValidationError(f'invalid degrees angle value: {v}')


# endregion
# region Translations

class Translated(Serializable):
    # The 'translations' attribute should be defined by Translation subclasses as the relation’s 'related_name'

    def get_translations(self) -> dict[str, str]:
        # noinspection PyUnresolvedReferences
        return {t.lang_code: t.label for t in self.translations.all()}

    def get_translation(self, lang_code: str) -> str | None:
        try:
            # noinspection PyUnresolvedReferences
            return self.translations.get(lang_code=lang_code)
        except _dj_exc.ObjectDoesNotExist:
            return None

    class Meta:
        abstract = True


class Translation(Serializable):
    translated_object: Translated  # Defined in subclasses
    lang_code = _dj_models.CharField(max_length=10)
    label = _dj_models.CharField(max_length=100)

    class Meta:
        abstract = True
        unique_together = ('lang_code', 'label')


# endregion
# region Enumerations


class Enumeration(Translated):
    label = _dj_models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True


class ConstructionMaterial(Enumeration):
    pass


class OperatorType(Enumeration):
    pass


class OperatorTypeTranslations(Translation):
    translated_object = _dj_models.ForeignKey(OperatorType, _dj_models.CASCADE, related_name='translations')


class TrackUseType(Enumeration):
    pass


class CrossingType(Enumeration):
    pass


class ElectrificationSystem(Enumeration):
    pass


class CurrentType(Enumeration):
    pass


class TractionType(Enumeration):
    pass


class RailType(Enumeration):
    pass


class TieType(Enumeration):
    pass


class BuildingUseType(Enumeration):
    pass


class BuildingType(Enumeration):
    pass


class BridgeSectionStructure(Enumeration):
    pass


class TrackInfrastructureUseType(Enumeration):
    pass


# endregion
# region Objects


class Unit(Translated):
    symbol = _dj_models.CharField(max_length=10, unique=True)
    to_base_unit_coef = _dj_models.FloatField()


class UnitTranslation(Translation):
    translated_object = _dj_models.ForeignKey(Unit, _dj_models.CASCADE, related_name='translations')


class LengthUnit(Unit):
    pass


class SpeedUnit(Unit):
    pass


class TemporalObject(Serializable):
    existence_interval = _mf.DateIntervalField()
    label = _dj_models.CharField(max_length=200, unique=True)
    qid = _dj_models.CharField(max_length=10, null=True, blank=True)  # QID on Wikidata
    sources = _dj_models.TextField(null=True, blank=True)
    comment = _dj_models.TextField(null=True, blank=True)


class Network(TemporalObject):
    pass


class Operator(TemporalObject):
    pass


class Relation(TemporalObject):
    networks = _dj_models.ManyToManyField(Network, related_name='relations')


class Site(Relation):
    pass


class TrainRoute(Relation):
    pass


class Infrastructure(Relation):
    pass


class Geometry(TemporalObject):
    pass


class Note(Serializable):
    text = _dj_models.TextField()
    geometries = _dj_models.ManyToManyField(Geometry, related_name='notes')


class Node(Geometry):
    altitude = _dj_models.FloatField()
    latitude = _dj_models.FloatField()
    longitude = _dj_models.FloatField()


class Polyline(Geometry):
    nodes = _dj_models.ManyToManyField(Node, related_name='polylines')


class WallSection(Polyline):
    materials = _dj_models.ManyToManyField(ConstructionMaterial, related_name='wall_sections')


class Gate(Polyline):
    materials = _dj_models.ManyToManyField(ConstructionMaterial, related_name='gates')


class TrackSection(Polyline):
    pass


class VALTrackSection(TrackSection):
    pass


class MonorailTrackSection(TrackSection):
    materials = _dj_models.ManyToManyField(ConstructionMaterial, related_name='monorail_track_sections')


class RubberTiredTramTrackSection(MonorailTrackSection):
    pass


class GLTTrackSection(TrackSection):  # Guided Light Transit
    unguided = _dj_models.BooleanField()


class TranshlohrTrackSection(TrackSection):
    pass


class LartigueMonorailTrackSection(TrackSection):
    pass


class StraddleBeamMonorailTrackSection(TrackSection):
    pass


class MaglevMonorailTrackSection(StraddleBeamMonorailTrackSection):
    pass


class InvertedTMonorailTrackSection(MonorailTrackSection):
    pass


class SuspendedMonorailTrackSection(MonorailTrackSection):
    pass


class SAFEGEMonorailTrackSection(SuspendedMonorailTrackSection):
    pass


class GroundRailMonorailTrackSection(MonorailTrackSection):
    pass


class GyroscopicMonorailTrackSection(GroundRailMonorailTrackSection):
    pass


class AddisMonorailTrackSection(GroundRailMonorailTrackSection):
    pass


class PSMTMonorailTrackSection(GroundRailMonorailTrackSection):
    pass


class CailletMonorailTrackSection(GroundRailMonorailTrackSection):
    pass


class TrackGauge(_dj_models.Model):
    gauge = _dj_models.IntegerField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(LengthUnit, _dj_models.PROTECT)


class ConventionalTrackSection(TrackSection):
    gauges = _dj_models.ManyToManyField(TrackGauge, related_name='track_sections')


class RailFerryRouteSection(ConventionalTrackSection):
    pass


class Polygon(Geometry):
    nodes = _dj_models.ManyToManyField(Node, related_name='polygons')


class PolygonHole(Polygon):
    parent = _dj_models.ForeignKey(Polygon, _dj_models.CASCADE, related_name='holes')

    def validate_constraints(self, exclude=None):  # TODO keep it depending on Leaflet.js’s rendering abilities
        super().validate_constraints(exclude=exclude)
        if 'parent' not in exclude and isinstance(self.parent, PolygonHole):
            raise _dj_exc.ValidationError('PolygonHole’s parent cannot be PolygonHole')


class Area(Polygon):
    pass


class Construction(Polygon):
    materials = _dj_models.ManyToManyField(ConstructionMaterial, related_name='constructions')


class Platform(Construction):
    pass


class BridgeAbutment(Construction):
    pass


class BridgePier(Construction):
    pass


class TrackInfrastructure(Construction):
    track_sections = _dj_models.ManyToManyField(TrackSection, related_name='track_infrastructures')


class Earthwork(TrackInfrastructure):
    pass


class Trench(Earthwork):
    pass


class Embankment(Earthwork):
    pass


class TrackCoverSection(TrackInfrastructure):
    pass


class TunnelSection(TrackInfrastructure):
    pass


class ManeuverStructure(TrackInfrastructure):
    pass


class CarDumper(ManeuverStructure):
    pass


class Turntable(ManeuverStructure):
    is_bridge = _dj_models.BooleanField()
    max_rotation_angle = _dj_models.FloatField(validators=[degrees_angle_validator])


class TranferTable(ManeuverStructure):
    has_pit = _dj_models.BooleanField()


class Lift(ManeuverStructure):
    pass


class BridgeSection(TrackInfrastructure):
    structure = _dj_models.ForeignKey(BridgeSectionStructure, _dj_models.PROTECT, related_name='bridge_sections')


class StaticBridgeSection(BridgeSection):
    pass


class MoveableBridgeSection(BridgeSection):
    pass


class BasculeBridgeSection(MoveableBridgeSection):
    pass


class FerrySlipSection(MoveableBridgeSection):
    pass


class LiftBridgeSection(MoveableBridgeSection):
    pass


class RetractableBridgeSection(MoveableBridgeSection):
    pass


class SeesawBridgeSection(MoveableBridgeSection):
    pass


class SubmersibleBridgeSection(MoveableBridgeSection):
    pass


class SwingBridgeSection(MoveableBridgeSection):
    pass


class TableBridgeSection(MoveableBridgeSection):
    pass


class TiltBridgeSection(MoveableBridgeSection):
    pass


class TransporterBridgeSection(MoveableBridgeSection):
    pass


class VlotbrugSection(MoveableBridgeSection):
    pass


class Building(Construction):
    pass


# endregion
# region Temporal states


class TemporalState(Serializable):
    no_overlap = False
    existence_interval = _mf.DateIntervalField()

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'existence_invertal' not in exclude and self.no_overlap:
            if self._overlaps_with():
                raise _dj_exc.ValidationError('overlapping existence intervals')

    def _overlaps_with(self, **filters):
        return any(self.existence_interval.overlaps(state.existence_interval)
                   for state in TemporalState.objects.filter(id=~_dj_models.Q(id=self.id), **filters))

    class Meta:
        abstract = True


class TemporalObjectNameState(TemporalState, Translated):
    object = _dj_models.ForeignKey(TemporalObject, _dj_models.CASCADE, related_name='name_states')


class TemporalObjectNameTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TemporalObjectNameState, _dj_models.CASCADE, related_name='translations')


class OperatorTypeState(TemporalState):
    no_overlap = True
    operator = _dj_models.ForeignKey(Operator, _dj_models.CASCADE, related_name='type_states')
    type = _dj_models.ForeignKey(OperatorType, _dj_models.PROTECT, related_name='type_states')


class OperatorState(TemporalState):
    relation = _dj_models.ForeignKey(Relation, _dj_models.CASCADE, related_name='operator_states')
    operator = _dj_models.ForeignKey(Operator, _dj_models.PROTECT, related_name='operator_states')
    entity_id_number = _dj_models.CharField(max_length=50, blank=True, null=True)

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'operator' not in exclude and self.operator.id:
            if self._overlaps_with(operator=self.operator):
                raise _dj_exc.ValidationError(
                    f'overlapping operator {self.operator} for operated entity {self.relation}')


class GeometryState(TemporalState):
    relation = _dj_models.ForeignKey(Relation, _dj_models.CASCADE, related_name='geometry_states')
    geometry = _dj_models.ForeignKey(Geometry, _dj_models.CASCADE, related_name='geometry_states')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'geometry' not in exclude and self.geometry.id:
            if self._overlaps_with(geometry=self.geometry):
                raise _dj_exc.ValidationError(f'overlapping geometry {self.geometry} for entity {self.relation}')


class TrackMainDirectionState(TemporalState):
    class Direction(_dj_models.IntegerChoices):
        NONE = 0
        FORWARD = 1
        BACKWARD = 2

    no_overlap = True
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='main_direction_states')
    direction = _dj_models.IntegerField(choices=Direction.choices)


class TrackMaximumSpeedState(TemporalState):
    no_overlap = True
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='maximum_speed_states')
    max_speed = _dj_models.FloatField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(SpeedUnit, _dj_models.PROTECT)


class TrackUseTypeState(TemporalState):
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='use_type_states')
    use_type = _dj_models.ForeignKey(TrackUseType, _dj_models.PROTECT, related_name='use_type_states')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'use_type' not in exclude and self.use_type.id:
            if self._overlaps_with(use_type=self.use_type):
                raise _dj_exc.ValidationError(
                    f'overlapping track use type {self.use_type} for track section {self.track_section}')


class CrossingTypeState(TemporalState):
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='crossing_type_states')
    type = _dj_models.ForeignKey(CrossingType, _dj_models.PROTECT, related_name='crossing_type_states')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'type' not in exclude and self.type.id:
            if self._overlaps_with(type=self.type):
                raise _dj_exc.ValidationError(
                    f'overlapping crossing type {self.type} for track section {self.track_section}')


class TrackElectrificationState(TemporalState):
    no_overlap = True
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='electrification_states')
    current_type = _dj_models.ForeignKey(CurrentType, _dj_models.PROTECT, related_name='electrification_states',
                                         null=True, blank=True)
    electrification_system = _dj_models.ForeignKey(ElectrificationSystem, _dj_models.PROTECT,
                                                   related_name='electrification_states', null=True, blank=True)
    electrified = _dj_models.BooleanField()
    tension = _dj_models.FloatField(validators=[positive_validator], null=True, blank=True)

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'electrified' not in exclude and not self.electrified and (
                self.tension is not None or self.electrification_system is not None or self.current_type is not None):
            raise _dj_exc.ValidationError(
                'tension, electrification_system and current_type should be None if electrified is False')


class TireRollwaysState(TemporalState):
    no_overlap = True
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE,
                                          related_name='tire_rollways_states')
    has_tire_rollways = _dj_models.BooleanField()


class TrackPitState(TemporalState):
    no_overlap = True
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE, related_name='pit_states')
    has_pit = _dj_models.BooleanField()


class TractionTypeState(TemporalState):
    no_overlap = True
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE,
                                          related_name='traction_type_states')
    traction_type = _dj_models.ForeignKey(TractionType, _dj_models.PROTECT, related_name='traction_type_states')


class RailTypeState(TemporalState):
    no_overlap = True
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE, related_name='rail_type_states')
    rail_type = _dj_models.ForeignKey(RailType, _dj_models.PROTECT, related_name='rail_type_states')


class TieTypeState(TemporalState):
    no_overlap = True
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE, related_name='tie_type_states')
    tie_type = _dj_models.ForeignKey(TieType, _dj_models.PROTECT, related_name='tie_type_states')


class RuinState(TemporalState):
    no_overlap = True
    construction = _dj_models.ForeignKey(Construction, _dj_models.CASCADE, related_name='ruin_states')
    ruined = _dj_models.BooleanField()


class ManeuverStructureMovingPartState(TemporalState):
    no_overlap = True
    maneuver_structure = _dj_models.ForeignKey(ManeuverStructure, _dj_models.CASCADE, related_name='moving_part_states')
    has_moving_part = _dj_models.BooleanField()


class FloorState(TemporalState):
    no_overlap = True
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='floor_states')
    floors_number = _dj_models.IntegerField(validators=[positive_validator])
    basement_floors_number = _dj_models.IntegerField(validators=[positive_validator])


class BuildingHeightState(TemporalState):
    no_overlap = True
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='height_states')
    height = _dj_models.FloatField(validators=[positive_validator])


class BuildingTypeState(TemporalState):
    no_overlap = True
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='type_states')
    type = _dj_models.ForeignKey(BuildingType, _dj_models.PROTECT, related_name='type_states')


class BuildingUseTypeState(TemporalState):
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='use_type_states')
    use_type = _dj_models.ForeignKey(BuildingUseType, _dj_models.PROTECT, related_name='use_type_states')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'use_type' not in exclude and self.use_type.id:
            if self._overlaps_with(use_type=self.use_type):
                raise _dj_exc.ValidationError(
                    f'overlapping use type {self.use_type} for building {self.building}')


class LiftHeighState(TemporalState):
    no_overlap = True
    lift = _dj_models.ForeignKey(Lift, _dj_models.CASCADE, related_name='height_states')
    height = _dj_models.FloatField(validators=[positive_validator])


class TrackInfrastructureUseTypeState(TemporalState):
    track_infrastructure = _dj_models.ForeignKey(TrackInfrastructure, _dj_models.CASCADE,
                                                 related_name='use_type_states')
    use_type = _dj_models.ForeignKey(TrackInfrastructureUseType, _dj_models.PROTECT, related_name='use_type_states')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if 'use_type' not in exclude and self.use_type.id:
            if self._overlaps_with(use_type=self.use_type):
                raise _dj_exc.ValidationError(
                    f'overlapping use type {self.use_type} for track infrastructure {self.track_infrastructure}')


# endregion
# region Edit system


class EditGroup(_dj_models.Model):
    date = _dj_models.DateTimeField()
    author = _dj_models.ForeignKey('CustomUser', on_delete=_dj_models.PROTECT, related_name='edit_groups')
    comment = _dj_models.TextField(null=True, blank=True)

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if EditGroup.objects.filter(_dj_models.Q(date=self.date, author=self.author)
                                    & ~_dj_models.Q(id=self.id)).exists():
            raise _dj_exc.ValidationError(
                f'user {self.author.username} attempted to make multiple edits at the exact same time',
                code='edit_group_duplicate_date'
            )


class Edit(_dj_models.Model):
    edit_group = _dj_models.ForeignKey(EditGroup, on_delete=_dj_models.CASCADE)
    object_id = _dj_models.IntegerField(validators=[positive_validator])
    object_type = _dj_models.CharField(max_length=50)

    class Meta:
        abstract = True


class ObjectEdit(Edit):
    operation = _dj_models.CharField(max_length=10, choices=tuple((v, v) for v in _cons.OBJECT_EDIT_ACTIONS))
    # JSON serialization of deleted object, null for creation
    deleted_data = _dj_models.JSONField(null=True, blank=True)

    @property
    def deleted_object(self) -> Serializable | None:
        if self.deleted_data is None:
            return None
        # noinspection PyTypeChecker
        data = _json.loads(self.deleted_data)
        class_ = globals()[data['class']]
        if not issubclass(class_, Serializable):
            raise TypeError(f'expected Serializable subclass, got {class_}')
        return class_.deserialize_full(data['data'])

    @deleted_object.setter
    def deleted_object(self, o: Serializable | None):
        if o is None:
            self.deleted_data = None
        else:
            if not isinstance(o, Serializable):
                raise TypeError(f'expected Serializable object, got {o.__class__}')
            self.deleted_data = _json.dumps({'class': o.__class__.__name__, 'data': o.serialize_full()})


class RelationEdit(Edit):
    operation = _dj_models.CharField(max_length=10, choices=tuple((v, v) for v in _cons.RELATION_EDIT_ACTIONS))
    relation_name = _dj_models.CharField(max_length=100)

    class Meta:
        abstract = True


class ObjectRelationEdit(RelationEdit):
    serialized_target_object = _dj_models.JSONField(null=True, blank=True)

    @property
    def target_object(self) -> Serializable | None:
        if self.serialized_target_object is None:
            return None
        return self._deserialize_object(self.serialized_target_object)

    @target_object.setter
    def target_object(self, o: Serializable | None):
        if o is None:
            self.serialized_target_object = None
        else:
            self.serialized_target_object = self._serialize_object(o)

    @staticmethod
    def _deserialize_object(json_string: str) -> Serializable:
        data = _json.loads(json_string)
        class_ = globals()[data['class']]
        if not issubclass(class_, Serializable):
            raise TypeError(f'expected Serializable subclass, got {class_}')
        return class_.deserialize_reference(data['id'])

    @staticmethod
    def _serialize_object(o: Serializable) -> str:
        if not isinstance(o, Serializable):
            raise TypeError(f'expected Serializable object, got {o.__class__}')
        return _json.dumps(o.serialize_reference())


class ObjectPropertyEdit(RelationEdit):
    serialized_value = _dj_models.JSONField(null=True, blank=True)

    @property
    def value(self):
        return self._deserialize_value(self.serialized_value)

    @value.setter
    def value(self, value):
        self.serialized_value = self._serialize_value(value)

    @staticmethod
    def _deserialize_value(json_string: str):
        data = _json.loads(json_string)
        type_ = data['type']
        value = data.get('value')
        if type_ in ('int', 'float', 'str', 'bool', None):
            return value
        if type_ == _dt.DateInterval.__name__:
            return _dt.DateInterval.from_string(value)
        raise TypeError(f'cannot deserialize type {type_}')

    @staticmethod
    def _serialize_value(v) -> str:
        if v is None:
            return _json.dumps({'type': None})
        if isinstance(v, int | float | str | bool):
            return _json.dumps({'type': v.__class__.__name__, 'value': v})
        if isinstance(v, _dt.DateInterval):
            return _json.dumps({'type': v.__class__.__name__, 'value': str(v)})
        # noinspection PyUnresolvedReferences
        raise TypeError(f'cannot serialize type {v.__class__.__name__}')

# endregion
