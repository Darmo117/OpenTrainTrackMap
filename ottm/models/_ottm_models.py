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
        raise _dj_exc.ValidationError(f'negative value: {v}', code='negative_value')


def degrees_angle_validator(v: float | int):
    if not (0 <= v <= 360):
        raise _dj_exc.ValidationError(f'invalid degrees angle value: {v}', code='invalid_angle_range')


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
    label = _dj_models.TextField()

    class Meta:
        abstract = True
        unique_together = ('translated_object', 'language', 'label')


# endregion
# region Enumerations


class Enumeration(Translated):
    label = _dj_models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True


class SurfaceMaterial(Enumeration):
    pass


class SurfaceMaterialTranslation(Translation):
    translated_object = _dj_models.ForeignKey(SurfaceMaterial, _dj_models.CASCADE, related_name='translations')


class ConstructionMaterial(Enumeration):
    pass


class ConstructionMaterialTranslation(Translation):
    translated_object = _dj_models.ForeignKey(ConstructionMaterial, _dj_models.CASCADE, related_name='translations')


class BarrierType(Enumeration):
    pass


class BarrierTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(BarrierType, _dj_models.CASCADE, related_name='translations')


class TrackInfrastructureUsage(Enumeration):
    pass


class TrackInfrastructureUsageTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TrackInfrastructureUsage, _dj_models.CASCADE, related_name='translations')


class BridgeStructure(Enumeration):
    pass


class BridgeStructureTranslation(Translation):
    translated_object = _dj_models.ForeignKey(BridgeStructure, _dj_models.CASCADE, related_name='translations')


class BuildingUsage(Enumeration):
    pass


class BuildingUseTranslation(Translation):
    translated_object = _dj_models.ForeignKey(BuildingUsage, _dj_models.CASCADE, related_name='translations')


class TrackLevel(Enumeration):
    pass


class TrackLevelTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TrackLevel, _dj_models.CASCADE, related_name='translations')


class TrackService(Enumeration):
    pass


class TrackServiceTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TrackService, _dj_models.CASCADE, related_name='translations')


class TrackUsage(Enumeration):
    pass


class TrackUsageTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TrackUsage, _dj_models.CASCADE, related_name='translations')


class ElectrificationSystem(Enumeration):
    pass


class ElectrificationSystemTranslation(Translation):
    translated_object = _dj_models.ForeignKey(ElectrificationSystem, _dj_models.CASCADE, related_name='translations')


class CurrentType(Enumeration):
    pass


class CurrentTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(CurrentType, _dj_models.CASCADE, related_name='translations')


class TractionSystem(Enumeration):
    pass


class TractionSystemTranslation(Translation):
    translated_object = _dj_models.ForeignKey(TractionSystem, _dj_models.CASCADE, related_name='translations')


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


class SegmentNodeType(Enumeration):
    pass


class SegmentNodeTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(SegmentNodeType, _dj_models.CASCADE, related_name='translations')


class CrossingBarrierType(Enumeration):
    pass


class CrossingBarrierTypeTranslation(Translation):
    translated_object = _dj_models.ForeignKey(CrossingBarrierType, _dj_models.CASCADE, related_name='translations')


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
    latitude = _dj_models.FloatField()
    longitude = _dj_models.FloatField()

    class Meta:
        abstract = True


class IsolatedNode(Node, Geometry):
    pass


class SignalMast(IsolatedNode):
    pass


class OverheadLinePylon(IsolatedNode):
    pass


class PointOfInterest(IsolatedNode):
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


class Barrier(Polyline):
    materials = _dj_models.ManyToManyField(ConstructionMaterial, related_name='barriers')
    type = _dj_models.ForeignKey(BarrierType, _dj_models.PROTECT, related_name='type', blank=True, null=True)


class Gate(Polyline):
    pass


class Track(Polyline):
    level = _dj_models.ForeignKey(TrackLevel, _dj_models.CASCADE, related_name='tracks')


class VALTrack(Track):
    pass


class MonorailTrack(Track):
    materials = _dj_models.ManyToManyField(ConstructionMaterial, related_name='monorail_tracks')


class RubberTiredTramTrack(MonorailTrack):
    pass


