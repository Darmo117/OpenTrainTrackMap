// Heavily inspired from work of @davidgilbertson on Github and `leaflet-geoman` project.
import {Map, MapMouseEvent} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import {Feature, LineString, Polygon, Position} from "@turf/helpers";
import bboxPolygon from "@turf/bbox-polygon";
import booleanDisjoint from "@turf/boolean-disjoint";
import {getCoords} from "@turf/invariant";
import distance from "@turf/distance";
import polygonToLine from "@turf/polygon-to-line";
import nearestPointOnLine from "@turf/nearest-point-on-line";
import midpoint from "@turf/midpoint";

import {ValidGeometry} from "../../editor-types";
import {SnapSubOptions, State} from "../types";

const {geojsonTypes} = MapboxDraw.constants;

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
  currentFeature: Feature<ValidGeometry>
): [Feature<ValidGeometry>[], Position[]] {
  // Get all drawn features
  const features: Feature<ValidGeometry>[] = drawApi.getAll().features;
  const bboxAsPolygon = getCurrentMapBbox(map);

  const snapList: Feature<ValidGeometry>[] = [];
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

    extractVertices(feature.geometry.coordinates);

    // If feature is currently on viewport add to snap list
    if (!booleanDisjoint(bboxAsPolygon, feature)) {
      snapList.push(feature);
    }
  });

  return [snapList, vertices];
}

export type Snap = {
  /**
   * The feature the point was snapped to.
   */
  target?: {
    /**
     * The actual feature object.
     */
    feature: Feature<ValidGeometry>,
    /**
     * The path (vertex ID) the point was snapped to. Absent if the point was snapped on a segment.
     */
    path?: string,
  };
  /**
   * The snap position.
   */
  latLng?: LngLatDict;
  /**
   * Whether the point was snapped to a feature.
   */
  snapped: boolean;
};

/**
 * Return a snap point for the given mouse event.
 * If there aren’t any available or the control key is held, the event’s lng/lat is returned.
 * Also, defines if vertices should show on the state object
 *
 * Mutates the state object.
 * @param state The current state.
 * @param e The mouse event.
 * @returns The snap coordinates and a boolean indicating whether the point was snapped to a feature.
 */
