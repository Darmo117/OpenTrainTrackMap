from __future__ import annotations

import base64 as _b64
import struct as _struct

import django.core.exceptions as _dj_exc
import django.db.models as _dj_models

from . import _i18n_models
from .. import model_fields as _mf
from ..api import data_types as _dt


# region Validators


def positive_validator(v: float | int):
    if v < 0:
        raise _dj_exc.ValidationError(f'negative value: {v}')


def degrees_angle_validator(v: float | int):
    if not (0 <= v <= 360):
        raise _dj_exc.ValidationError(f'invalid degrees angle value: {v}')


# endregion
# region Translations

class Translated(_dj_models.Model):
    # The 'translations' attribute should be defined by Translation subclasses as the relation’s 'related_name'

    def get_translations(self) -> dict[_i18n_models.Language, str]:
        # self.translations defined in subclasses of Translation as related_name
        # noinspection PyUnresolvedReferences
        return {t.language: t.label for t in self.translations.all()}

    def get_translation(self, language: _i18n_models.Language) -> str | None:
        try:
            # noinspection PyUnresolvedReferences
            return self.translations.get(language=language)
        except _dj_exc.ObjectDoesNotExist:
            return None

    class Meta:
        abstract = True


class Translation(_dj_models.Model):
    translated_object: Translated  # Defined in subclasses
    language = _dj_models.ForeignKey(_i18n_models.Language, _dj_models.CASCADE)
    label = _dj_models.CharField(max_length=100)

    class Meta:
        abstract = True
        unique_together = ('translated_object', 'language', 'label')


# endregion
# region Enumerations


class Enumeration(Translated):
    label = _dj_models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True


class ConstructionMaterial(Enumeration):
    pass


class ConstructionMaterialTranslation(Translation):
    translated_object = _dj_models.ForeignKey(ConstructionMaterial, _dj_models.CASCADE, related_name='translations')


class TrackInfrastructureUseType(Enumeration):
    pass


class TrackInfrastructureUseTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TrackInfrastructureUseType, _dj_models.CASCADE,
                                              related_name='translations')


class BridgeStructure(Enumeration):
    pass


class BridgeStructureTranslation(Translation):
    translated_object = _dj_models.ForeignKey(BridgeStructure, _dj_models.CASCADE, related_name='translations')


class BuildingType(Enumeration):
    pass


class BuildingTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(BuildingType, _dj_models.CASCADE, related_name='translations')


class BuildingUseType(Enumeration):
    pass


class BuildingUseTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(BuildingUseType, _dj_models.CASCADE, related_name='translations')


class TrackUseType(Enumeration):
    pass


class TrackUseTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TrackUseType, _dj_models.CASCADE, related_name='translations')


class CrossingType(Enumeration):
    pass


class CrossingTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(CrossingType, _dj_models.CASCADE, related_name='translations')


class ElectrificationSystem(Enumeration):
    pass


class ElectrificationSystemTranslation(Translation):
    translated_object = _dj_models.ForeignKey(ElectrificationSystem, _dj_models.CASCADE, related_name='translations')


class CurrentType(Enumeration):
    pass


class CurrentTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(CurrentType, _dj_models.CASCADE, related_name='translations')


class TractionType(Enumeration):
    pass


class TractionTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TractionType, _dj_models.CASCADE, related_name='translations')


class RailType(Enumeration):
    pass


class RailTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(RailType, _dj_models.CASCADE, related_name='translations')


class TieType(Enumeration):
    pass


class TieTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TieType, _dj_models.CASCADE, related_name='translations')


class OperatorType(Enumeration):
    pass


class OperatorTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(OperatorType, _dj_models.CASCADE, related_name='translations')


# endregion
# region Objects


class Unit(Translated):
    symbol = _dj_models.CharField(max_length=10, unique=True)


class UnitTranslation(Translation):
    translated_object = _dj_models.ForeignKey(Unit, _dj_models.CASCADE, related_name='translations')


class LengthUnit(Unit):
    pass


class SpeedUnit(Unit):
    pass


class TemporalObject(_dj_models.Model):
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


class Note(_dj_models.Model):
    author = _dj_models.ForeignKey('CustomUser', on_delete=_dj_models.PROTECT, related_name='notes')
    text = _dj_models.TextField()
    geometries = _dj_models.ManyToManyField(Geometry, related_name='notes')


class Node(_dj_models.Model):
    altitude = _dj_models.FloatField()
    latitude = _dj_models.FloatField()

    class Meta:
        abstract = True


class IsolatedNode(Node, Geometry):
    pass


class SignalMast(IsolatedNode):
    pass


class SegmentNode(Node):
    pass


class Polyline(Geometry):
    nodes = _dj_models.ManyToManyField(SegmentNode, related_name='polylines', through='PolylineNodes')


class PolylineNodes(_dj_models.Model):
    node = _dj_models.ForeignKey(SegmentNode, _dj_models.CASCADE)
    polyline = _dj_models.ForeignKey(Polyline, _dj_models.CASCADE)
    order = _dj_models.IntegerField()

    class Meta:
        ordering = ('order',)


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
    nodes = _dj_models.ManyToManyField(SegmentNode, related_name='polygons', through='PolygonNodes')


