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
import {SnapOptions, State} from "../state";

const {geojsonTypes} = MapboxDraw.constants;

export const IDS = {
  VERTICAL_GUIDE: "VERTICAL_GUIDE",
  HORIZONTAL_GUIDE: "HORIZONTAL_GUIDE",
};

export type LngLatDict = {
  lng: number,
  lat: number,
};

export function addPointTovertices(
  map: Map,
  vertices: Position[],
  coordinates: Position,
  forceInclusion: boolean = false
) {
  const {width: w, height: h} = map.getCanvas();
  // Just add vertices of features currently visible in viewport
  const {x, y} = map.project(coordinates as [number, number]);
  const pointIsOnTheScreen = x > 0 && x < w && y > 0 && y < h;

  // But do add off-screen points if forced (e.g. for the current feature)
  // So features will always snap to their own points
  if (pointIsOnTheScreen || forceInclusion) {
    vertices.push(coordinates);
  }
}

function getCurrentMapBbox(map: Map) {
  const canvas = map.getCanvas();
  const w = canvas.width;
  const h = canvas.height;
  // const cUL = map.unproject([0, 0]).toArray();
  const cUR = map.unproject([w, 0]).toArray();
  // const cLR = map.unproject([w, h]).toArray();
  const cLL = map.unproject([0, h]).toArray();
  return bboxPolygon([cLL, cUR].flat() as [number, number, number, number]);
}

/**
 * Create the list of snappable features for the given feature.
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
  const snapList: Feature<Geometries>[] = [];
  const bboxAsPolygon = getCurrentMapBbox(map);

  const vertices: Position[] = [];

  // Extract vertices for drawing guides
  function extractVertices(
    coordinates: Position | Position[] | Position[][] | Position[][][],
    isCurrentFeature: boolean = false
  ) {
    if (!Array.isArray(coordinates)) {
      throw Error("Your array is not an array");
    }

    if (Array.isArray(coordinates[0])) {
      // coordinates is an array of arrays, we must go deeper
      coordinates.forEach((coord) => {
        extractVertices(coord as Position | Position[] | Position[][]);
      });
    } else {
      // If not an array of arrays, only consider arrays with two items
      if (coordinates.length === 2) {
        addPointTovertices(map, vertices, coordinates as Position, isCurrentFeature);
      }
    }
  }

  features.forEach(feature => {
    if (feature.id === currentFeature.id) {
      if ((currentFeature.type as string) === geojsonTypes.POLYGON) {
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
    if (feature.id === IDS.HORIZONTAL_GUIDE || feature.id === IDS.VERTICAL_GUIDE) {
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
 * Get the guide line that is the nearest to the given coordinates.
 * Guide line coordinates are fetched in the given list of vertices.
 * @param vertices List of vertex positions to fetch guide lines in.
 * @param coords The reference coordinates.
 * @returns The vertical and horizontal pixel coordinates of the nearest guide line.
 */
function getNearestGuideline(vertices: Position[], coords: LngLatDict): { verticalPx: number, horizontalPx: number } {
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
  latlng: LngLatDict,
  segment?: Position[],
  distance: number,
  isMarker: boolean,
};

/**
 * Calculate the distance between the given coordinates and feature.
 * @param lngLat The coordinates of the point.
 * @param layer The layer to get the distance to.
 */
function calculateLayerDistance(lngLat: LngLatDict, layer: Feature<Geometries>): LayerDistance {
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
    segment: linesString.geometry.coordinates.slice(segmentIndex, segmentIndex + 2),
    distance: nearestPoint.properties.dist,
    isMarker: false,
  };
}

type FeatureWithNearestPoint = {
  feature: Feature<LineString>,
  point: NearestPointOnLine,
};

