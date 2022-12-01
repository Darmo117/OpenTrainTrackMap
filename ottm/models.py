from __future__ import annotations

import datetime
import functools
import math
import typing as typ

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_auth_models
import django.core.exceptions as dj_exc
import django.core.validators as dj_valid
import django.db.models as dj_models
import geopy.distance as geopy_dist
import pyproj
import shapely.geometry.polygon as sh_polygon
import shapely.ops as sh_ops

from . import settings, model_fields


def lang_code_validator(value: str):
    if value not in settings.LANGUAGES:
        raise dj_exc.ValidationError(f'invalid language code "{value}"', code='invalid_language')


###############
# Site models #
###############


class UserInfo(dj_models.Model):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    language_code = dj_models.CharField(max_length=20, validators=[lang_code_validator])
    is_administrator = dj_models.BooleanField(default=False)

    @property
    def prefered_language(self) -> settings.Language:
        return settings.LANGUAGES[self.language_code]


class User:
    """Simple wrapper class for a Django user and its associated user data."""

    def __init__(self, django_user: dj_auth_models.AbstractUser, data: typ.Optional[UserInfo]):
        self.__django_user = django_user
        self.__data = data

    @property
    def django_user(self) -> dj_auth_models.AbstractUser:
        return self.__django_user

    @property
    def data(self) -> typ.Optional[UserInfo]:
        return self.__data

    @property
    def username(self) -> str:
        return self.__django_user.username

    @property
    def is_logged_in(self) -> bool:
        return self.__django_user.is_authenticated

    @property
    def prefered_language(self) -> settings.Language:
        return self.__data.prefered_language if self.__data else settings.LANGUAGES[settings.DEFAULT_LANGUAGE]

    @property
    def is_admin(self) -> bool:
        return self.__data.is_administrator if self.__data else False

    @property
    def notes_count(self) -> int:
        return 0  # TODO

    @property
    def edits_count(self) -> int:
        return 0  # TODO

    @property
    def wiki_edits_count(self) -> int:
        import WikiPy.api.users as wpy_api_users
        return len(wpy_api_users.get_user_contributions(wpy_api_users.get_user_from_name(self.username), self.username))

    def __repr__(self):
        return f'User[django_user={self.__django_user.username},data={self.__data}]'


##############
# Data model #
##############
# TODO edit history


def inf_validator_generator(inf: float) -> typ.Callable[[float], None]:
    return dj_valid.MinValueValidator(inf, message=f'value should be greater than {inf}')


positive_value_validator = inf_validator_generator(0)


def future_date_validator(date: datetime.datetime):
    if date and date > datetime.datetime.now():
        raise dj_exc.ValidationError('date is in the future', code='future_date')


def non_empty_text_validator(value: str):
    if value.strip() == '':
        raise dj_exc.ValidationError('text is empty', code='empty_text')


class BaseObject(dj_models.Model):
    """Base class of the data model."""

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True


class WikidataQObject(BaseObject):
    """An object that corresponds to a Wikidata QID"""
    qid = dj_models.CharField(max_length=16, validators=[dj_valid.RegexValidator(
        regex=r'^Q\d+$', message='invalid Wikidata QID "%(value)s"', code='invalid_qid')])


class Source(BaseObject):
    """An object used to source information. The "source" field is free text."""
    source = dj_models.TextField()

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if not exclude or 'source' not in exclude:
            self.source = self.source.strip()


class SourcedObject(BaseObject):
    """An object that may have attached sources and Wikidata QIDs."""
    sources = dj_models.ManyToManyField(Source, related_name='objects')
    qids = dj_models.ManyToManyField(WikidataQObject, related_name='linked_objects')


# Temporal models


class TemporalObject(SourcedObject):
    """An object that exists for a specific time interval. This model is abstract."""
    time_span = model_fields.TimeIntervalField()

    class Meta:
        abstract = True