class GLTTrack(Track):  # Guided Light Transit
    unguided = _dj_models.BooleanField()


class TranshlohrTrack(Track):
    pass


class LartigueMonorailTrack(Track):
    pass


class StraddleBeamMonorailTrack(Track):
    pass


class MaglevMonorailTrack(StraddleBeamMonorailTrack):
    pass


class InvertedTMonorailTrack(MonorailTrack):
    pass


class SuspendedMonorailTrack(MonorailTrack):
    pass


class SAFEGEMonorailTrack(SuspendedMonorailTrack):
    pass


class GroundRailMonorailTrack(MonorailTrack):
    pass


class GyroscopicMonorailTrack(GroundRailMonorailTrack):
    pass


class AddisMonorailTrack(GroundRailMonorailTrack):
    pass


class PSMTMonorailTrack(GroundRailMonorailTrack):
    pass


class CailletMonorailTrack(GroundRailMonorailTrack):
    pass


class TrackGauge(_dj_models.Model):
    gauge = _dj_models.IntegerField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(LengthUnit, _dj_models.PROTECT)


class ConventionalTrack(Track):
    gauges = _dj_models.ManyToManyField(TrackGauge, related_name='tracks')


class RailFerryRoute(ConventionalTrack):
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
            raise _dj_exc.ValidationError(
                'PolygonHole cannot have parents of type PolygonHole',
                code='polygon_hole_invalid_parent'
            )


class Area(Polygon):
    pass


class Platform(Polygon):
    material = _dj_models.ForeignKey(SurfaceMaterial, _dj_models.PROTECT, related_name='platforms',
                                     blank=True, null=True)


class Construction(Polygon):
    materials = _dj_models.ManyToManyField(ConstructionMaterial, related_name='constructions')


class BridgeAbutment(Construction):
    pass


class BridgePier(Construction):
    pass


class TrackInfrastructure(Construction):
    tracks = _dj_models.ManyToManyField(Track, related_name='track_infrastructures')


class Earthwork(TrackInfrastructure):
    pass


class Trench(Earthwork):
    pass


class Embankment(Earthwork):
    pass


class TrackCover(TrackInfrastructure):
    pass


class Tunnel(TrackInfrastructure):
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


class Bridge(TrackInfrastructure):
    structure = _dj_models.ForeignKey(BridgeStructure, _dj_models.PROTECT, related_name='bridges',
                                      blank=True, null=True)


class StaticBridge(Bridge):
    pass


class MoveableBridge(Bridge):
    pass


class BasculeBridge(MoveableBridge):
    pass


class FerrySlip(MoveableBridge):
    pass


class LiftBridge(MoveableBridge):
    pass


class RetractableBridge(MoveableBridge):
    pass


class SeesawBridge(MoveableBridge):
    pass


class SubmersibleBridge(MoveableBridge):
    pass


class SwingBridge(MoveableBridge):
    pass


class TableBridge(MoveableBridge):
    pass


class TiltBridge(MoveableBridge):
    pass


class TransporterBridge(MoveableBridge):
    pass


class Vlotbrug(MoveableBridge):
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
            raise _dj_exc.ValidationError(
                f'overlapping existence intervals for objects: {filters}',
                code='temporal_state_overlap'
            )

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
    operator = _dj_models.ForeignKey(Operator, _dj_models.CASCADE, related_name='operator_states')
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

    track = _dj_models.ForeignKey(Track, _dj_models.CASCADE, related_name='main_direction_states')
    reversed = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class TrackMaximumSpeedState(TemporalState):
    track = _dj_models.ForeignKey(Track, _dj_models.CASCADE, related_name='maximum_speed_states')
    max_speed = _dj_models.FloatField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(SpeedUnit, _dj_models.PROTECT)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class TrackServiceState(TemporalState):
    track = _dj_models.ForeignKey(Track, _dj_models.CASCADE, related_name='service_states')
    service = _dj_models.ForeignKey(TrackService, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class TrackUsageState(TemporalState):
    track = _dj_models.ForeignKey(Track, _dj_models.CASCADE, related_name='usage_states')
    usage = _dj_models.ForeignKey(TrackUsage, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class TrackElectrificationState(TemporalState):
    track = _dj_models.ForeignKey(Track, _dj_models.CASCADE, related_name='electrification_states')
    electrified = _dj_models.BooleanField()
    current_type = _dj_models.ForeignKey(CurrentType, _dj_models.PROTECT, related_name='states', null=True, blank=True)
    electrification_system = _dj_models.ForeignKey(ElectrificationSystem, _dj_models.PROTECT, related_name='states',
                                                   null=True, blank=True)
    tension = _dj_models.FloatField(validators=[positive_validator], null=True, blank=True)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)

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
                'tension, electrification_system and current_type should be None if electrified is False',
                'track_electrification_state_invalid_electricity_data'
            )