function getFeatureWithNearestPoint(lineStrings: Feature<LineString>[], p: Position): FeatureWithNearestPoint {
  const nearestPointsOfEachFeature = lineStrings.map(feature => ({
    feature: feature,
    point: nearestPointOnLine(feature, p),
  }));

  nearestPointsOfEachFeature.sort(
    (a, b) => a.point.properties.dist - b.point.properties.dist
  );

  return {
    feature: nearestPointsOfEachFeature[0].feature,
    point: nearestPointsOfEachFeature[0].point,
  };
}

function calculateClosestLayer(
  lngLat: LngLatDict,
  layers: Feature<Geometries>[]
): LayerDistance | undefined {
  let closestLayer: LayerDistance;
  layers.forEach(layer => {
    // find the closest latlng, segment and the distance of this layer to the dragged marker latlng
    const result = calculateLayerDistance(lngLat, layer);
    if (closestLayer?.distance === undefined || result.distance < closestLayer.distance) {
      closestLayer = result;
    }
  });
  return closestLayer;
}

// minimal distance before marker snaps (in pixels)
const metersPerPixel = function (latitude: number, zoomLevel: number): number {
  const earthCircumference = 40075017;
  const latitudeRadians = latitude * (Math.PI / 180);
  return (
    (earthCircumference * Math.cos(latitudeRadians)) /
    Math.pow(2, zoomLevel + 8)
  );
};

// we got the point we want to snap to (C), but we need to check if a coord of the polygon
function snapToLineOrPolygon(
  closestLayer: LayerDistance,
  snapOptions: SnapOptions,
  snapVertexPriorityDistance: number
): LngLatDict {
  // A and B are the points of the closest segment to P (the marker position we want to snap)
  const A = closestLayer.segment[0];
  const B = closestLayer.segment[1];

  // C is the point we would snap to on the segment.
  // The closest point on the closest segment of the closest polygon to P. That's right.
  const C = [closestLayer.latlng.lng, closestLayer.latlng.lat];

  // distances from A to C and B to C to check which one is closer to C
  const distanceAC = distance(A, C);
  const distanceBC = distance(B, C);

  // closest latlng of A and B to C
  let closestVertexLatLng = distanceAC < distanceBC ? A : B;

  // distance between closestVertexLatLng and C
  let shortestDistance = distanceAC < distanceBC ? distanceAC : distanceBC;

  // snap to middle (M) of segment if option is enabled
  if (snapOptions?.snapToMidPoints) {
    const M = midpoint(A, B).geometry.coordinates;
    const distanceMC = distance(M, C);

    if (distanceMC < distanceAC && distanceMC < distanceBC) {
      // M is the nearest vertex
      closestVertexLatLng = M;
      shortestDistance = distanceMC;
    }
  }

  // the distance that needs to be undercut to trigger priority
  const priorityDistance = snapVertexPriorityDistance;

  // the latlng we ultemately want to snap to
  let snapLatlng;

  // if C is closer to the closestVertexLatLng (A, B or M) than the snapDistance,
  // the closestVertexLatLng has priority over C as the snapping point.
  if (shortestDistance < priorityDistance) {
    snapLatlng = closestVertexLatLng;
  } else {
    snapLatlng = C;
  }

  // return the copy of snapping point
  const [lng, lat] = snapLatlng;
  return {lng, lat};
}

function snapToPoint(closestLayer: LayerDistance) {
  return closestLayer.latlng;
}

const checkPrioritiySnapping = (
  closestLayer: LayerDistance,
  snapOptions: SnapOptions,
  snapVertexPriorityDistance: number = 1.25
): LngLatDict => {
  let snappingToPoint = !Array.isArray(closestLayer.segment);
  if (snappingToPoint) {
    return snapToPoint(closestLayer);
  } else {
    return snapToLineOrPolygon(
      closestLayer,
      snapOptions,
      snapVertexPriorityDistance
    );
  }
};

/**
 * Returns snap points if there are any, otherwise the original lng/lat of the event
 * Also, defines if vertices should show on the state object
 *
 * Mutates the state object
 */
