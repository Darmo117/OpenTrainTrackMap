// Heavily inspired from work of @davidgilbertson on Github and `leaflet-geoman` project.
import {Map, MapMouseEvent} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import {
  Feature,
  FeatureCollection,
  featureCollection,
  Geometries,
  LineString,
  lineString as turfLineString,
  MultiLineString,
  MultiPolygon,
  point as turfPoint,
  Polygon,
  Position,
} from "@turf/helpers";
import bboxPolygon from "@turf/bbox-polygon";
import booleanDisjoint from "@turf/boolean-disjoint";
import {getCoords} from "@turf/invariant";
import distance from "@turf/distance";
import polygonToLine from "@turf/polygon-to-line";
import nearestPointOnLine, {NearestPointOnLine} from "@turf/nearest-point-on-line";
import nearestPointInPointSet from "@turf/nearest-point";
import midpoint from "@turf/midpoint";
import {GeoJSON} from "geojson";

import {SnapOptions, State} from "../state";

const {geojsonTypes} = MapboxDraw.constants;

export enum GuideId {
  VERTICAL = "VERTICAL_GUIDE",
  HORIZONTAL = "HORIZONTAL_GUIDE",
}

export type LngLatDict = {
  lng: number;
  lat: number;
};

/**
 * Add the given point to the given list of points only if the point is visible in the map’s current viewport.
 * @param map A map.
 * @param listToUpdate The list of points to update.
 * @param point The point to add to the list.
 * @param forceInclusion If true, the point will be added regardless of its visibility.
 */
export function addPointToList(
  map: Map,
  listToUpdate: Position[],
  point: Position,
  forceInclusion: boolean = false
) {
  if (forceInclusion) {
    listToUpdate.push(point);
    return;
  }

  const {width: w, height: h} = map.getCanvas();
  const {x, y} = map.project(point as [number, number]);
  const pointIsOnTheScreen = x > 0 && x < w && y > 0 && y < h;

  if (pointIsOnTheScreen) {
    listToUpdate.push(point);
  }
}

/**
 * Create the list of snappable features for the given feature.
 * The list will only contain features that are visible in the map’s current bounding box.
 * @param map The map.
 * @param drawApi The MapboxDraw drawing API.
 * @param currentFeature The feature to get the list for.
 * @returns The list of snappable features and the list of snappable vertices.
 */
export function createSnapList(
  map: Map,
  drawApi: any,
  currentFeature: Feature<Geometries>
): [Feature<Geometries>[], Position[]] {
  // Get all drawn features
  const features: Feature<Geometries>[] = drawApi.getAll().features;
  const bboxAsPolygon = getCurrentMapBbox(map);

  const snapList: Feature<Geometries>[] = [];
  const vertices: Position[] = [];

  function extractVertices(
    coordinates: Position | Position[] | Position[][] | Position[][][],
    isCurrentFeature: boolean = false
  ) {
    if (!Array.isArray(coordinates)) {
      throw Error("Your array is not an array");
    }

    if (Array.isArray(coordinates[0])) {
      // coordinates is an array of arrays, we must go deeper
      coordinates.forEach(coord => {
        extractVertices(coord as Position | Position[] | Position[][]);
      });
    } else if (coordinates.length === 2) {
      // Force-add off-screen points for the current feature
      // so that features always snap to their own points
      addPointToList(map, vertices, coordinates as Position, isCurrentFeature);
    }
  }

  // Extract vertices for drawing guides
  features.forEach(feature => {
    if (feature.id === currentFeature.id) {
      if (currentFeature.type as string === geojsonTypes.POLYGON) {
        // For the current polygon, the last two points are the mouse position and back home
        // so we chop those off (else we get vertices showing where the user clicked, even
        // if they were just panning the map)
        extractVertices(
          (feature.geometry.coordinates[0] as Position[]).slice(0, -2),
          true
        );
      }
      return;
    }

    // If this is re-running because a user is moving the map, the features might include
    // vertices or the last leg of a polygon
    if (feature.id === GuideId.HORIZONTAL || feature.id === GuideId.VERTICAL) {
      return;
    }

    extractVertices(feature.geometry.coordinates);

    // If feature is currently on viewport add to snap list
    if (!booleanDisjoint(bboxAsPolygon, feature)) {
      snapList.push(feature);
    }
  });

  return [snapList, vertices];
}