class PolygonNodes(_dj_models.Model):
    node = _dj_models.ForeignKey(SegmentNode, _dj_models.CASCADE)
    polygon = _dj_models.ForeignKey(Polygon, _dj_models.CASCADE)
    order = _dj_models.IntegerField()

    class Meta:
        ordering = ('order',)


class PolygonHole(Polygon):
    parent = _dj_models.ForeignKey(Polygon, _dj_models.CASCADE, related_name='holes')

    def validate_constraints(self, exclude=None):  # TODO keep it depending on Leaflet.js’s rendering abilities
        super().validate_constraints(exclude=exclude)
        if (exclude is None or 'parent' not in exclude) and isinstance(self.parent, PolygonHole):
            raise _dj_exc.ValidationError('PolygonHole cannot have parents of type PolygonHole')


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
    structure = _dj_models.ForeignKey(BridgeStructure, _dj_models.PROTECT, related_name='bridge_sections')


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


class TemporalState(_dj_models.Model):
    existence_interval = _mf.DateIntervalField()

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        filters = {k: getattr(self, k) for k in self._get_overlap_filter()}
        if (
                filters
                and (exclude is None or 'existence_invertal' not in exclude and not any(k in exclude for k in filters))
                and self._overlaps_any(**filters)
        ):
            raise _dj_exc.ValidationError(f'overlapping existence intervals for objects: {filters}')

    def _overlaps_any(self, **filters):
        return any(self.existence_interval.overlaps(state.existence_interval)
                   for state in TemporalState.objects.filter(id=~_dj_models.Q(id=self.id), **filters))

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ()

    class Meta:
        abstract = True


class TemporalObjectNameState(TemporalState, Translated):
    object = _dj_models.ForeignKey(TemporalObject, _dj_models.CASCADE, related_name='name_states')


class TemporalObjectNameStateTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TemporalObjectNameState, _dj_models.CASCADE, related_name='translations')


class OperatorTypeState(TemporalState):
    operator = _dj_models.ForeignKey(Operator, _dj_models.CASCADE, related_name='type_states')
    type = _dj_models.ForeignKey(OperatorType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('operator',)


class OperatorState(TemporalState):
    operator = _dj_models.ForeignKey(Operator, _dj_models.PROTECT, related_name='operator_states')
    relation = _dj_models.ForeignKey(Relation, _dj_models.CASCADE, related_name='operator_states')
    entity_id_number = _dj_models.CharField(max_length=50, blank=True, null=True)  # For train routes only

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return 'operator', 'relation'


class ContainedGeometryState(TemporalState):
    relation = _dj_models.ForeignKey(Relation, _dj_models.CASCADE, related_name='geometry_states')
    geometry = _dj_models.ForeignKey(Geometry, _dj_models.CASCADE, related_name='geometry_states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return 'relation', 'geometry'


class TrackMainDirectionState(TemporalState):
    class Direction(_dj_models.IntegerChoices):
        FORWARD = 0
        BACKWARD = 1

    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='main_direction_states')
    reversed = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)


class TrackMaximumSpeedState(TemporalState):
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='maximum_speed_states')
    max_speed = _dj_models.FloatField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(SpeedUnit, _dj_models.PROTECT)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)


class TrackUseTypeState(TemporalState):
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='use_type_states')
    use_type = _dj_models.ForeignKey(TrackUseType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return 'track_section', 'use_type'


class CrossingTypeState(TemporalState):
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='crossing_type_states')
    type = _dj_models.ForeignKey(CrossingType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return 'track_section', 'type'


class TrackElectrificationState(TemporalState):
    track_section = _dj_models.ForeignKey(TrackSection, _dj_models.CASCADE, related_name='electrification_states')
    current_type = _dj_models.ForeignKey(CurrentType, _dj_models.PROTECT, related_name='states', null=True, blank=True)
    electrification_system = _dj_models.ForeignKey(ElectrificationSystem, _dj_models.PROTECT, related_name='states',
                                                   null=True, blank=True)
    electrified = _dj_models.BooleanField()
    tension = _dj_models.FloatField(validators=[positive_validator], null=True, blank=True)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if (
                (exclude is None or 'electrified' not in exclude)
                and not self.electrified
                and (self.tension is not None
                     or self.electrification_system is not None
                     or self.current_type is not None)
        ):
            raise _dj_exc.ValidationError(
                'tension, electrification_system and current_type should be None if electrified is False')


class TireRollwaysState(TemporalState):
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE,
                                          related_name='tire_rollways_states')
    has_tire_rollways = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)


class TrackPitState(TemporalState):
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE, related_name='pit_states')
    has_pit = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)


class TractionTypeState(TemporalState):
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE,
                                          related_name='traction_type_states')
    traction_type = _dj_models.ForeignKey(TractionType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)


class RailTypeState(TemporalState):
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE, related_name='rail_type_states')
    rail_type = _dj_models.ForeignKey(RailType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)