class TemporalProperty(SourcedObject):
    """A property that associates some values to an object for a specific time interval.

    The "object_name" attribute should hold the name of the attribute that points to the associated
    object instance.

    By default, for a given object, the absence of a property for a given time interval means that
    its value is unknown for this period. This behavior can be disabled by setting the "absent_means_none"
    attribute to True.

    By default, for a given object, time intervals for different instances of a property cannot overlap.
    This constraint can be disable by setting the "prevent_overlaps" attribute to False.

    Note: No checks are performed to ensure that properties’ time intervals fit inside the associated
    object’s time interval. This is intended as to ease editing by users.

    This model is abstract.
    """
    time_span = model_fields.TimeIntervalField()
    # Name of the field that points to the object this property applies to.
    # It should be an instance of a TemporalObject subclass.
    object_name = None
    # Whether the absence of a property on a given interval means that the property does not apply or is unknown.
    absent_means_none = False
    # Whether the instances of this property can overlap for a given object.
    prevent_overlaps = True

    def clean(self):
        super().clean()
        obj: TemporalObject = getattr(self, self.object_name)
        # Check for any overlap
        if self.prevent_overlaps:
            for tq in self.__class__.objects.filter(~dj_models.Q(id=self.id) & dj_models.Q(**{self.object_name: obj})):
                if tq.overlaps(self):
                    raise dj_exc.ValidationError(
                        f'property overlap between {self} and {tq} for object {getattr(self, self.object_name)}',
                        code='time_interval_overlap')

    class Meta:
        abstract = True


# Translations


class TranslatedObject(SourcedObject):
    """A object whose label can be translated in different languages."""
    unlocalized_name = dj_models.CharField(max_length=200)

    def get_label(self, language_code: str, default: str = None) -> str:
        """Returns the label for this object in the specific language.

        :param language_code: Code of the desired language.
        :param default: The value returned if no label was found for the given language code.
        :return: The label or the default value if no labels were found.
        """
        try:
            trans = self.label_translations.get(language_code=language_code)
        except Translation.DoesNotExist:
            return default if default is not None else f'{self.__class__.__name__}@{self.id}'
        else:
            return trans.label_text


class Translation(BaseObject):
    """A translation for a TranslatedObject."""
    object = dj_models.ForeignKey(TranslatedObject, dj_models.CASCADE, related_name='label_translations')
    label_text = dj_models.CharField(max_length=200, validators=[non_empty_text_validator])
    language_code = dj_models.CharField(max_length=20, validators=[lang_code_validator])

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if not exclude or 'label_text' not in exclude:
            self.label_text = self.label_text.strip()

    class Meta:
        unique_together = ('object', 'language_code')


############
# Geometry #
############


class Geometry(TemporalObject):
    """Base class for physical objects."""

    @property
    def perimeter(self) -> float:
        """The approximate perimeter of this geometry object in meters."""
        raise NotImplementedError('should be implemented by subclasses')

    @property
    def area(self) -> float:
        """The approximate area of this geometry object in meters squared."""
        raise NotImplementedError('should be implemented by subclasses')


class Node(Geometry):
    """A node corresponds to an small physical object (such as signals, poles, etc.) or to a line/polygon vertex."""
    latitude = dj_models.FloatField()
    longitude = dj_models.FloatField()
    altitude = dj_models.FloatField()

    @property
    def perimeter(self):
        """0, as a point has no perimeter."""
        return 0

    @property
    def area(self):
        """0, as a point has no area."""
        return 0

    @property
    def as_tuple(self) -> typ.Tuple[float, float, float]:
        return self.latitude, self.longitude, self.altitude

    class Meta:
        unique_together = ('latitude', 'longitude', 'altitude')


# noinspection PyAbstractClass
class GeometryWithNodes(Geometry):
    """Base class for polylines and polygons."""
    nodes = dj_models.ManyToManyField(Node, through='GeometryWithNodesNodeTable', related_name='geometries')

    @property
    def ordered_nodes(self) -> typ.List[Node]:
        """Returns all nodes for this object ordered by their index."""
        return list(self.nodes.order_by('geometries_table__index'))

    @staticmethod
    def _distance(nodes: typ.List[Node]) -> float:  # In meters
        """Computes the approximate total length in meters of the line formed by the given list of nodes.
        The computation is done using the WGS-84 ellipsoid model of Earth.
        To take altitude into account, it is assumed that distances between points is small
        enough Earth’s curvature is negligeable.
        """
        if len(nodes) < 2:
            return 0
        distance = 0
        for i in range(len(nodes) - 1):
            node1 = nodes[i].as_tuple
            node2 = nodes[i + 1].as_tuple
            surface_distance = geopy_dist.distance(node1[:2], node2[:2], ellipsoid='WGS-84').meters
            # Distances are supposed to be short enough that euclidian distance
            # for altitude should not degrade results too much
            distance += math.sqrt(surface_distance ** 2 + (node1[2] - node2[2]) ** 2)
        return distance