/**
 * Return a snap points for the given mouse event.
 * If there aren’t any available or the control key is held, the event’s lng/lat is returned.
 * Also, defines if vertices should show on the state object
 *
 * Mutates the state object.
 * @param state The current state.
 * @param e The mouse event.
 * @returns The snap coordinates.
 */
export function snap(state: State, e: MapMouseEvent): LngLatDict | null {
  let latLng: LngLatDict = e.lngLat;

  if (e.originalEvent.ctrlKey) {
    state.showVerticalSnapLine = false;
    state.showHorizontalSnapLine = false;
    return latLng;
  }
  if (state.snapList.length == 0) {
    return latLng;
  }

  if (state.options.snap) {
    const closestLayer = getClosestLayer(latLng, state.snapList);
    // If no layers found. Can happen when circle is the only visible layer on the map
    // and the hidden snapping-border circle layer is also on the map.
    if (!closestLayer) {
      return null;
    }

    let snapLatLng: LngLatDict;
    if (!closestLayer.isMarker) {
      snapLatLng = checkPrioritiySnapping(
        closestLayer,
        state.options.snapOptions,
        state.options.snapOptions?.snapVertexPriorityDistance
      );
    } else {
      snapLatLng = closestLayer.latlng;
    }

    let verticalPx, horizontalPx;
    if (state.options.guides) {
      const nearestGuideline = getNearestGuideline(state.vertices, e.lngLat);
      verticalPx = nearestGuideline.verticalPx;
      horizontalPx = nearestGuideline.horizontalPx;

      state.showVerticalSnapLine = verticalPx !== undefined;
      if (state.showVerticalSnapLine) {
        // Draw a line from top to bottom
        state.verticalGuide.updateCoordinate("0", verticalPx, e.lngLat.lat + 10);
        state.verticalGuide.updateCoordinate("1", verticalPx, e.lngLat.lat - 10);
      }

      state.showHorizontalSnapLine = horizontalPx !== undefined;
      if (state.showHorizontalSnapLine) {
        // Draw a line from left to right
        state.horizontalGuide.updateCoordinate("0", e.lngLat.lng + 10, horizontalPx);
        state.horizontalGuide.updateCoordinate("1", e.lngLat.lng - 10, horizontalPx);
      }
    }

    const minDistance =
      (state.options.snapOptions?.snapPx ?? 15) *
      getMetersPerPixel(snapLatLng.lat, state.map.getZoom());
    if (closestLayer.distance * 1000 < minDistance) {
      return snapLatLng;
    } else if (verticalPx || horizontalPx) {
      // Snap to guide line(s)
      return {
        lng: verticalPx ?? e.lngLat.lng,
        lat: horizontalPx ?? e.lngLat.lat
      };
    }
  }

  return latLng;
}

/**
 * Return the guide feature for the given guide ID.
 * @param id The guide’s ID.
 * @returns The feature.
 */
export function getGuideFeature(id: GuideId): GeoJSON {
  return {
    id,
    type: geojsonTypes.FEATURE,
    properties: {
      isSnapGuide: "true", // for styling
    },
    geometry: {
      type: geojsonTypes.LINE_STRING,
      coordinates: [] as Position[],
    },
  };
}

/**
 * Check whether the guide lines should be hidden for the given object.
 * @param state The current state.
 * @param geojson A GeoJSON object.
 * @return True if the guide lines should be hidden, false otherwise.
 */
export function shouldHideGuide(state: State, geojson: Feature<Geometries>): boolean {
  return geojson.properties.id === GuideId.VERTICAL && (!state.options.guides || !state.showVerticalSnapLine)
    || geojson.properties.id === GuideId.HORIZONTAL && (!state.options.guides || !state.showHorizontalSnapLine);
}

/**
 * Return the given map’s current viewport as a polygon feature.
 * @param map A map.
 * @returns A polygon feature.
 */
function getCurrentMapBbox(map: Map): Feature<Polygon> {
  const canvas = map.getCanvas();
  const w = canvas.width;
  const h = canvas.height;
  // const cUL = map.unproject([0, 0]).toArray();
  const cUR = map.unproject([w, 0]).toArray();
  // const cLR = map.unproject([w, h]).toArray();
  const cLL = map.unproject([0, h]).toArray();
  return bboxPolygon([cLL, cUR].flat() as [number, number, number, number]);
}

type GuidePosition = {
  verticalPx: number | undefined;
  horizontalPx: number | undefined;
};

