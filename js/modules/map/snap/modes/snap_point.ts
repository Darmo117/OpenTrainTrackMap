import MapboxDraw from "@mapbox/mapbox-gl-draw";
import {Feature, Geometries} from "@turf/helpers";

import {createSnapList, getGuideFeature, GuideId, shouldHideGuide, snap} from "../utils";
import {GeometryState, SnapOptions} from "../state";
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

// @ts-ignore
const SnapPointMode: DrawCustomModeWithContext<PointState> = {...DrawPoint};

SnapPointMode.onSetup = function () {
  const point = this.newFeature({
    type: geojsonTypes.FEATURE,
    properties: {},
    geometry: {
      type: geojsonTypes.POINT,
      coordinates: [0, 0],
    },
  }) as MapboxDraw.DrawPoint;

  const verticalGuide = this.newFeature(getGuideFeature(GuideId.VERTICAL));
  const horizontalGuide = this.newFeature(getGuideFeature(GuideId.HORIZONTAL));

  this.addFeature(point);
  this.addFeature(verticalGuide);
  this.addFeature(horizontalGuide);

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
    verticalGuide,
    horizontalGuide,
    options: this._ctx.options,
  };

  const moveendCallback = () => {
    const [snapList, vertices] =
      createSnapList(this.map as any, this._ctx.api, point as any);
    state.vertices = vertices;
    state.snapList = snapList;
  };
  // for removing listener later on close
  state.moveendCallback = moveendCallback;

  const optionsChangedCallBack = (options: SnapOptions) => {
    state.options = options;
  };
  // for removing listener later on close
  state.optionsChangedCallBack = optionsChangedCallBack;

  this.map.on("moveend", moveendCallback);
  this.map.on("draw.snap.options_changed", optionsChangedCallBack);

  return state;
};

SnapPointMode.onClick = function (state) {
  // We mock out e with the rounded lng/lat then call DrawPoint with it
  DrawPoint.onClick.call(this, state, {
    lngLat: {
      lng: state.snappedLng,
      lat: state.snappedLat,
    },
  });
};

SnapPointMode.onMouseMove = function (state: PointState, e) {
  const snapPos = snap(state, e as any);

  if (!snapPos) {
    return;
  }

  const {lng, lat} = snapPos;

  state.snappedLng = lng;
  state.snappedLat = lat;

  if (
    state.lastVertex &&
    state.lastVertex[0] === lng &&
    state.lastVertex[1] === lat
  ) {
    this.updateUIClasses({mouse: cursors.POINTER});

    // cursor options:
    // ADD: "add"
    // DRAG: "drag"
    // MOVE: "move"
    // NONE: "none"
    // POINTER: "pointer"
  } else {
    this.updateUIClasses({mouse: cursors.ADD});
  }
};

// This is 'extending' DrawPoint.toDisplayFeatures
SnapPointMode.toDisplayFeatures = function (
  state: PointState,
  geojson: Feature<Geometries>,
  display: (geojson: Feature<Geometries>) => void
) {
  if (shouldHideGuide(state, geojson)) {
    return;
  }

  // This relies on the the state of SnapPointMode having a 'point' prop
  // @ts-ignore
  DrawPoint.toDisplayFeatures(state, geojson, display);
};

// This is 'extending' DrawPoint.onStop
SnapPointMode.onStop = function (state) {
  this.deleteFeature(GuideId.VERTICAL, {silent: true});
  this.deleteFeature(GuideId.HORIZONTAL, {silent: true});

  // remove moveemd callback
  this.map.off("moveend", state.moveendCallback);

  // This relies on the the state of SnapPointMode having a 'point' prop
  DrawPoint.onStop.call(this, state);
};

export default SnapPointMode;