class TireRollwaysState(TemporalState):
    track = _dj_models.ForeignKey(ConventionalTrack, _dj_models.CASCADE, related_name='tire_rollways_states')
    has_tire_rollways = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class TrackPitState(TemporalState):
    track = _dj_models.ForeignKey(ConventionalTrack, _dj_models.CASCADE, related_name='pit_states')
    has_pit = _dj_models.BooleanField()

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class TractionSystemState(TemporalState):
    track = _dj_models.ForeignKey(ConventionalTrack, _dj_models.CASCADE, related_name='traction_system_states')
    traction_system = _dj_models.ForeignKey(TractionSystem, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class RailTypeState(TemporalState):
    track = _dj_models.ForeignKey(ConventionalTrack, _dj_models.CASCADE, related_name='rail_type_states')
    rail_type = _dj_models.ForeignKey(RailType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


class TieTypeState(TemporalState):
    track = _dj_models.ForeignKey(ConventionalTrack, _dj_models.CASCADE, related_name='tie_type_states')
    tie_type = _dj_models.ForeignKey(TieType, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('track',)


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


class ManeuverStructureTrackState(TemporalState):
    structure = _dj_models.ForeignKey(ManeuverStructure, _dj_models.CASCADE, related_name='track_states')
    has_track = _dj_models.BooleanField()

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


class BuildingUsageState(TemporalState):
    building = _dj_models.ForeignKey(Building, _dj_models.CASCADE, related_name='usage_states')
    usage = _dj_models.ForeignKey(BuildingUsage, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('building',)


class LiftHeighState(TemporalState):
    lift = _dj_models.ForeignKey(Lift, _dj_models.CASCADE, related_name='height_states')
    height = _dj_models.FloatField(validators=[positive_validator])
    unit = _dj_models.ForeignKey(LengthUnit, _dj_models.PROTECT)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('lift',)


class TrackInfrastructureUsageState(TemporalState):
    infrastructure = _dj_models.ForeignKey(TrackInfrastructure, _dj_models.CASCADE, related_name='usage_states')
    usage = _dj_models.ForeignKey(TrackInfrastructureUsage, _dj_models.PROTECT, related_name='states')

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('infrastructure',)


class SegmentNodeTypeState(TemporalState):
    node = _dj_models.ForeignKey(SegmentNode, _dj_models.CASCADE, related_name='type_states')
    type = _dj_models.ForeignKey(SegmentNodeType, _dj_models.PROTECT, related_name='states')
    # Field when type is a crossing
    has_crossing_lights = _dj_models.BooleanField(blank=True, null=True)
    has_crossing_bells = _dj_models.BooleanField(blank=True, null=True)
    has_crossing_markings = _dj_models.BooleanField(blank=True, null=True)
    crossing_barriers_type = _dj_models.ForeignKey(CrossingBarrierType, _dj_models.PROTECT, related_name='states',
                                                   blank=True, null=True)

    def _get_overlap_filter(self) -> tuple[str, ...]:
        return ('node',)

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude)
        if ('crossing' not in self.type.label and (
                self.has_crossing_lights is not None
                or self.has_crossing_bells is not None
                or self.has_crossing_markings is not None
                or self.crossing_barriers_type is not None)):
            raise _dj_exc.ValidationError(
                'non-crossing node cannot have non-null crossing-related fields',
                code='segment_node_type_state_invalid_crossing_data'
            )


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