/**
 * Get the guide line that is the nearest to the given coordinates.
 * Guide line coordinates are fetched in the given list of vertices.
 * @param vertices List of vertex positions to fetch guide lines in.
 * @param coords The reference coordinates.
 * @returns The vertical and horizontal pixel coordinates of the nearest guide line.
 */
function getNearestGuideline(vertices: Position[], coords: LngLatDict): GuidePosition {
  const verticals: number[] = [];
  const horizontals: number[] = [];

  vertices.forEach(vertex => {
    verticals.push(vertex[0]);
    horizontals.push(vertex[1]);
  });

  const nearbyVerticalGuide = verticals.find(
    px => Math.abs(px - coords.lng) < 0.009
  );
  const nearbyHorizontalGuide = horizontals.find(
    py => Math.abs(py - coords.lat) < 0.009
  );

  return {
    verticalPx: nearbyVerticalGuide,
    horizontalPx: nearbyHorizontalGuide,
  };
}

type LayerDistance = {
  latlng: LngLatDict;
  segment?: [Position, Position];
  distance: number;
  isMarker: boolean;
};

/**
 * Calculate the distance between the given coordinates and feature.
 * @param lngLat The coordinates of the point.
 * @param layer The layer to get the distance to.
 */
function getDistanceToLayer(lngLat: LngLatDict, layer: Feature<Geometries>): LayerDistance {
  const point: Position = [lngLat.lng, lngLat.lat];
  const layerLatLngs = getCoords(layer);

  const isMarker = layer.geometry.type === "Point";
  const isPolygon = layer.geometry.type === "Polygon";
  const isMultiPolygon = layer.geometry.type === "MultiPolygon";
  const isMultiPoint = layer.geometry.type === "MultiPoint";

  if (isMarker) {
    const [lng, lat] = layerLatLngs;
    return {
      latlng: {lng, lat},
      distance: distance(layerLatLngs, point),
      isMarker: true,
    };
  }

  if (isMultiPoint) {
    const np = nearestPointInPointSet(
      point,
      featureCollection(layerLatLngs.map(x => turfPoint(x)))
    );
    const c = np.geometry.coordinates;
    return {
      latlng: {lng: c[0], lat: c[1]},
      distance: np.properties.distanceToPoint,
      isMarker: true,
    };
  }

  let lines: Feature<LineString | MultiLineString> | FeatureCollection<LineString | MultiLineString>;

  if (isPolygon || isMultiPolygon) {
    lines = polygonToLine(layer as Feature<Polygon | MultiPolygon>);
  } else {
    lines = layer as Feature<LineString | MultiLineString>;
  }

  let linesString: Feature<LineString>;
  let nearestPoint;
  // Extract all lines from the (multi-)polygon
  if (isPolygon) {
    let lineStrings;
    if ((lines as Feature<LineString | MultiLineString>).geometry.type === "LineString") {
      lineStrings = [turfLineString((lines as Feature<LineString>).geometry.coordinates)];
    } else {
      lineStrings = (lines as Feature<MultiLineString>).geometry.coordinates.map((coords) =>
        turfLineString(coords)
      );
    }

    const closestFeature = getFeatureWithNearestPoint(lineStrings, point);
    linesString = closestFeature.feature;
    nearestPoint = closestFeature.point;
  } else if (isMultiPolygon) {
    const lineStrings = (lines as FeatureCollection<LineString | MultiLineString>).features
      .map(feature => {
        if (feature.geometry.type === "LineString") {
          return [feature.geometry.coordinates];
        } else {
          return feature.geometry.coordinates;
        }
      })
      .flatMap(coords => coords)
      .map(coords => turfLineString(coords));

    const closestFeature = getFeatureWithNearestPoint(lineStrings, point);
    linesString = closestFeature.feature;
    nearestPoint = closestFeature.point;
  } else {
    linesString = lines as Feature<LineString>;
    nearestPoint = nearestPointOnLine(linesString, point);
  }

  const [lng, lat] = nearestPoint.geometry.coordinates;

  let segmentIndex = nearestPoint.properties.index;
  if (segmentIndex + 1 === linesString.geometry.coordinates.length) {
    segmentIndex--;
  }

  return {
    latlng: {lng, lat},
    segment: linesString.geometry.coordinates.slice(segmentIndex, segmentIndex + 2) as [Position, Position],
    distance: nearestPoint.properties.dist,
    isMarker: false,
  };
}

