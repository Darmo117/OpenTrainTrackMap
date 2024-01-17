import * as mgl from "maplibre-gl";
import * as geojson from "geojson";
import * as turfh from "@turf/helpers";
import distance from "@turf/distance";
import polygonToLine from "@turf/polygon-to-line";
import nearestPointOnLine from "@turf/nearest-point-on-line";

import * as geom from "./geometry";

/**
 * Union of the object types returned by {@link trySnapPoint}.
 */
export type SnapResult = SnapPoint | SnapSegmentVertex | SnapSegment;

/**
 * Object returned by {@link trySnapPoint} when the point was snapped to an isolated point.
 */
export type SnapPoint = {
  type: "point";
  /**
   * The snapped point.
   */
  point: geom.Point;
};

/**
 * Object returned by {@link trySnapPoint} when the point was snapped to a segment’s vertex.
 */
export type SnapSegmentVertex = {
  type: "segment_vertex";
  /**
   * The feature the snapped vertex belongs to.
   */
  feature: geom.LinearFeature;
  /**
   * The path to the snapped vertex in the feature.
   */
  path: string;
}

/**
 * Object returned by {@link trySnapPoint} when the point was snapped to segment.
 */
export type SnapSegment = {
  type: "segment";
  /**
   * The feature the snapped segment belongs to.
   */
  feature: geom.LinearFeature;
  /**
   * The path to the snapped segment in the feature.
   */
  path: string;
  /**
   * The snap position on the segment.
   */
  lngLat: mgl.LngLat;
};

/**
 * Try to snap the given position to a nearby feature.
 * @param pos The position to try to snap.
 * @param features The list of available features.
 * @param zoom The current map zoom lever.
 * @param snapDistancePx Optional. Maximum snap distance in pixels.
 * @returns Information for the snap position or null if nothing was snapped.
 */
export function trySnapPoint(
    pos: mgl.LngLat,
    features: geom.MapFeature[],
    zoom: number,
    snapDistancePx: number = 5
): SnapResult | null {
  const res = getClosestFeature(pos, features);
  if (!res) {
    return null;
  }
  // Only return if pixel distance is less than threshold
  if (res.dist * 1000 > snapDistancePx * getMetersPerPixel(res.lngLat.lat, zoom)) {
    return null;
  }
  if (res.feature instanceof geom.Point) {
    return {
      type: "point",
      point: res.feature,
    };
  } else if (res.feature instanceof geom.LinearFeature) {
    const vertexPath = checkSnapToSegmentVertex(res, features, 0.0025);
    if (vertexPath) {
      return {
        type: "segment_vertex",
        feature: res.feature,
        path: vertexPath,
      }
    } else {
      return {
        type: "segment",
        feature: res.feature,
        path: res.path,
        lngLat: res.lngLat,
      }
    }
  }
}

/**
 * Given a non-point feature, check if we should snap to one of the vertices of the specified segment.
 * @param feature The feature to check.
 * @param features List of allowed features.
 * If a vertex of the feature segment is not in this list, it cannot be snapped to.
 * @param snapVertexPriorityDistance The distance that needs to be undercut to trigger priority to vertices.
 * @returns The path of the selected segment vertex or null if the point is too far from a vertex.
 */
function checkSnapToSegmentVertex(
    feature: ClosestFeature,
    features: geom.MapFeature[],
    snapVertexPriorityDistance: number
): string | null {
  const [A, B] = feature.segment;
  const aIncluded = features.includes(A);
  const bIncluded = features.includes(B);

  if (!aIncluded && !bIncluded) {
    return null;
  }

  const C = [feature.lngLat.lng, feature.lngLat.lat];
  const distanceAC = distance(A.lngLat.toArray(), C);
  const distanceBC = distance(B.lngLat.toArray(), C);

  if (aIncluded && !bIncluded || aIncluded && bIncluded && distanceAC < distanceBC) {
    return distanceAC < snapVertexPriorityDistance
        ? feature.path
        : null;
  } else if (!aIncluded && bIncluded || aIncluded && bIncluded && distanceBC < distanceAC) {
    return distanceBC < snapVertexPriorityDistance
        ? (feature.feature as geom.LinearFeature).incrementPath(feature.path)
        : null;
  } else {
    return null;
  }
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
 * This object is returned by the {@link getClosestFeature} function.
 */
type ClosestFeature = {
  /**
   * Position of the projected point on the closest feature.
   */
  lngLat: mgl.LngLat;
  /**
   * Distance in kilometers between the point and its projection.
   */
  dist: number;
  /**
   * The feature the projected points is on.
   */
  feature: geom.MapFeature;
  /**
   * Optional. If the feature is not a point, path to the segment on which the point was projected.
   */
  path?: string;
  /**
   * Optional. If the feature is not a point, the vertices of segment on which the point was projected.
   */
  segment?: [geom.Point, geom.Point],
};

/**
 * Return the closest point or feature border to the given point.
 * A feature border is either a {@link geom.LineString} or a {@link geom.Polygon}’s ring.
 * @param pos Position of the point.
 * @param features List of features to search into.
 * @returns A ClosestFeature object or null if the list is empty.
 * @see ClosestFeature
 */
function getClosestFeature(pos: mgl.LngLat, features: geom.MapFeature[]): ClosestFeature | null {
  let closestFeature: ClosestFeature = null;
  for (const feature of features) {
    if (feature instanceof geom.Point) {
      const dist = distance(pos.toArray(), feature);
      if (!closestFeature || dist < closestFeature.dist) {
        closestFeature = {
          lngLat: feature.lngLat,
          dist: dist,
          feature: feature,
        };
      }

    } else if (feature instanceof geom.LineString) {
      const nearestPoint = nearestPointOnLine(feature, pos.toArray());
      if ((!closestFeature || nearestPoint.properties.dist < closestFeature.dist)
          // Segment index may be > than actual number of segments on line feature
          && nearestPoint.properties.index < feature.vertices.count() - 1) {
        const path = "" + nearestPoint.properties.index;
        closestFeature = {
          lngLat: mgl.LngLat.convert(nearestPoint.geometry.coordinates as [number, number]),
          dist: nearestPoint.properties.dist,
          feature: feature,
          path: path, // Index of the nearest segment
          segment: feature.getSegmentVertices(path),
        };
      }

    } else if (feature instanceof geom.Polygon) {
      const lines = polygonToLine(feature) as geojson.Feature<geojson.LineString | geojson.MultiLineString>;
      let coords: geojson.Position[][];
      if (lines.geometry.type === "LineString") { // Polygon without holes
        coords = [lines.geometry.coordinates];
      } else if (lines.geometry.type === "MultiLineString") { // Polygon with holes
        coords = lines.geometry.coordinates;
      }
      for (let i = 0; i < coords.length; i++) {
        const lineCoords = coords[i];
        const nearestPoint = nearestPointOnLine(turfh.lineString(lineCoords), pos.toArray());
        if (!closestFeature || nearestPoint.properties.dist < closestFeature.dist) {
          const path = `${i}.${nearestPoint.properties.index}`;
          closestFeature = {
            lngLat: mgl.LngLat.convert(nearestPoint.geometry.coordinates as [number, number]),
            dist: nearestPoint.properties.dist,
            feature: feature,
            path: path,
            segment: feature.getSegmentVertices(path),
          };
        }
      }
    }
  }
  return closestFeature;
}
