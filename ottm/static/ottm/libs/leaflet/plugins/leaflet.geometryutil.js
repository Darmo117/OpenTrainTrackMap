import * as L from "../leaflet-src.esm.js";

L.Polyline._flat = L.LineUtil.isFlat ?? L.Polyline._flat ?? (latlngs => {
  // true if it's a flat array of latlngs; false if nested
  return !L.Util.isArray(latlngs[0]) || (typeof latlngs[0][0] !== "object" && typeof latlngs[0][0] !== "undefined");
});

/**
 * @fileOverview Leaflet Geometry utilities for distances and linear referencing.
 * @name GeometryUtil
 */
export const GeometryUtil = L.extend({}, {
  /**
   * Shortcut function for planar distance between two {L.LatLng} at current zoom.
   *
   * @param map Leaflet map to be used for this method
   * @param {L.LatLng} latlngA geographical point A
   * @param {L.LatLng} latlngB geographical point B
   * @returns {Number} planar distance
   */
  distance: function (map, latlngA, latlngB) {
    return map.latLngToLayerPoint(latlngA).distanceTo(map.latLngToLayerPoint(latlngB));
  },

  /**
   * Shortcut function for planar distance between a {L.LatLng} and a segment (A-B).
   *
   * @param map Leaflet map to be used for this method
   * @param {L.LatLng} latlng - The position to search
   * @param {L.LatLng} latlngA geographical point A of the segment
   * @param {L.LatLng} latlngB geographical point B of the segment
   * @returns {Number} planar distance
   */
  distanceSegment: function (map, latlng, latlngA, latlngB) {
    const p = map.latLngToLayerPoint(latlng);
    const p1 = map.latLngToLayerPoint(latlngA);
    const p2 = map.latLngToLayerPoint(latlngB);
    return L.LineUtil.pointToSegmentDistance(p, p1, p2);
  },

  /**
   * Shortcut function for converting distance to readable distance.
   *
   * @param {Number} distance distance to be converted
   * @param {String} unit "metric" or "imperial"
   * @returns {String} in m/km or yd/miles
   */
  readableDistance: function (distance, unit) {
    let distanceStr;
    if (unit !== "imperial") {
      // show metres when distance is < 1km, then show km
      if (distance > 1000) {
        distanceStr = (distance / 1000).toFixed(2) + " km";
      } else {
        distanceStr = distance.toFixed(1) + " m";
      }
    } else {
      distance *= 1.09361;
      if (distance > 1760) {
        distanceStr = (distance / 1760).toFixed(2) + " miles";
      } else {
        distanceStr = distance.toFixed(1) + " yd";
      }
    }
    return distanceStr;
  },

  /**
   * Returns true if the latlng belongs to segment A-B.
   *
   * @param latlng The position to search
   * @param latlngA geographical point A of the segment
   * @param latlngB geographical point B of the segment
   * @param {?Number} [tolerance=0.2] tolerance to accept if latlng belongs really
   * @returns {boolean}
   */
  belongsSegment: function (latlng, latlngA, latlngB, tolerance = 0.2) {
    const hypotenuse = latlngA.distanceTo(latlngB);
    const delta = latlngA.distanceTo(latlng) + latlng.distanceTo(latlngB) - hypotenuse;
    return delta / hypotenuse < tolerance;
  },

  /**
   * Returns total length of line
   *
   * @param {L.Polyline|L.Point[]|L.LatLng[]} coords Set of coordinates
   * @returns {Number} Total length (pixels for Point, meters for LatLng)
   */
  length: function (coords) {
    const accumulated = GeometryUtil.accumulatedLengths(coords);
    return accumulated.length > 0 ? accumulated[accumulated.length - 1] : 0;
  },

  /**
   * Returns a list of accumulated length along a line.
   *
   * @param {L.Polyline|L.Point[]|L.LatLng[]} coords Set of coordinates
   * @returns {Number[]} Array of accumulated lengths (pixels for Point, meters for LatLng)
   */
  accumulatedLengths: function (coords) {
    // noinspection JSUnresolvedReference
    if (typeof coords.getLatLngs === "function") {
      // noinspection JSUnresolvedReference
      coords = coords.getLatLngs();
    }
    if (coords.length === 0) {
      return [];
    }
    let total = 0;
    let lengths = [0];
    for (let i = 0, n = coords.length - 1; i < n; i++) {
      total += coords[i].distanceTo(coords[i + 1]);
      lengths.push(total);
    }
    return lengths;
  },

  /**
   * Returns the closest point of a L.LatLng on the segment (A-B).
   *
   * @param map Leaflet map to be used for this method
   * @param {L.LatLng} latlng - The position to search
   * @param {L.LatLng} latlngA geographical point A of the segment
   * @param {L.LatLng} latlngB geographical point B of the segment
   * @returns {L.LatLng} Closest geographical point
   */
  closestOnSegment: function (map, latlng, latlngA, latlngB) {
    let maxzoom = map.getMaxZoom();
    if (maxzoom === Infinity) {
      maxzoom = map.getZoom();
    }
    const p = map.project(latlng, maxzoom);
    const p1 = map.project(latlngA, maxzoom);
    const p2 = map.project(latlngB, maxzoom);
    const closest = L.LineUtil.closestPointOnSegment(p, p1, p2);
    return map.unproject(closest, maxzoom);
  },

  /**
   * Returns the closest latlng on layer.
   *
   * Accepts nested arrays.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.LatLng[]|L.LatLng[][]|L.Polyline|L.Polygon|L.Layer} layer Layer that contains the result
   * @param {L.LatLng} latlng - The position to search
   * @param {?boolean} [vertices=false] - Whether to restrict to path vertices.
   * @returns {L.LatLng} Closest geographical point or null if layer param is incorrect
   */
  closest: function (map, layer, latlng, vertices = false) {
    const latlngs = [];
    let mindist = Infinity;
    let result = null;

    if (layer instanceof Array) {
      // if layer is T[][]
      if (layer[0] instanceof Array && typeof layer[0][0] !== "number") {
        // if we have nested arrays, we calc the closest for each array recursive
        for (let i = 0; i < layer.length; i++) {
          const subResult = GeometryUtil.closest(map, layer[i], latlng, vertices);
          // noinspection JSUnresolvedReference
          if (subResult && subResult.distance < mindist) {
            // noinspection JSUnresolvedReference
            mindist = subResult.distance;
            result = subResult;
          }
        }
        return result;
      } else if (layer[0] instanceof L.LatLng
        || typeof layer[0][0] === "number"
        || typeof layer[0].lat === "number") { // we could have a latlng as [x,y] with x & y numbers or {lat, lng}
        layer = L.polyline(layer);
      } else {
        return result;
      }
    }

    // if we don't have here a Polyline, that means layer is incorrect
    // see https://github.com/makinacorpus/Leaflet.GeometryUtil/issues/23
    if (!(layer instanceof L.Polyline)) {
      return result;
    }

    // FIX: some layers may contain recursive objects that throw errors with JSON.stringify()
    // noinspection JSUnresolvedReference
    let lls = layer.getLatLngs();
    if (!L.LineUtil.isFlat(lls)) {
      lls = lls[0];
    }
    for (const latLng of lls) {
      latlngs.push({lat: latLng.lat, lng: latLng.lng});
    }
    // deep copy of latlngs
    // latlngs = JSON.parse(JSON.stringify(layer.getLatLngs().slice(0)));

    // add the last segment for L.Polygon
    if (layer instanceof L.Polygon) {
      // add the last segment for each child that is a nested array
      const addLastSegment = function (latlngs) {
        if (L.Polyline._flat(latlngs)) {
          latlngs.push(latlngs[0]);
        } else {
          for (let i = 0; i < latlngs.length; i++) {
            addLastSegment(latlngs[i]);
          }
        }
      };
      addLastSegment(latlngs);
    }

    // we have a multi polygon / multi polyline / polygon with holes
    // use recursive to explore and return the good result
    if (!L.Polyline._flat(latlngs)) {
      for (let i = 0; i < latlngs.length; i++) {
        // if we are at the lower level, and if we have a L.Polygon, we add the last segment
        const subResult = GeometryUtil.closest(map, latlngs[i], latlng, vertices);
        // noinspection JSUnresolvedReference
        if (subResult.distance < mindist) {
          // noinspection JSUnresolvedReference
          mindist = subResult.distance;
          result = subResult;
        }
      }
      return result;
    }

    // Lookup vertices
    if (vertices) {
      for (let i = 0, n = latlngs.length; i < n; i++) {
        const ll = latlngs[i];
        const distance = GeometryUtil.distance(map, latlng, ll);
        if (distance < mindist) {
          mindist = distance;
          result = ll;
          result.distance = distance;
        }
      }
      return result;
    }

    // Keep the closest point of all segments
    for (let i = 0, n = latlngs.length; i < n - 1; i++) {
      const latlngA = latlngs[i];
      const latlngB = latlngs[i + 1];
      const distance = GeometryUtil.distanceSegment(map, latlng, latlngA, latlngB);
      if (distance <= mindist) {
        mindist = distance;
        result = GeometryUtil.closestOnSegment(map, latlng, latlngA, latlngB);
        result.distance = distance;
      }
    }
    return result;
  },

  /**
   * Returns the closest layer to latlng among a list of layers.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.Layer[]} layers Set of layers
   * @param {L.LatLng} latlng - The position to search
   * @returns {object} ``{layer, latlng, distance}`` or ``null`` if list is empty;
   */
  closestLayer: function (map, layers, latlng) {
    let mindist = Infinity;
    let result = null;
    let distance = Infinity;

    for (let i = 0, n = layers.length; i < n; i++) {
      const layer = layers[i];
      if (layer instanceof L.LayerGroup) {
        // recursive
        // noinspection JSUnresolvedReference
        const subResult = GeometryUtil.closestLayer(map, layer.getLayers(), latlng);
        if (subResult.distance < mindist) {
          mindist = subResult.distance;
          result = subResult;
        }
      } else {
        // Single dimension, snap on points, else snap on closest
        let ll;
        // noinspection JSUnresolvedReference
        if (typeof layer.getLatLng == "function") {
          // noinspection JSUnresolvedReference
          ll = layer.getLatLng();
          distance = GeometryUtil.distance(map, latlng, ll);
        } else {
          ll = GeometryUtil.closest(map, layer, latlng);
          if (ll) {
            distance = ll.distance;
          }  // Can return null if layer has no points.
        }
        if (distance < mindist) {
          mindist = distance;
          result = {layer: layer, latlng: ll, distance: distance};
        }
      }
    }
    return result;
  },

  /**
   * Returns the n closest layers to latlng among a list of input layers.
   *
   * @param {L.Map} map - Leaflet map to be used for this method
   * @param {L.Layer[]} layers - Set of layers
   * @param {L.LatLng} latlng - The position to search
   * @param {?Number} [n=layers.length] - the expected number of output layers.
   * @returns {object[]} an array of objects ``{layer, latlng, distance}`` or ``null`` if the input is invalid (empty list or negative n)
   */
  nClosestLayers: function (map, layers, latlng, n = layers.length) {
    if (n < 1 || layers.length < 1) {
      return null;
    }

    let results = [];

    for (let i = 0, m = layers.length; i < m; i++) {
      const layer = layers[i];
      if (layer instanceof L.LayerGroup) {
        // recursive
        // noinspection JSUnresolvedReference
        results.push(GeometryUtil.closestLayer(map, layer.getLayers(), latlng));
      } else {
        // Single dimension, snap on points, else snap on closest
        let ll;
        let distance;
        // noinspection JSUnresolvedReference
        if (typeof layer.getLatLng === "function") {
          // noinspection JSUnresolvedReference
          ll = layer.getLatLng();
          distance = GeometryUtil.distance(map, latlng, ll);
        } else {
          ll = GeometryUtil.closest(map, layer, latlng);
          if (ll) {
            distance = ll.distance;
          }  // Can return null if layer has no points.
        }
        results.push({layer: layer, latlng: ll, distance: distance});
      }
    }

    results.sort((a, b) => a.distance - b.distance);

    return results.length > n ? results.slice(0, n) : results;
  },

  /**
   * Returns all layers within a radius of the given position, in an ascending order of distance.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.Layer[]} layers - A list of layers.
   * @param {L.LatLng} latlng - The position to search
   * @param {?Number} [radius=Infinity] - Search radius in pixels
   * @return {object[]} an array of objects including layer within the radius, closest latlng, and distance
   */
  layersWithin: function (map, layers, latlng, radius = Infinity) {
    const results = [];

    for (let i = 0, n = layers.length; i < n; i++) {
      const layer = layers[i];
      let ll = null;
      let distance = 0;

      // noinspection JSUnresolvedReference
      if (typeof layer.getLatLng === "function") {
        // noinspection JSUnresolvedReference
        ll = layer.getLatLng();
        distance = GeometryUtil.distance(map, latlng, ll);
      } else {
        ll = GeometryUtil.closest(map, layer, latlng);
        if (ll) {
          // noinspection JSUnresolvedReference
          distance = ll.distance;
        }  // Can return null if layer has no points.
      }

      if (ll && distance < radius) {
        results.push({layer: layer, latlng: ll, distance: distance});
      }
    }

    return results.sort((a, b) => a.distance - b.distance);
  },

  /**
   * Returns the closest position from specified {LatLng} among specified layers,
   * with a maximum tolerance in pixels, providing snapping behaviour.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {Layer[]} layers - A list of layers to snap on.
   * @param {L.LatLng} latlng - The position to snap
   * @param {?Number} [tolerance=Infinity] - Maximum number of pixels.
   * @param {?boolean} [withVertices=true] - Snap to layers vertices or segment points (not only vertex)
   * @returns {object} with snapped {LatLng} and snapped {Layer} or null if tolerance exceeded.
   */
  closestLayerSnap: function (map, layers, latlng,
                              tolerance = Infinity, withVertices = true) {
    const result = GeometryUtil.closestLayer(map, layers, latlng);
    if (!result || result.distance > tolerance) {
      return null;
    }

    // If snapped layer is linear, try to snap on vertices (extremities and middle points)
    // noinspection JSUnresolvedReference
    if (withVertices && typeof result.layer.getLatLngs === "function") {
      const closest = GeometryUtil.closest(map, result.layer, result.latlng, true);
      // noinspection JSUnresolvedReference
      if (closest.distance < tolerance) {
        result.latlng = closest;
        result.distance = GeometryUtil.distance(map, closest, latlng);
      }
    }
    return result;
  },

  /**
   * Returns the Point located on a segment at the specified ratio of the segment length.
   * @param {L.Point} pA coordinates of point A
   * @param {L.Point} pB coordinates of point B
   * @param {Number} ratio the length ratio, expressed as a decimal between 0 and 1, inclusive.
   * @returns {L.Point} the interpolated point.
   */
  interpolateOnPointSegment: function (pA, pB, ratio) {
    // noinspection JSUnresolvedReference
    return L.point(
      (pA.x * (1 - ratio)) + (ratio * pB.x),
      (pA.y * (1 - ratio)) + (ratio * pB.y)
    );
  },

  /**
   * Returns the coordinate of the point located on a line at the specified ratio of the line length.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.LatLng[]|L.Polyline} latlngs Set of geographical points
   * @param {Number} ratio the length ratio, expressed as a decimal between 0 and 1, inclusive
   * @returns {Object} an object with latLng (LatLng) and predecessor (Number), the index of the preceding vertex in the Polyline
   *  (-1 if the interpolated point is the first vertex)
   */
  interpolateOnLine: function (map, latlngs, ratio) {
    // noinspection JSUnresolvedReference
    latlngs = latlngs instanceof L.Polyline ? latlngs.getLatLngs() : latlngs;
    const n = latlngs.length;
    if (n < 2) {
      return null;
    }

    // ensure the ratio is between 0 and 1;
    ratio = Math.max(Math.min(ratio, 1), 0);

    if (ratio === 0) {
      return {
        latLng: latlngs[0] instanceof L.LatLng ? latlngs[0] : L.latLng(latlngs[0]),
        predecessor: -1
      };
    }
    if (ratio === 1) {
      return {
        latLng: latlngs[latlngs.length - 1] instanceof L.LatLng ? latlngs[latlngs.length - 1] : L.latLng(latlngs[latlngs.length - 1]),
        predecessor: latlngs.length - 2
      };
    }

    // project the LatLngs as Points,
    // and compute total planar length of the line at max precision
    // noinspection JSUnresolvedReference
    let maxzoom = map.getMaxZoom();
    if (maxzoom === Infinity) {
      // noinspection JSUnresolvedReference
      maxzoom = map.getZoom();
    }
    const pts = [];
    let lineLength = 0;
    for (let i = 0; i < n; i++) {
      // noinspection JSUnresolvedReference
      pts[i] = map.project(latlngs[i], maxzoom);
      if (i > 0) {
        lineLength += pts[i - 1].distanceTo(pts[i]);
      }
    }

    const ratioDist = lineLength * ratio;

    // follow the line segments [ab], adding lengths,
    // until we find the segment where the points should lie on
    let cumulativeDistanceToA = 0, cumulativeDistanceToB = 0;
    let pointA;
    let pointB;
    let i;
    for (i = 0; cumulativeDistanceToB < ratioDist; i++) {
      pointA = pts[i];
      pointB = pts[i + 1];
      cumulativeDistanceToA = cumulativeDistanceToB;
      cumulativeDistanceToB += pointA.distanceTo(pointB);
    }

    if (pointA === undefined && pointB === undefined) { // Happens when line has no length
      pointA = pts[0];
      pointB = pts[1];
      i = 1;
    }

    // compute the ratio relative to the segment [ab]
    const segmentRatio = (cumulativeDistanceToB - cumulativeDistanceToA) !== 0
      ? (ratioDist - cumulativeDistanceToA) / (cumulativeDistanceToB - cumulativeDistanceToA)
      : 0;
    const interpolatedPoint = GeometryUtil.interpolateOnPointSegment(pointA, pointB, segmentRatio);
    // noinspection JSUnresolvedReference
    return {
      latLng: map.unproject(interpolatedPoint, maxzoom),
      predecessor: i - 1
    };
  },

  /**
   * Returns a float between 0 and 1 representing the location of the
   * closest point on polyline to the given latlng, as a fraction of total line length.
   * (opposite of GeometryUtil.interpolateOnLine())
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.Polyline} polyline Polyline on which the latlng will be search
   * @param {L.LatLng} latlng The position to search
   * @returns {Number} Float between 0 and 1
   */
  locateOnLine: function (map, polyline, latlng) {
    // noinspection JSUnresolvedReference
    const latlngs = polyline.getLatLngs();
    // noinspection JSUnresolvedReference
    if (latlng.equals(latlngs[0])) {
      return 0.0;
    }
    // noinspection JSUnresolvedReference
    if (latlng.equals(latlngs[latlngs.length - 1])) {
      return 1.0;
    }

    const point = GeometryUtil.closest(map, polyline, latlng, false);
    const lengths = GeometryUtil.accumulatedLengths(latlngs);
    const total_length = lengths[lengths.length - 1];
    let portion = 0;
    let found = false;
    for (let i = 0, n = latlngs.length - 1; i < n; i++) {
      const l1 = latlngs[i];
      const l2 = latlngs[i + 1];
      portion = lengths[i];
      if (GeometryUtil.belongsSegment(point, l1, l2, 0.001)) {
        portion += l1.distanceTo(point);
        found = true;
        break;
      }
    }
    if (!found) {
      throw `Could not interpolate ${latlng} within ${polyline}`;
    }
    return portion / total_length;
  },

  /**
   * Returns a clone with reversed coordinates.
   *
   * @param {L.Polyline} polyline polyline to reverse
   * @returns {L.Polyline} polyline reversed
   */
  reverse: function (polyline) {
    // noinspection JSUnresolvedReference
    return L.polyline(polyline.getLatLngs().slice(0).reverse());
  },

  /**
   * Returns a sub-part of the polyline, from start to end.
   * If start is superior to end, returns extraction from inverted line.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.Polyline} polyline Polyline on which will be extracted the sub-part
   * @param {Number} start ratio, expressed as a decimal between 0 and 1, inclusive
   * @param {Number} end ratio, expressed as a decimal between 0 and 1, inclusive
   * @returns {L.LatLng[]} new polyline
   */
  extract: function (map, polyline, start, end) {
    if (start > end) {
      return GeometryUtil.extract(map, GeometryUtil.reverse(polyline), 1.0 - start, 1.0 - end);
    }

    // Bound start and end to [0-1]
    start = Math.max(Math.min(start, 1), 0);
    end = Math.max(Math.min(end, 1), 0);

    // noinspection JSUnresolvedReference
    const latlngs = polyline.getLatLngs();
    const startpoint = GeometryUtil.interpolateOnLine(map, polyline, start);
    const endpoint = GeometryUtil.interpolateOnLine(map, polyline, end);
    // Return single point if start == end
    if (start === end) {
      return [GeometryUtil.interpolateOnLine(map, polyline, end).latLng];
    }
    // Array.slice() works indexes at 0
    if (startpoint.predecessor === -1) {
      startpoint.predecessor = 0;
    }
    if (endpoint.predecessor === -1) {
      endpoint.predecessor = 0;
    }
    const result = latlngs.slice(startpoint.predecessor + 1, endpoint.predecessor + 1);
    result.unshift(startpoint.latLng);
    result.push(endpoint.latLng);
    return result;
  },

  /**
   * Returns true if first polyline ends where other second starts.
   *
   * @param {L.Polyline} polyline First polyline
   * @param {L.Polyline} other Second polyline
   * @returns {boolean}
   */
  isBefore: function (polyline, other) {
    if (!other) {
      return false;
    }
    // noinspection JSUnresolvedReference
    const lla = polyline.getLatLngs();
    // noinspection JSUnresolvedReference
    const llb = other.getLatLngs();
    return (lla[lla.length - 1]).equals(llb[0]);
  },

  /**
   * Returns true if first polyline starts where second ends.
   *
   * @param {L.Polyline} polyline First polyline
   * @param {L.Polyline} other Second polyline
   * @returns {boolean}
   */
  isAfter: function (polyline, other) {
    if (!other) {
      return false;
    }
    // noinspection JSUnresolvedReference
    const lla = polyline.getLatLngs();
    // noinspection JSUnresolvedReference
    const llb = other.getLatLngs();
    return (lla[0]).equals(llb[llb.length - 1]);
  },

  /**
   * Returns true if first polyline starts where second ends or start.
   *
   * @param {L.Polyline} polyline First polyline
   * @param {L.Polyline} other Second polyline
   * @returns {boolean}
   */
  startsAtExtremity: function (polyline, other) {
    if (!other) {
      return false;
    }
    // noinspection JSUnresolvedReference
    const lla = polyline.getLatLngs();
    // noinspection JSUnresolvedReference
    const llb = other.getLatLngs();
    const start = lla[0];
    return start.equals(llb[0]) || start.equals(llb[llb.length - 1]);
  },

  /**
   * Returns horizontal angle in degres between two points.
   *
   * @param {L.Point} a Coordinates of point A
   * @param {L.Point} b Coordinates of point B
   * @returns {Number} horizontal angle
   */
  computeAngle: function (a, b) {
    // noinspection JSUnresolvedReference
    return (Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI);
  },

  /**
   * Returns slope (Ax+B) between two points.
   *
   * @param {L.Point} a Coordinates of point A
   * @param {L.Point} b Coordinates of point B
   * @returns {Object} with ``a`` and ``b`` properties.
   */
  computeSlope: function (a, b) {
    // noinspection JSUnresolvedReference
    const s = (b.y - a.y) / (b.x - a.x);
    // noinspection JSUnresolvedReference
    const o = a.y - (s * a.x);
    return {'a': s, 'b': o};
  },

  /**
   * Returns LatLng of rotated point around specified LatLng center.
   *
   * @param map the map
   * @param {L.LatLng} latlngPoint point to rotate
   * @param {number} angleDeg angle to rotate in degrees
   * @param {L.LatLng} latlngCenter center of rotation
   * @returns {L.LatLng} rotated point
   */
  rotatePoint: function (map, latlngPoint, angleDeg, latlngCenter) {
    let maxzoom = map.getMaxZoom();
    if (maxzoom === Infinity) {
      maxzoom = map.getZoom();
    }
    const angleRad = angleDeg * Math.PI / 180;
    const pPoint = map.project(latlngPoint, maxzoom);
    const pCenter = map.project(latlngCenter, maxzoom);
    const x2 = Math.cos(angleRad) * (pPoint.x - pCenter.x) - Math.sin(angleRad) * (pPoint.y - pCenter.y) + pCenter.x;
    const y2 = Math.sin(angleRad) * (pPoint.x - pCenter.x) + Math.cos(angleRad) * (pPoint.y - pCenter.y) + pCenter.y;
    return map.unproject(new L.Point(x2, y2), maxzoom);
  },

  /**
   * Returns the bearing in degrees clockwise from north (0 degrees)
   * from the first L.LatLng to the second, at the first LatLng.
   *
   * @param {L.LatLng} latlng1 origin point of the bearing
   * @param {L.LatLng} latlng2 destination point of the bearing
   * @returns {number} degrees clockwise from north.
   */
  bearing: function (latlng1, latlng2) {
    const rad = Math.PI / 180;
    const lat1 = latlng1.lat * rad;
    const lat2 = latlng2.lat * rad;
    const lon1 = latlng1.lng * rad;
    const lon2 = latlng2.lng * rad;
    const y = Math.sin(lon2 - lon1) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(lon2 - lon1);
    const bearing = ((Math.atan2(y, x) * 180 / Math.PI) + 360) % 360;
    return bearing >= 180 ? bearing - 360 : bearing;
  },

  /**
   * Returns the point that is a distance and heading away from the given origin point.
   *
   * @param {L.LatLng} latlng origin point
   * @param {number} heading heading in degrees, clockwise from 0 degrees north.
   * @param {number} distance distance in meters
   * @returns {L.LatLng} the destination point.
   *  Many thanks to Chris Veness at http://www.movable-type.co.uk/scripts/latlong.html
   *  for a great reference and examples.
   */
  destination: function (latlng, heading, distance) {
    heading = (heading + 360) % 360;
    const rad = Math.PI / 180;
    const radInv = 180 / Math.PI;
    const R = 6378137;  // approximation of Earth's radius
    const lon1 = latlng.lng * rad;
    const lat1 = latlng.lat * rad;
    const rheading = heading * rad;
    const sinLat1 = Math.sin(lat1);
    const cosLat1 = Math.cos(lat1);
    const cosDistR = Math.cos(distance / R);
    const sinDistR = Math.sin(distance / R);
    const lat2 = Math.asin(sinLat1 * cosDistR + cosLat1 * sinDistR * Math.cos(rheading));
    let lon2 = lon1 + Math.atan2(Math.sin(rheading) * sinDistR * cosLat1,
      cosDistR - sinLat1 * Math.sin(lat2));
    lon2 = lon2 * radInv;
    lon2 = lon2 > 180 ? lon2 - 360 : lon2 < -180 ? lon2 + 360 : lon2;
    return L.latLng([lat2 * radInv, lon2]);
  },

  /**
   * Returns the the angle of the given segment and the Equator in degrees,
   * clockwise from 0 degrees north.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.LatLng} latlngA geographical point A of the segment
   * @param {L.LatLng} latlngB geographical point B of the segment
   * @returns {number} the angle in degrees.
   */
  angle: function (map, latlngA, latlngB) {
    // noinspection JSUnresolvedReference
    const pointA = map.latLngToContainerPoint(latlngA);
    // noinspection JSUnresolvedReference
    const pointB = map.latLngToContainerPoint(latlngB);
    let angleDeg = Math.atan2(pointB.y - pointA.y, pointB.x - pointA.x) * 180 / Math.PI + 90;
    angleDeg += angleDeg < 0 ? 360 : 0;
    return angleDeg;
  },

  /**
   * Returns a point snaps on the segment and heading away from the given origin point a distance.
   *
   * @param {L.Map} map Leaflet map to be used for this method
   * @param {L.LatLng} latlngA geographical point A of the segment
   * @param {L.LatLng} latlngB geographical point B of the segment
   * @param {number} distance distance in meters
   * @returns {L.LatLng} the destination point.
   */
  destinationOnSegment: function (map, latlngA, latlngB, distance) {
    const angleDeg = GeometryUtil.angle(map, latlngA, latlngB);
    const latlng = GeometryUtil.destination(latlngA, angleDeg, distance);
    return GeometryUtil.closestOnSegment(map, latlng, latlngA, latlngB);
  },
});