class GeometryWithNodesNodeTable(BaseObject):
    """This table associates geometry objects their nodes.
    Each object-node pair is associated to an index.
    Indexes must be unique for each geometry object.
    A node cannot be associated to a geometry object more than once.
    """
    geometry_object = dj_models.ForeignKey(GeometryWithNodes, dj_models.CASCADE, related_name='nodes_table')
    node = dj_models.ForeignKey(Node, dj_models.CASCADE, related_name='geometries_table')
    index = dj_models.IntegerField()

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if not exclude or 'index' not in exclude:
            indexes = []
            for item in GeometryWithNodesNodeTable.objects.filter(geometry_object=self.geometry_object):
                index = item.index
                if index in indexes:
                    raise dj_exc.ValidationError({
                        'index': f'duplicate node index {index} for geometry object {self.geometry_object}',
                    })
                indexes.append(index)

    class Meta:
        unique_together = ('geometry_object', 'node')


class Polyline(GeometryWithNodes):
    """An object that represents a line composed of a series of contiguous segments."""

    @property
    def perimeter(self):
        """The approximate total length in meters of this polyline.
        The computation is done using the WGS-84 ellipsoid model of Earth.
        To take altitude into account, it is assumed that distances between points is small
        enough Earth’s curvature is negligeable.
        """
        return self.length

    @property
    def area(self):
        """0, as a line has no area."""
        return 0

    @property
    def length(self) -> float:
        """Alias for "perimeter" property."""
        return self._distance(list(self.ordered_nodes))


class Polygon(GeometryWithNodes):
    """An object that represents a polygon with any number of verteces."""

    @property
    def perimeter(self):
        """The perimeter in meters of this polygon.
        The computation is done using the WGS-84 ellipsoid model of Earth.
        To take altitude into account, it is assumed that distances between points is small
        enough Earth’s curvature is negligeable.
        """
        holes_total_perimeter = sum(hole.perimeter for hole in self.holes)
        nodes = list(self.ordered_nodes)
        return self._distance(nodes + [nodes[0]]) + holes_total_perimeter

    @property
    def area(self):
        """The area of this polygon in meters squared.
        The computation is done using the WGS-84 ellipsoid model of Earth.
        Verteces altitudes are considered to be at sea level (0 m).
        """
        # Swap latitude and longitude, and remove altitude
        nodes = [n.as_tuple[1::-1] for n in self.ordered_nodes]
        if len(nodes) < 3:
            return 0
        holes_total_area = sum(hole.area for hole in self.holes)
        geom = sh_polygon.Polygon(nodes)
        area = sh_ops.transform(
            functools.partial(
                pyproj.transform,
                pyproj.Proj('WGS84'),
                pyproj.Proj(
                    proj='aea',
                    lat_1=geom.bounds[1],
                    lat_2=geom.bounds[3]
                )
            ),
            geom).area
        return area - holes_total_area


def polygon_hole_validator(value: Polygon):
    if isinstance(value, PolygonHole):
        raise dj_exc.ValidationError('a PolygonHole object cannot have another PolygonHole object as its parent')


class PolygonHole(Polygon):
    """An polygon object that represents a hole in another polygon. Holes cannot have holes."""
    parent_polygon = dj_models.ForeignKey(Polygon, dj_models.CASCADE, validators=[polygon_hole_validator],
                                          related_name='holes')


##########
# Tracks #
##########


class ElectrificationSystem(TranslatedObject):
    """An enumeration that represents the electrification system of a track section.
    Examples: none, side rail(s), overhead wire, floor, etc.
    """
    pass


class ElectricityType(TranslatedObject):
    """An enumeration that represents the type of electrical current used to power a track section.
    Examples: DC, single-phase, three-phase, etc.
    """
    pass


class TrackType(TranslatedObject):
    """An enumeration that represents the type of a track section.
    Examples: Main, high speed, spur, tramway, subway, etc.
    """
    pass


class TrackUsage(TranslatedObject):
    """An enumeration that represents the usage of a track section.
    Examples: Passenger service, goods service, project, heritage, in construction, abandonned, industrial, etc.
    """
    pass


