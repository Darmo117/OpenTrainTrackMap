import MapboxDraw from "@mapbox/mapbox-gl-draw";

import {createSnapList, snap} from "../utils";
import {GeometryState, SnapOptions} from "../types";
import {DrawCustomModeWithContext} from "./patch";

const {doubleClickZoom} = MapboxDraw.lib;
const DrawPoint = MapboxDraw.modes.draw_point;
const {geojsonTypes, cursors} = MapboxDraw.constants;

type PointState = GeometryState & {
  point: MapboxDraw.DrawPoint;
  selectedFeatures: MapboxDraw.DrawFeature[];
  snappedLng?: number;
  snappedLat?: number;
  lastVertex?: any;
};

const SnapPointMode = {...DrawPoint} as DrawCustomModeWithContext<PointState>;

SnapPointMode.onSetup = function () {
  const point = this.newFeature({
    type: geojsonTypes.FEATURE,
    properties: {},
    geometry: {
      type: geojsonTypes.POINT,
      coordinates: [],
    },
  }) as MapboxDraw.DrawPoint;

  this.addFeature(point);

  const selectedFeatures = this.getSelected();
  this.clearSelectedFeatures();
  doubleClickZoom.disable(this);

  const [snapList, vertices] =
    createSnapList(this.map as any, this._ctx.api, point as any);

  const state: PointState = {
    map: this.map as any,
    point,
    vertices,
    snapList,
    selectedFeatures,
    options: this._ctx.options,
  };

  const moveendCallback = () => {
    const [snapList, vertices] =
      createSnapList(this.map as any, this._ctx.api, point as any);
    state.vertices = vertices;
    state.snapList = snapList;
  };
  state.moveendCallback = moveendCallback;

  const optionsChangedCallBack = (options: SnapOptions) => {
    state.options = options;
  };
  state.optionsChangedCallBack = optionsChangedCallBack;

  this.map.on("moveend", moveendCallback);
  this.map.on("draw.snap.options_changed", optionsChangedCallBack);

  return state;
};

SnapPointMode.onClick = function (state: PointState) {
  // We mock out e with the rounded lng/lat then call DrawPoint with it
  // TODO fire add event
  DrawPoint.onClick.call(this, state, {
    lngLat: {
      lng: state.snappedLng,
      lat: state.snappedLat,
    },
  });
};

SnapPointMode.onMouseMove = function (state: PointState, e) {
  const {latLng: snapPos, snapped, target} = snap(state, e as any);
  if (!snapPos) {
    return;
  }

  const {lng, lat} = snapPos;
  state.snappedLng = lng;
  state.snappedLat = lat;
  let cursor = state.lastVertex && state.lastVertex[0] === lng && state.lastVertex[1] === lat
    ? cursors.POINTER
    : cursors.ADD;
  this.updateUIClasses({mouse: cursor});
};

SnapPointMode.onStop = function (state) {
  this.map.off("moveend", state.moveendCallback);
  this.map.off("draw.snap.options_changed", state.optionsChangedCallBack);
  DrawPoint.onStop.call(this, state);
};

export default SnapPointMode;