export function snap(state: State, e: MapMouseEvent): Snap {
  let latLng: LngLatDict = e.lngLat;

  if (e.originalEvent.ctrlKey || state.snapList.length == 0) {
    return {latLng, snapped: false};
  }

  if (state.options.snap) {
    const closestLayer = getClosestLayer(latLng, state.snapList);
    // If no layers were found. Can happen when circle is the only visible layer on the map
    // and the hidden snapping-border circle layer is also on the map.
    if (!closestLayer) {
      return {snapped: false};
    }

    let snapLatLng: LngLatDict;
    let snapIndex: number;
    if (closestLayer.isMarker) {
      snapLatLng = closestLayer.latlng;
    } else {
      [snapLatLng, snapIndex] = checkPrioritySnapping(
        closestLayer,
        state.options.snapOptions,
        state.options.snapOptions?.snapVertexPriorityDistance
      );
    }

    const minDistance =
      (state.options.snapOptions?.snapPx ?? 15) *
      getMetersPerPixel(snapLatLng.lat, state.map.getZoom());
    if (closestLayer.distance * 1000 < minDistance) {
      return {
        latLng: snapLatLng,
        snapped: true,
        target: {
          feature: closestLayer.feature,
          path: snapIndex?.toString(),
        },
      };
    }
  }

  return {latLng, snapped: false};
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

type LayerDistance = {
  latlng: LngLatDict;
  segment?: [Position, Position];
  segmentIndex?: number,
  distance: number;
  isMarker: boolean;
  feature: Feature<ValidGeometry>,
};

/**
 * Calculate the distance between the given coordinates and feature.
 * @param lngLat The coordinates of the point.
 * @param layer The layer to get the distance to.
 */
function getDistanceToLayer(lngLat: LngLatDict, layer: Feature<ValidGeometry>): LayerDistance {
  const point: Position = [lngLat.lng, lngLat.lat];

  if (layer.geometry.type === "Point") {
    const layerLatLngs = getCoords(layer);
    const [lng, lat] = layerLatLngs;
    return {
      latlng: {lng, lat},
      distance: distance(layerLatLngs, point),
      isMarker: true,
      feature: layer,
    };
  }

  let line: Feature<LineString>;
  if (layer.geometry.type === "Polygon") {
    // Extract the line from the polygon
    line = polygonToLine(layer as Feature<Polygon>) as Feature<LineString>;
  } else {
    line = layer as Feature<LineString>;
  }
  const nearestPoint = nearestPointOnLine(line, point);

  let segmentIndex = nearestPoint.properties.index;
  if (segmentIndex + 1 === line.geometry.coordinates.length) {
    segmentIndex--;
  }

  const [lng, lat] = nearestPoint.geometry.coordinates;
  return {
    latlng: {lng, lat},
    segment: line.geometry.coordinates.slice(segmentIndex, segmentIndex + 2) as [Position, Position],
    segmentIndex: segmentIndex,
    distance: nearestPoint.properties.dist,
    isMarker: false,
    feature: layer,
  };
}

/**
 * Get the feature that is the closest to the given point.
 * @param lngLat A point.
 * @param layers A list of layers.
 * @returns The closest layer with its distance to the given point or undefined if none were found.
 */
function getClosestLayer(
  lngLat: LngLatDict,
  layers: Feature<ValidGeometry>[]
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

/**
 * Get the number of meters per pixel for the given latitude and zoom level,
 * assuming an Equator circumference of 40,075,017 meters.
 * @param latitude A latitude.
 * @param zoomLevel A zoom level.
 * @returns The number of meters per pixel.
 */
function getMetersPerPixel(latitude: number, zoomLevel: number): number {
  const earthCircumference = 40_075_017;
  const latitudeRadians = latitude * (Math.PI / 180);
  return (earthCircumference * Math.cos(latitudeRadians)) / (2 ** (zoomLevel + 8));
}

/**
 * Return the snap position for the given layer and distance.
 * @param closestLayer The layer with its distance to the vertex to snap.
 * @param snapOptions The snap options.
 * @param snapVertexPriorityDistance The distance that needs to be undercut to trigger priority.
 * @returns The snap position and a number indicating if the index of the segment vertex the point was snapped to.
 */
function snapToLineOrPolygon(
  closestLayer: LayerDistance,
  snapOptions: SnapSubOptions | undefined,
  snapVertexPriorityDistance: number
): [LngLatDict, number] {
  // A and B are the points of the closest segment to P (the marker position we want to snap).
  const [A, B] = closestLayer.segment;
  // C is the point we would snap to on the segment.
  // The closest point on the closest segment of the closest polygon to P.
  const C = [closestLayer.latlng.lng, closestLayer.latlng.lat];

  // Distances from A to C and B to C to check which one is closer to C
  const distanceAC = distance(A, C);
  const distanceBC = distance(B, C);

  // Closest latlng to C among A and B
  let closestVertexLatLng: number[];
  let closestVertexIndex = closestLayer.segmentIndex;
  if (distanceAC < distanceBC) {
    closestVertexLatLng = A;
  } else {
    closestVertexLatLng = B;
    closestVertexIndex += 1;
  }
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
  let lng: number, lat: number;
  let onPoint = shortestDistance < snapVertexPriorityDistance;
  if (onPoint) {
    [lng, lat] = closestVertexLatLng;
  } else {
    [lng, lat] = C;
  }
  // Return the copy of snapping point
  return [{lng, lat}, onPoint ? closestVertexIndex : -1];
}

/**
 * Check whether the snap position is on a vertex or a segment.
 * @param closestLayer A layer.
 * @param snapOptions The snap options.
 * @param snapVertexPriorityDistance The distance that needs to be undercut to trigger priority.
 * @returns The snap position and a number indicating if the index of the segment vertex the point was snapped to.
 */
function checkPrioritySnapping(
  closestLayer: LayerDistance,
  snapOptions: SnapSubOptions | undefined,
  snapVertexPriorityDistance: number = 1.25
): [LngLatDict, number] {
  return !closestLayer.segment ? [closestLayer.latlng, -1] : snapToLineOrPolygon(
    closestLayer,
    snapOptions,
    snapVertexPriorityDistance
  );
}