class Unit(TranslatedObject):
    """A unit has a symbol and coefficient to convert into the reference unit."""
    symbol = dj_models.CharField(max_length=20)
    to_reference_coefficient = dj_models.FloatField(validators=[positive_value_validator])

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if not exclude or 'symbol' not in exclude:
            s = self.symbol.strip()
            if s == '':
                raise dj_exc.ValidationError({'symbol': 'empty symbol'})
            self.symbol = s

    def convert_value_to(self, value: float, unit: Unit) -> float:
        """Converts a value expressed in this unit into the given unit.

        :param value: The value to convert.
        :param unit: The target unit.
        :return: The converted value.
        :raises TypeError: If the unit’s class differs from this unit’s class.
        """
        if self.__class__ != unit.__class__:
            raise TypeError(f'expected unit of type "{self.__class__}", got "{unit.__class__}"')
        return value * self.to_reference_coefficient / unit.to_reference_coefficient

    class Meta:
        abstract = True


class LengthUnit(Unit):
    """A length unit with its symbol and coefficient to convert into meters."""

    @property
    def to_meters_coefficient(self) -> float:
        """Alias for "to_reference_coefficient"."""
        return self.to_reference_coefficient


class SpeedUnit(Unit):
    """A speed unit with its symbol and coefficient to convert into kilometers per hour."""

    @property
    def to_kph_coefficient(self) -> float:
        """Alias for "to_reference_coefficient"."""
        return self.to_reference_coefficient


class TrackSection(Polyline):
    """Base class for all track types.

    Track sections have a direction that is relative to the order of its nodes.

    A track section may belong to one or more track infrastructures.
    """
    # Relative to node order
    direction = dj_models.CharField(max_length=30,
                                    choices=(('normal', 'Normal'), ('reverse', 'Reverse'), ('both', 'Both')),
                                    default='both')
    track_infrastructures = dj_models.ManyToManyField('TrackInfrastructure', related_name='track_sections')


class TrackNumberState(TemporalProperty):
    """A property representing the number of a track section.
    Meant to be used primarily in stations.
    The absence of a state object for a given time interval is
    interpreted as the absence of number, not as unknown.
    """
    number = dj_models.CharField(max_length=10)
    track_section = dj_models.ForeignKey(TrackSection, dj_models.CASCADE, related_name='number_states')
    object_name = 'track_section'
    absent_means_none = True


class RoadCrossingState(TemporalProperty):
    """A property representing whether the associated track section is a road crossing or not.
    The absence of a state object for a given time interval is
    interpreted as the absence of crossing, not as unknown.
    """
    road_name = dj_models.CharField(validators=[non_empty_text_validator], max_length=100, null=True, blank=True)
    track_section = dj_models.ForeignKey(TrackSection, dj_models.CASCADE, related_name='road_crossing_states')
    object_name = 'track_section'
    absent_means_none = True


class ElectrificationState(TemporalProperty):
    """A property representing the electrification state (tension in Volts, current type, system) of a track section.
    If the property states that the section is not elecrified, the values of the other attributes
    (namely tension, system and current_type) should be ignored.
    """
    electrified = dj_models.BooleanField()
    tension = dj_models.IntegerField(validators=[positive_value_validator], null=True, blank=True)
    system = dj_models.ForeignKey(ElectrificationSystem, dj_models.SET_NULL, null=True, blank=True,
                                  related_name='electrification_states')
    current_type = dj_models.ForeignKey(ElectricityType, dj_models.SET_NULL, null=True, blank=True,
                                        related_name='electrification_states')
    track_section = dj_models.ForeignKey(TrackSection, dj_models.CASCADE, related_name='electrification_states')
    object_name = 'track_section'


class TrackTypeState(TemporalProperty):
    """A property representing the type of a track section.
    This property allows overlapping.
    """
    type = dj_models.ForeignKey(TrackType, dj_models.PROTECT, related_name='track_type_states')
    track_section = dj_models.ForeignKey(TrackSection, dj_models.CASCADE, related_name='type_states')
    object_name = 'track_section'
    prevent_overlaps = False


