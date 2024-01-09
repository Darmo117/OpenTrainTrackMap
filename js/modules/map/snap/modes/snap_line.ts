import MapboxDraw from "@mapbox/mapbox-gl-draw";

import {addPointToList, createSnapList, snap} from "../utils";
import {GeometryState, SnapOptions} from "../types";
import {DrawCustomModeWithContext} from "./patch";

const {
  geojsonTypes,
  modes,
  cursors,
} = MapboxDraw.constants;
const {doubleClickZoom} = MapboxDraw.lib;
const DrawLine = MapboxDraw.modes.draw_line_string;

type LineState = GeometryState & {
  line: MapboxDraw.DrawLineString;
  currentVertexPosition: number;
  selectedFeatures: MapboxDraw.DrawFeature[];
  direction: string;
  snappedLng?: number;
  snappedLat?: number;
  lastVertex?: any;
};

const SnapLineMode = {...DrawLine} as DrawCustomModeWithContext<LineState>;

SnapLineMode.onSetup = function () {
  const line = this.newFeature({
    type: geojsonTypes.FEATURE,
    properties: {},
    geometry: {
      type: geojsonTypes.LINE_STRING,
      coordinates: [[]],
    },
  }) as MapboxDraw.DrawLineString;

  this.addFeature(line);

  const selectedFeatures = this.getSelected();
  this.clearSelectedFeatures();
  doubleClickZoom.disable(this);

  const [snapList, vertices] =
    createSnapList(this.map as any, this._ctx.api, line as any);

  const state: LineState = {
    map: this.map as any,
    line,
    currentVertexPosition: 0,
    vertices,
    snapList,
    selectedFeatures,
    direction: "forward", // expected by DrawLineString
    options: this._ctx.options,
  };

  const moveendCallback = () => {
    const [snapList, vertices] =
      createSnapList(this.map as any, this._ctx.api, line as any);
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

SnapLineMode.onClick = function (state: LineState) {
  // We save some processing by rounding on click, not mousemove
  const lng = state.snappedLng;
  const lat = state.snappedLat;

  if (state.currentVertexPosition > 0) {
    const lastVertex = state.line.coordinates[state.currentVertexPosition - 1];
    state.lastVertex = lastVertex;
    // End the drawing if this click is on the previous position
    // Note: not bothering with "direction"
    if (lastVertex[0] === lng && lastVertex[1] === lat) {
      return this.changeMode(modes.SIMPLE_SELECT, {
        featureIds: [state.line.id],
      });
    }
  }

  // TODO fire add event
  addPointToList(state.map, state.vertices, [lng, lat]);
  state.line.updateCoordinate(state.currentVertexPosition.toString(), lng, lat);
  state.currentVertexPosition++;
  state.line.updateCoordinate(state.currentVertexPosition.toString(), lng, lat);
};

SnapLineMode.onMouseMove = function (state: LineState, e) {
  const {latLng: snapPos, snapped, target} = snap(state, e as any);
  if (!snapPos) {
    return;
  }

  const {lng, lat} = snapPos;
  state.line.updateCoordinate(state.currentVertexPosition.toString(), lng, lat);
  state.snappedLng = lng;
  state.snappedLat = lat;
  let cursor = state.lastVertex && state.lastVertex[0] === lng && state.lastVertex[1] === lat
    ? cursors.POINTER
    : cursors.ADD;
  this.updateUIClasses({mouse: cursor});
};

SnapLineMode.onStop = function (state: LineState) {
  this.map.off("moveend", state.moveendCallback);
  this.map.off("draw.snap.options_changed", state.optionsChangedCallBack);
  DrawLine.onStop.call(this, state);
};

export default SnapLineMode;