type FeatureWithNearestPoint = {
  feature: Feature<LineString>;
  point: NearestPointOnLine;
};

/**
 * Get the feature that is the closest to the given point.
 * @param lineStrings List of line features.
 * @param p A point.
 * @returns The closest feature with the point closest to the given one.
 */
function getFeatureWithNearestPoint(lineStrings: Feature<LineString>[], p: Position): FeatureWithNearestPoint {
  const nearestPointsOfEachFeature: FeatureWithNearestPoint[] = lineStrings.map(feature => ({
    feature: feature,
    point: nearestPointOnLine(feature, p),
  }));
  nearestPointsOfEachFeature.sort(
    (a, b) => a.point.properties.dist - b.point.properties.dist
  );
  return nearestPointsOfEachFeature[0];
}

/**
 * Get the feature that is the closest to the given point.
 * @param lngLat A point.
 * @param layers A list of layers.
 * @returns The closest layer with its distance to the given point or undefined if none were found.
 */
function getClosestLayer(
  lngLat: LngLatDict,
  layers: Feature<Geometries>[]
): LayerDistance | undefined {
  let closestLayer: LayerDistance;
  layers.forEach(layer => {
    // Find the closest latlng, segment and the distance of this layer to the dragged marker latlng
    const result = getDistanceToLayer(lngLat, layer);
    if (!closestLayer || result.distance < closestLayer.distance) {
      closestLayer = result;
    }
  });
  return closestLayer;
}

// minimal distance before marker snaps (in pixels)
function getMetersPerPixel(latitude: number, zoomLevel: number): number {
  const earthCircumference = 40075017;
  const latitudeRadians = latitude * (Math.PI / 180);
  return (
    (earthCircumference * Math.cos(latitudeRadians)) /
    Math.pow(2, zoomLevel + 8)
  );
}

/**
 * Return the snap position for the given layer and distance.
 * @param closestLayer The layer with its distance to the vertex to snap.
 * @param snapOptions The snap options.
 * @param snapVertexPriorityDistance The distance that needs to be undercut to trigger priority.
 * @returns The snap position.
 */
function snapToLineOrPolygon(
  closestLayer: LayerDistance,
  snapOptions: SnapOptions | undefined,
  snapVertexPriorityDistance: number
): LngLatDict {
  // A and B are the points of the closest segment to P (the marker position we want to snap).
  const [A, B] = closestLayer.segment;
  // C is the point we would snap to on the segment.
  // The closest point on the closest segment of the closest polygon to P. That's right.
  const C = [closestLayer.latlng.lng, closestLayer.latlng.lat];

  // Distances from A to C and B to C to check which one is closer to C
  const distanceAC = distance(A, C);
  const distanceBC = distance(B, C);

  // Closest latlng of A and B to C
  let closestVertexLatLng = distanceAC < distanceBC ? A : B;
  // Distance between closestVertexLatLng and C
  let shortestDistance = distanceAC < distanceBC ? distanceAC : distanceBC;

  // Snap to middle (M) of segment if option is enabled
  if (snapOptions?.snapToMidPoints) {
    const M = midpoint(A, B).geometry.coordinates;
    const distanceMC = distance(M, C);

    if (distanceMC < distanceAC && distanceMC < distanceBC) {
      // M is the nearest vertex
      closestVertexLatLng = M;
      shortestDistance = distanceMC;
    }
  }

  // If C is closer to the closestVertexLatLng (A, B or M) than the snapDistance,
  // the closestVertexLatLng has priority over C as the snapping point.
  const [lng, lat] = shortestDistance < snapVertexPriorityDistance ? closestVertexLatLng : C;
  // Return the copy of snapping point
  return {lng, lat};
}

/**
 * Check whether the snap position is on a vertex or a segment.
 * @param closestLayer A layer.
 * @param snapOptions The snap options.
 * @param snapVertexPriorityDistance The distance that needs to be undercut to trigger priority.
 */
function checkPrioritiySnapping(
  closestLayer: LayerDistance,
  snapOptions: SnapOptions | undefined,
  snapVertexPriorityDistance: number = 1.25
): LngLatDict {
  return !closestLayer.segment ? closestLayer.latlng : snapToLineOrPolygon(
    closestLayer,
    snapOptions,
    snapVertexPriorityDistance
  );
}