class TrackUsageState(TemporalProperty):
    """A property representing the usage of a track section.
    This property allows overlapping.
    """
    usage = dj_models.ForeignKey(TrackUsage, dj_models.PROTECT, related_name='track_usage_states')
    track_section = dj_models.ForeignKey(TrackSection, dj_models.CASCADE, related_name='usage_states')
    object_name = 'track_section'
    prevent_overlaps = False


class TrackMaxSpeedState(TemporalProperty):
    """A property representing the maximum speed of a track section."""
    max_speed = dj_models.FloatField()
    unit = dj_models.ForeignKey(SpeedUnit, dj_models.PROTECT, related_name='+')
    track_section = dj_models.ForeignKey(TrackSection, dj_models.CASCADE, related_name='max_speed_states')
    object_name = 'track_section'

    def convert_speed_to(self, unit: SpeedUnit) -> float:
        """Converts the speed into the given unit.

        :param unit: The target unit.
        :return: The converted speed.
        :raises TypeError: If the specified unit is not a speed unit.
        """
        return self.unit.convert_value_to(self.max_speed, unit)


class TractionSystem(TranslatedObject):
    """An enumeration that represents the traction system of a track section.
    Examples: None, rack and pinion, funicular, etc.
    """
    pass


class RailType(TranslatedObject):
    """An enumeration that represents a rail type.
    Examples: UIC 60, Vignole, wood, metal strips, etc.
    """
    pass


class TieType(TranslatedObject):
    """An enumeration that represents a type of track ties.
    Examples: Wood, concrete, bi-block, concrete slab, stones, sunken track, metal, etc.
    """
    pass


def gauge_validator(value: float):
    if value is not None and value < 380:
        raise dj_exc.ValidationError('track gauge should be greater than or equal to 380 mm', code='invalid_gauge')


class ConventionalTrackSection(TrackSection):
    """This class represents a section of conventional two-rail train track.

    A track section may have multiple gauges at once. Whenever at least one
    gauge is specified, the unit should not be null.

    Rails type, ties type and traction system are considered to be a part of a track section
    and are thus direct attributes and not temporal properties.

    It also features a property named "has_tyre_roll_ways" that indicates whether
    the track has special strips for tyred trains (e.g. Lyon subway). It defaults to False.
    """
    gauges = model_fields.CommaSeparatedFloatField(max_length=200, validators=[gauge_validator], null=True, blank=True)
    unit = dj_models.ForeignKey(LengthUnit, dj_models.PROTECT, null=True, blank=True,
                                related_name='+')  # No inverse relation
    tie_type = dj_models.ForeignKey(TieType, dj_models.SET_NULL, null=True, blank=True, related_name='track_sections')
    rail_type = dj_models.ForeignKey(RailType, dj_models.SET_NULL, null=True, blank=True, related_name='track_sections')
    traction_system = dj_models.ForeignKey(TractionSystem, dj_models.SET_NULL, null=True, blank=True,
                                           related_name='track_sections')
    has_tyre_roll_ways = dj_models.BooleanField(default=False)  # e.g. Lyon subway

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if (not exclude or 'unit' not in exclude) and self.gauges and self.unit is None:
            raise dj_exc.ValidationError({'unit': 'unit cannot be null if at least one gauge is defined'})

    def convert_gauges_to(self, unit_symbol: str) -> typ.Optional[typ.List[float]]:
        """Converts the gauges of this track section into the given unit.

        :param unit_symbol: The target unit’s symbol.
        :return: The converted gauges or None if the unit does not exist.
        """
        try:
            target_unit = LengthUnit.objects.get(symbol=unit_symbol)
        except LengthUnit.DoesNotExist:
            return None
        else:
            return [self.unit.convert_value_to(gauge, target_unit) for gauge in self.gauges]


class RailFerryRouteSection(ConventionalTrackSection):
    """A special case of two-rail track that represents a section of a rail-ferry route."""
    pass


class MonorailTrackType(TranslatedObject):
    """An enumeration that represents a type of monorail track.
    Examples: T-track (Jean Bertin), Ewing, Lartigue, Translohr, suspened, tyres with central rail, etc.
    """
    pass


class MonorailTrackSection(TrackSection):
    """This class represents a section of monorail track."""
    type = dj_models.ForeignKey(MonorailTrackType, dj_models.SET_NULL, null=True, blank=True,
                                related_name='track_sections')


