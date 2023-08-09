L.Snap = {
  // try to prefer the corner of guidelines, or the the intersection of gridlines, if we're within the tolerance of two
  _findGuideIntersection: function (gType, map, latlng, guides) {
    const isNS = guides[0].layer[`_${gType}lineGroup`] === "NS";
    const nsi = isNS ? 1 : 0;
    const wei = isNS ? 0 : 1;
    const ns = this._defaultShape(guides[nsi].layer._latlngs)[0];
    const we = this._defaultShape(guides[wei].layer._latlngs)[0];
    const intersection = new L.LatLng(ns.lat, we.lng);
    // noinspection JSCheckFunctionSignatures
    const distance = L.GeometryUtil.distance(map, intersection, latlng);
    return {
      "intersection": intersection,
      "distance": distance
    };
  },

  _findClosestLayerSnap: function (map, layers, latlng, tolerance, onlyVertices) {
    const closest = L.GeometryUtil.nClosestLayers(map, layers, latlng, 6);

    // code to correct prefer snap to shapes (or only their vertices, if onlyVertices is true)
    // to gridlines and guidelines, and then guidelines to gridlines
    const withinTolerance = [];
    const pointsWithinTolerance = [];
    const shapesWithinTolerance = [];
    const guidesWithinTolerance = [];
    for (const layerInfo of closest) {
      if (layerInfo.distance < tolerance) {
        withinTolerance.push(layerInfo);
        if (layerInfo.layer.hasOwnProperty("_latlng")) {
          pointsWithinTolerance.push(layerInfo);
        } else if (!layerInfo.layer.hasOwnProperty("_gridlineGroup") && !layerInfo.layer.hasOwnProperty("_guidelineGroup")) {
          shapesWithinTolerance.push(layerInfo);
        } else if (layerInfo.layer.hasOwnProperty("_guidelineGroup")) {
          guidesWithinTolerance.push(layerInfo);
        }
      }
    }

    if (withinTolerance.length === 0) {
      return null;
    }

    let intInfo;
    let returnLayer = withinTolerance[0].layer;
    let returnLatLng = withinTolerance[0].latlng;

    if (pointsWithinTolerance.length > 0) {
      const pointInfo = pointsWithinTolerance[0];
      returnLayer = pointInfo.layer;
      returnLatLng = pointInfo.latlng;
    } else if (shapesWithinTolerance.length > 0) {
      const shapeInfo = shapesWithinTolerance[0];
      returnLayer = shapeInfo.layer;
      returnLatLng = shapeInfo.latlng;

      // this is code from L.GeometryUtil.closestSnap that will find
      // the closest vertex of this layer to the point
      const vertexLatLng = L.GeometryUtil.closest(map, shapeInfo.layer, shapeInfo.latlng, true);

      if (vertexLatLng) {
        const d = L.GeometryUtil.distance(map, latlng, vertexLatLng);
        if (d < tolerance) {
          returnLatLng = new L.LatLng(vertexLatLng.lat, vertexLatLng.lng);
        } else if (onlyVertices) {
          return null;
        }
      } else if (onlyVertices) {
        return null;
      }
    } else if (guidesWithinTolerance.length > 0) {
      const guideInfo = guidesWithinTolerance[0];

      for (const item of withinTolerance) {
        intInfo = this._findGuideIntersection("guide", map, latlng, [guideInfo, item]);
        if (intInfo.distance < tolerance) {
          returnLatLng = intInfo.intersection;
          break;
        }
      }
    } else {
      if (withinTolerance.length === 2) {
        intInfo = this._findGuideIntersection("grid", map, latlng, withinTolerance);
        if (intInfo.distance < tolerance) {
          returnLatLng = intInfo.intersection;
        }
      }
    }

    return {
      "layer": returnLayer,
      "latlng": returnLatLng
    };
  },

  // Compatibility method to normalize Poly* objects
  // between 0.7.x and 1.0+
  // pulled from code from L.Edit.Poly in Leaflet.Draw
  _defaultShape: function (latlngs) {
    if (!L.Polyline._flat) {
      return latlngs;
    }
    return L.Polyline._flat(latlngs) ? latlngs : latlngs[0];
  },

  _updateSnap: function (marker, layer, latlng) {
    if (!marker.hasOwnProperty("_latlng")) {
      return;
    }

    if (layer && latlng) {
      // don't call setLatLng so that we don't fire an unnecessary 'move' event
      marker._latlng = L.latLng(latlng);
      marker.update();
      if (marker.snap !== layer) {
        marker.snap = layer;
        if (marker._icon) {
          L.DomUtil.addClass(marker._icon, "marker-snapped");
        }
        marker.fire("snap", {layer: layer, latlng: latlng});
      }
    } else {
      if (marker.snap) {
        if (marker._icon) {
          L.DomUtil.removeClass(marker._icon, "marker-snapped");
        }
        marker.fire("unsnap", {layer: marker.snap});
      }

      delete marker.snap;
    }
  },

  snapMarker: function (e, guides, map, options) {
    const marker = e.target;
    const latlng = e.target._latlng ?? e.latlng;

    if (!latlng) {
      return;
    }

    const snaplist = [];
    for (const guide of guides) {
      // don't snap to vertices of a poly object for poly move
      if (marker.hasOwnProperty("_owner") && guide._leaflet_id === marker._owner) {
        continue;
      }
      snaplist.push(guide);
    }

    if (snaplist.length === 0) {
      return;
    }

    const closest =
      this._findClosestLayerSnap(map, snaplist, latlng, options.snapDistance, options.onlyVertices)
      ?? {layer: null, latlng: null};
    this._updateSnap(marker, closest.layer, closest.latlng);

    if (e.latlng && closest.latlng) {
      e.latlng = closest.latlng;
    }
  },
};

L.Handler.MarkerSnap = L.Handler.extend({
  options: {
    snapDistance: 15, // in pixels
    onlyVertices: false
  },

  initialize: function (map, marker, options) {
    L.Handler.prototype.initialize.call(this, map);
    this._markers = [];
    this._guides = [];

    if (arguments.length === 2) {
      if (!(marker instanceof L.Class)) {
        options = marker;
        marker = null;
      }
    }

    L.Util.setOptions(this, options ?? {});
  },

  enable: function () {
    this.disable();
    for (const item of this._markers) {
      this.watchMarker(item);
    }
  },

  disable: function () {
    for (const item of this._markers) {
      this.unwatchMarker(item);
    }
  },

  watchMarker: function (marker) {
    if (this._markers.indexOf(marker) === -1) {
      this._markers.push(marker);
    }
    marker.on("move", this._snapMarker, this);
    this._map.on("touchmove", this._snapMarker, this);
  },

  unwatchMarker: function (marker) {
    marker.off("move", this._snapMarker, this);
    this._map.off("touchmove", this._snapMarker, this);
    delete marker.snap;
  },

  addGuideLayer: function (layer) {
    for (const item of this._guides) {
      if (L.stamp(layer) === L.stamp(item)) {
        return;
      }
    }
    this._guides.push(layer);
  },

  _snapMarker: function (e) {
    L.Snap.snapMarker(e, this._guides, this._map, this.options);
  }
});