export const snap = (state: State, e: MapMouseEvent): LngLatDict | null => {
  let lng = e.lngLat.lng;
  let lat = e.lngLat.lat;

  // Holding alt bypasses all snapping
  if (e.originalEvent.altKey) {
    state.showVerticalSnapLine = false;
    state.showHorizontalSnapLine = false;

    return {lng, lat};
  }

  if (state.snapList.length <= 0) {
    return {lng, lat};
  }

  // snapping is on
  let closestLayer: LayerDistance, minDistance, snapLatLng;
  if (state.options.snap) {
    closestLayer = calculateClosestLayer({lng, lat}, state.snapList);

    // if no layers found. Can happen when circle is the only visible layer on the map and the hidden snapping-border circle layer is also on the map
    if (!closestLayer) {
      return null;
    }

    const isMarker = closestLayer.isMarker;
    const snapVertexPriorityDistance = state.options.snapOptions?.snapVertexPriorityDistance;

    if (!isMarker) {
      snapLatLng = checkPrioritiySnapping(
        closestLayer,
        state.options.snapOptions,
        snapVertexPriorityDistance
      );
      // snapLatLng = closestLayer.latlng;
    } else {
      snapLatLng = closestLayer.latlng;
    }

    minDistance =
      ((state.options.snapOptions && state.options.snapOptions.snapPx) || 15) *
      metersPerPixel(snapLatLng.lat, state.map.getZoom());
  }

  let verticalPx, horizontalPx;
  if (state.options.guides) {
    const nearestGuideline = getNearestGuideline(state.vertices, e.lngLat);

    verticalPx = nearestGuideline.verticalPx;
    horizontalPx = nearestGuideline.horizontalPx;

    if (verticalPx) {
      // Draw a line from top to bottom

      const lngLatTop = {lng: verticalPx, lat: e.lngLat.lat + 10};
      const lngLatBottom = {lng: verticalPx, lat: e.lngLat.lat - 10};

      state.verticalGuide.updateCoordinate("0", lngLatTop.lng, lngLatTop.lat);
      state.verticalGuide.updateCoordinate(
        "1",
        lngLatBottom.lng,
        lngLatBottom.lat
      );
    }

    if (horizontalPx) {
      // Draw a line from left to right

      const lngLatTop = {lng: e.lngLat.lng + 10, lat: horizontalPx};
      const lngLatBottom = {lng: e.lngLat.lng - 10, lat: horizontalPx};

      state.horizontalGuide.updateCoordinate("0", lngLatTop.lng, lngLatTop.lat);
      state.horizontalGuide.updateCoordinate(
        "1",
        lngLatBottom.lng,
        lngLatBottom.lat
      );
    }

    state.showVerticalSnapLine = !!verticalPx;
    state.showHorizontalSnapLine = !!horizontalPx;
  }

  if (closestLayer && closestLayer.distance * 1000 < minDistance) {
    return snapLatLng;
  } else if (verticalPx || horizontalPx) {
    if (verticalPx) {
      lng = verticalPx;
    }
    if (horizontalPx) {
      lat = horizontalPx;
    }
    return {lng, lat};
  } else {
    return {lng, lat};
  }
};

export const getGuideFeature = (id: string) => ({
  id,
  type: geojsonTypes.FEATURE,
  properties: {
    isSnapGuide: "true", // for styling
  },
  geometry: {
    type: geojsonTypes.LINE_STRING,
    coordinates: [] as Position[],
  },
});

export const shouldHideGuide = (state: State, geojson: Feature<Geometries>) => {
  if (
    geojson.properties.id === IDS.VERTICAL_GUIDE &&
    (!state.options.guides || !state.showVerticalSnapLine)
  ) {
    return true;
  }

  return geojson.properties.id === IDS.HORIZONTAL_GUIDE &&
    (!state.options.guides || !state.showHorizontalSnapLine);
};