class GLTTrackSection(TrackSection):  # TVR
    """This class represents a section of GLT (Guided Light Rail) track.
    The "guided" attributes indicates whether a section has a guide rail or not.
    """
    guided = dj_models.BooleanField()


class VALTracksection(TrackSection):
    """This class represents a section of VAL (Véhicule Automatique Léger, Automatic Light Vehicle) track"""
    pass


class MaglevTrackSection(TrackSection):
    """This class represents a section of Maglev track."""
    pass


#############
# Buildings #
#############


class BuildingMaterial(TranslatedObject):
    """An enumeration that represents the construction material of a building.
    Examples: Brick, concrete, stone, wood, etc.
    """
    pass


class BuildingType(TranslatedObject):
    """An enumeration that represents the type of a building.
    Examples: Engine shed, passenger hall, factory, guard house, water tower, etc.
    """
    pass


class BuildingUsage(TranslatedObject):
    """An enumeration that represents the usage of a building.
    Examples: In service, abandonned, house, museum, etc.
    """
    pass


class Building(Polygon):
    """This class represents a building."""
    walls_material = dj_models.ForeignKey(BuildingMaterial, dj_models.SET_NULL, null=True, blank=True,
                                          related_name='buildings')
    type = dj_models.ForeignKey(BuildingType, dj_models.SET_NULL, null=True, blank=True, related_name='buildings')


class BuildingHeightState(TemporalProperty):
    """A property representing the height of a building."""
    height = dj_models.FloatField(validators=[positive_value_validator])
    unit = dj_models.ForeignKey(LengthUnit, dj_models.PROTECT)
    building = dj_models.ForeignKey(Building, dj_models.CASCADE, related_name='height_states')
    object_name = 'building'

    def convert_height_to(self, unit: LengthUnit) -> float:
        """Converts the height into the given unit.

        :param unit: The target unit.
        :return: The converted height.
        :raises TypeError: If the specified unit is not a length unit.
        """
        return self.unit.convert_value_to(self.height, unit)


class BuildingFloorsState(TemporalProperty):
    """A property representing the number of floors (above and underground) in a building."""
    floors = dj_models.IntegerField(validators=[positive_value_validator])
    underground_floors = dj_models.IntegerField(validators=[positive_value_validator])
    building = dj_models.ForeignKey(Building, dj_models.CASCADE, related_name='floors_states')
    object_name = 'building'


class BuildingUsageState(TemporalProperty):
    """A property representing the usage of a building."""
    usage = dj_models.ForeignKey(BuildingUsage, dj_models.PROTECT, related_name='usage_states')
    building = dj_models.ForeignKey(Building, dj_models.CASCADE, related_name='usage_states')
    object_name = 'building'


#########
# Walls #
#########


class WallMaterial(TranslatedObject):
    """An enumeration that represents the material of a wall or fence.
    Examples: Brick, stone, wooden fence, chain-link fence, etc.
    """
    pass


class WallSection(Polyline):
    """This class represents a section of wall or fence."""
    material = dj_models.ForeignKey(WallMaterial, dj_models.SET_NULL, null=True, blank=True,
                                    related_name='wall_sections')


class GateMaterial(TranslatedObject):
    """An enumeration that represents the material of a gate.
    Examples: Chain, wood, chain-links, metal, etc.
    """
    pass


class Gate(Polyline):
    """This class represents a gate."""
    material = dj_models.ForeignKey(GateMaterial, dj_models.SET_NULL, null=True, blank=True,
                                    related_name='gates')


####################
# Track structures #
####################


class TrackInfrastructureUsage(TranslatedObject):
    """An enumeration that represents the usage of a track infrastructure.
    Examples: Railroad, road, path, none, etc.
    """
    pass


class TrackInfrastructure(Polygon):
    """This class represents a track infrastructure, i.e. a construction that supports tracks."""
    pass


class TrackInfrastructureUsageState(TemporalProperty):
    """A property representing the usage of a track infrastructure.
    This property allows overlapping.
    """
    usage = dj_models.ForeignKey(TrackInfrastructureUsage, dj_models.PROTECT, related_name='usage_states')
    track_infrastructure = dj_models.ForeignKey(TrackInfrastructure, dj_models.CASCADE, related_name='usage_states')
    object_name = 'track_infrastructure'
    prevent_overlaps = False


# Bridges