class TieTypeState(TemporalState):
    track_section = _dj_models.ForeignKey(ConventionalTrackSection, _dj_models.CASCADE, related_name='tie_type_states')
    tie_type = _dj_models.ForeignKey(TieType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track_section',)


class RuinState(TemporalState):
    construction = _dj_models.ForeignKey(Construction, _dj_models.CASCADE, related_name='ruin_states')
    ruined = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('construction',)


class ManeuverStructureMovingPartState(TemporalState):
    structure = _dj_models.ForeignKey(ManeuverStructure, _dj_models.CASCADE, related_name='moving_part_states')
    has_moving_part = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('structure',)


class FloorState(TemporalState):
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='floor_states')
    floors_number = _dj_models.IntegerField(validators=[positive_validator])
    basements_number = _dj_models.IntegerField(validators=[positive_validator])

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('building',)


class BuildingHeightState(TemporalState):
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='height_states')
    height = _dj_models.FloatField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(LengthUnit, _dj_models.PROTECT)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('building',)


class BuildingTypeState(TemporalState):
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='type_states')
    type = _dj_models.ForeignKey(BuildingType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('building',)


class BuildingUseTypeState(TemporalState):
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='use_type_states')
    use_type = _dj_models.ForeignKey(BuildingUseType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return 'building', 'use_type'


class LiftHeighState(TemporalState):
    lift = _dj_models.ForeignKey(Lift, _dj_models.CASCADE, related_name='height_states')
    height = _dj_models.FloatField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(LengthUnit, _dj_models.PROTECT)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('lift',)


class TrackInfrastructureUseTypeState(TemporalState):
    infrastructure = _dj_models.ForeignKey(TrackInfrastructure, _dj_models.CASCADE, related_name='use_type_states')
    use_type = _dj_models.ForeignKey(TrackInfrastructureUseType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return 'infrastructure', 'use_type'


class BufferStopState(TemporalState):
    node = _dj_models.ForeignKey(SegmentNode, _dj_models.CASCADE, related_name='buffer_stop_states')
    is_present = _dj_models.BooleanField()


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
    edit_group = _dj_models.ForeignKey(EditGroup, on_delete=_dj_models.CASCADE, related_name='edits')
    object_id = _dj_models.IntegerField(validators=[positive_validator])
    object_type = _dj_models.CharField(max_length=50)

    def get_object(self) -> _dj_models.Model | None:
        try:
            return globals()[self.object_type].objects.get(id=self.object_id)
        except _dj_exc.ObjectDoesNotExist:
            return None


class ObjectAdded(Edit):
    pass


class ObjectDeleted(Edit):
    pass


class ObjectPropertyEdit(Edit):
    property_name = _dj_models.CharField(max_length=50)
    old_value = _dj_models.TextField(blank=True, null=True)
    new_value = _dj_models.TextField(blank=True, null=True)

    def get_old_value(self):
        return self._deserialize_value(self.old_value)

    def set_old_value(self, v):
        self.old_value = self._serialize_value(v)

    def get_new_value(self):
        return self._deserialize_value(self.new_value)

    def set_new_value(self, v):
        self.new_value = self._serialize_value(v)

    @classmethod
    def _serialize_value(cls, v) -> str | None:
        match v:
            case None:
                return None
            case int(v):
                return 'int:' + cls._to_base_64(v, 'q')
            case float(v):
                return 'float:' + cls._to_base_64(v, 'd')
            case bool(v):
                return 'bool:' + ('1' if v else '0')
            case str(v):
                return 'str:' + v
            case v if isinstance(v, _dt.DateInterval):
                return 'DateInterval:' + _mf.DateIntervalField.to_string(v)
            case v if isinstance(v, _dj_models.Model):
                return f'Model:{type(v)}:{v.id}'
            case v:
                raise TypeError(f'unsupported type: {type(v)}')

    @staticmethod
    def _to_base_64(v, f: str) -> str:
        b = _struct.pack(f'>{f}', v)
        return _b64.b64encode(b).decode('ascii')

    @classmethod
    def _deserialize_value(cls, s: str | None):
        if s is None:
            return None
        type_name, serialized_value = s.split(':', maxsplit=1)
        match type_name:
            case 'int':
                return cls._from_base64(serialized_value, 'q')
            case 'float':
                return cls._from_base64(serialized_value, 'd')
            case 'bool':
                return bool(int(serialized_value))
            case 'str':
                return serialized_value
            case 'DateInterval':
                return _mf.DateIntervalField.parse(serialized_value)
            case 'Model':
                t, v = serialized_value.split(':', maxsplit=1)
                try:
                    return globals()[t].objects.get(id=int(v))
                except _dj_exc.ObjectDoesNotExist:
                    return None  # TODO raise error instead?
            case t:
                raise TypeError(f'unsupported type: {t}')

    @staticmethod
    def _from_base64(s: str, f: str):
        b = _b64.b64decode(s.encode('ascii'))
        return _struct.unpack(f'>{f}', b)[0]


class ObjectTranslationEdit(Edit):
    old_label = _dj_models.TextField(blank=True, null=True)
    new_label = _dj_models.TextField(blank=True, null=True)
    language = _dj_models.ForeignKey(_i18n_models.Language, _dj_models.CASCADE)

# endregion