class BridgePier(Polygon):
    """This class represents a bridge pier or column."""
    infrastructures = dj_models.ManyToManyField('Infrastructure', related_name='bridge_piers')
    material = dj_models.ForeignKey(BuildingMaterial, dj_models.SET_NULL, null=True, blank=True,
                                    related_name='bridge_piers')


class BridgeAbutment(Polygon):
    """This class represents a bridge abutment."""
    infrastructures = dj_models.ManyToManyField('Infrastructure', related_name='bridge_abutments')
    material = dj_models.ForeignKey(BuildingMaterial, dj_models.SET_NULL, null=True, blank=True,
                                    related_name='bridge_abutments')


class BridgeSectionType(TranslatedObject):
    """An enumeration that represents a type of bridge section.
    Examples: Static, swing, bascule, etc.
    """
    pass


class BridgeSectionStructure(TranslatedObject):
    """An enumeration that represents the structure of a bridge section.
    Examples: Cantilever, arch, bow-string, tressle, piers, suspended, etc.
    """
    pass


class BridgeSection(TrackInfrastructure):
    """This class represents a section of bridge."""
    infrastructures = dj_models.ManyToManyField('Infrastructure', related_name='bridge_sections')
    material = dj_models.ForeignKey(BuildingMaterial, dj_models.SET_NULL, null=True, blank=True,
                                    related_name='bridge_sections')
    type = dj_models.ForeignKey(BridgeSectionType, dj_models.SET_NULL, null=True, blank=True,
                                related_name='bridge_sections')
    structure = dj_models.ForeignKey(BridgeSectionStructure, dj_models.SET_NULL, null=True, blank=True,
                                     related_name='bridge_sections')


# Tunnels


class TunnelSectionMaterial(TranslatedObject):
    """An enumeration that represents the material of the inside of a tunnel.
    Examples: None (bare rock), bricks, concrete, etc.
    """
    pass


class TunnelSection(TrackInfrastructure):
    """This class represents a tunnel section."""
    infrastructures = dj_models.ManyToManyField('Infrastructure', related_name='tunnel_sections')


class TunnelSectionMaterialState(TemporalProperty):
    """A property representing the material of a tunnel section."""
    material = dj_models.ForeignKey(TunnelSectionMaterial, dj_models.PROTECT, related_name='material_states')
    tunnel_section = dj_models.ForeignKey(TunnelSection, dj_models.CASCADE, related_name='material_states')
    object_name = 'tunnel_section'


# Track covers


class TrackCoverSection(TrackInfrastructure):
    """This class represents a section of track cover (for snow or rocks)."""
    material = dj_models.ForeignKey(BuildingMaterial, dj_models.SET_NULL, null=True, blank=True,
                                    related_name='track_cover_sections')


# Maneuver


class ManeuverStructure(TrackInfrastructure):
    """This class represents a structure used to maneuver trains."""
    pass


class ManeuverStructureState(TemporalProperty):
    """A property representing the state of a maneuver structure.

    The "moving_structure_present" attribute indicates whether the moving part of the structure
    (i.e. bridge, plate, etc.) is still present or not.

    If "moving_structure_present" is False, "tracks_number" should be 0.
    """
    moving_structure_present = dj_models.BooleanField()
    tracks_number = dj_models.IntegerField(validators=[inf_validator_generator(1)])
    structure = dj_models.ForeignKey(ManeuverStructure, dj_models.CASCADE, related_name='states')
    object_name = 'structure'

    def clean(self):
        super().clean()
        if not self.moving_structure_present and self.tracks_number != 0:
            raise dj_exc.ValidationError('tracks number is not 0 but structure marked as not present',
                                         code='invalid_track_number')


def angle_validator(value: float):
    if not (0 <= value <= 360):
        raise dj_exc.ValidationError(f'angle value should be in [0, 360] degrees, got {value}', code='invalid_angle')


class Turntable(ManeuverStructure):
    """This class represents a turntable.

    The "is_bridge" attribute indicates whether the turntable features a bridge or a plate.
    """
    is_bridge = dj_models.BooleanField()
    max_rotation_angle = dj_models.FloatField(validators=[angle_validator], default=360)  # In degrees


class TransferTable(ManeuverStructure):
    """This class represents a transfer table.

    The "has_pit" attribute indicates whether this structure has a bridge over a pit
    or the moving section rolls over the tracks.
    """
    has_pit = dj_models.BooleanField()


# Earth-work


class EarthworkType(TranslatedObject):
    """An enumeration that represents a type of earthwork.
    Examples: Cutting, embankment, etc.
    """
    pass


class Earthwork(TrackInfrastructure):
    """This class represents an earthwork, i.e. a structure made of soil and/or rock to lay tracks on."""
    type = dj_models.ForeignKey(EarthworkType, dj_models.PROTECT, related_name='earthworks')


# Platforms


class SurfaceMaterial(TranslatedObject):
    """An enumeration that represents the material of a surface.
    Examples: Concrete, gravel, dirt, stone, planks, etc.
    """
    pass


class Surface(Polygon):
    """This class represents a surface, e.g. a platform, dock, etc."""
    pass


class SurfaceMaterialState(TemporalProperty):
    """A property representing the material of a surface."""
    material = dj_models.ForeignKey(SurfaceMaterial, dj_models.PROTECT, related_name='surface_material_states')
    surface = dj_models.ForeignKey(Surface, dj_models.CASCADE, related_name='material_states')
    object_name = 'surface'


class Platform(Surface):
    """This class represents a platform."""
    pass


class Dock(Surface):
    """This class represents a dock’s floor."""
    pass


#####################
# Abstract entities #
#####################


class OperatorType(TranslatedObject):
    """An enumeration that represents the type of an operator.
    Examples: Private/public company, association, individual, etc.
    """
    pass


class Operator(TranslatedObject, TemporalObject):
    """This class represents an operator, i.e. an entity that operates train lines, factories, etc."""
    pass


class OperatorTypeState(TemporalProperty):
    """A property representing the type of a an operator."""
    type = dj_models.ForeignKey(OperatorType, dj_models.PROTECT, related_name='type_states')
    operator = dj_models.ForeignKey(Operator, dj_models.CASCADE, related_name='type_states')
    object_name = 'operator'


class OperatedEntity(TranslatedObject, TemporalObject):
    """This class represents an entity that is operated by one or more operators."""
    opened_by = dj_models.ForeignKey(Operator, dj_models.SET_NULL, null=True, blank=True,
                                     related_name='opened_entities')
    operators = dj_models.ManyToManyField(Operator, through='OperatedEntityOperatorTable',
                                          related_name='operated_entities')


class OperatedEntityOperatorTable(TemporalObject):
    """This table associates operator objects to the entities they operate.
    Each operator-entity pair is associated to a time interval during which the operator operates the entity.
    An entity cannot be associated to an operator object more than once per time interval.
    """
    operator = dj_models.ForeignKey(Operator, dj_models.CASCADE, related_name='entities_table')
    entity = dj_models.ForeignKey(OperatedEntity, dj_models.CASCADE, related_name='operators_table')

    class Meta:
        unique_together = ('time_span', 'operator', 'entity')


class SiteType(TranslatedObject):
    """An enumeration that represents the type of a site.
    Examples: Station, factory, mine, military installation, depot, etc.
    """
    pass


class Site(OperatedEntity):
    """This class represents a site."""
    objects = dj_models.ManyToManyField(Geometry, through='SiteObjectTable', related_name='sites')
    type = dj_models.ForeignKey(SiteType, dj_models.SET_NULL, null=True, blank=True, related_name='sites')


class SiteObjectTable(TemporalObject):
    """This table associates site objects the geometries that are part of it.
    Each site-geometry pair is associated to a time interval during which the geometry is part of the site.
    A geometry cannot be associated to a site object more than once per time interval.
    """
    site = dj_models.ForeignKey(Site, dj_models.CASCADE, related_name='objects_table')
    object = dj_models.ForeignKey(Geometry, dj_models.CASCADE, related_name='sites_table')

    class Meta:
        unique_together = ('time_span', 'site', 'object')


class TrainLine(OperatedEntity):
    """This class represents a train line."""
    track_sections = dj_models.ManyToManyField(TrackSection, related_name='train_lines')
    sites = dj_models.ManyToManyField(Site, related_name='train_lines')


class Infrastructure(TranslatedObject, TemporalObject):
    """This class represents an infrastructure. This can be a bridge or a tunnel."""
    pass


class Area(Polygon):  # TODO keep?
    pass
