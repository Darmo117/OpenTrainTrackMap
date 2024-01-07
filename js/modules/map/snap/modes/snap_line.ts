import MapboxDraw from "@mapbox/mapbox-gl-draw";
import {addPointTovertices, createSnapList, getGuideFeature, IDS, shouldHideGuide, snap,} from "../utils";
import {GeometryState, Options} from "../state";
import {DrawCustomModeWithContext} from "./patch";
import {Feature, Geometries,} from "@turf/helpers";

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

// @ts-ignore
const SnapLineMode: DrawCustomModeWithContext<LineState> = {...DrawLine};

SnapLineMode.onSetup = function () {
  const line = this.newFeature({
    type: geojsonTypes.FEATURE,
    properties: {},
    geometry: {
      type: geojsonTypes.LINE_STRING,
      coordinates: [[]],
    },
  }) as MapboxDraw.DrawLineString;

  const verticalGuide = this.newFeature(getGuideFeature(IDS.VERTICAL_GUIDE));
  const horizontalGuide = this.newFeature(
    getGuideFeature(IDS.HORIZONTAL_GUIDE)
  );

  this.addFeature(line);
  this.addFeature(verticalGuide);
  this.addFeature(horizontalGuide);

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
    verticalGuide,
    horizontalGuide,
    direction: "forward", // expected by DrawLineString
    options: this._ctx.options,
  };

  const moveendCallback = () => {
    const [snapList, vertices] =
      createSnapList(this.map as any, this._ctx.api, line as any);
    state.vertices = vertices;
    state.snapList = snapList;
  };
  // for removing listener later on close
  state.moveendCallback = moveendCallback;

  const optionsChangedCallBack = (options: Options) => {
    state.options = options;
  };
  // for removing listener later on close
  state.optionsChangedCallBack = optionsChangedCallBack;

  this.map.on("moveend", moveendCallback);
  this.map.on("draw.snap.options_changed", optionsChangedCallBack);

  return state;
};

SnapLineMode.onClick = function (state: LineState) {
  // We save some processing by rounding on click, not mousemove
  const lng = state.snappedLng;
  const lat = state.snappedLat;

  // End the drawing if this click is on the previous position
  // Note: not bothering with 'direction'
  if (state.currentVertexPosition > 0) {
    const lastVertex = state.line.coordinates[state.currentVertexPosition - 1];

    state.lastVertex = lastVertex;

    if (lastVertex[0] === lng && lastVertex[1] === lat) {
      return this.changeMode(modes.SIMPLE_SELECT, {
        featureIds: [state.line.id],
      });
    }
  }

  // const point = state.map.project({ lng: lng, lat: lat });

  addPointTovertices(state.map, state.vertices, [lng, lat]);

  state.line.updateCoordinate(state.currentVertexPosition.toString(), lng, lat);

  state.currentVertexPosition++;

  state.line.updateCoordinate(state.currentVertexPosition.toString(), lng, lat);
};

SnapLineMode.onMouseMove = function (state: LineState, e) {
  const snapPos = snap(state, e as any);
  if (!snapPos) {
    return;
  }

  const {lng, lat} = snapPos;
  state.line.updateCoordinate(state.currentVertexPosition.toString(), lng, lat);
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

// This is 'extending' DrawLine.toDisplayFeatures
SnapLineMode.toDisplayFeatures = function (
  state: LineState,
  geojson: Feature<Geometries>,
  display: (geojson: Feature<Geometries>) => void
) {
  if (shouldHideGuide(state, geojson)) {
    return;
  }

  // This relies on the the state of SnapLineMode being similar to DrawLine
  // @ts-ignore
  DrawLine.toDisplayFeatures(state, geojson, display);
};

// This is 'extending' DrawLine.onStop
SnapLineMode.onStop = function (state: LineState) {
  this.deleteFeature(IDS.VERTICAL_GUIDE, {silent: true});
  this.deleteFeature(IDS.HORIZONTAL_GUIDE, {silent: true});

  // remove moveemd callback
  this.map.off("moveend", state.moveendCallback);

  // This relies on the the state of SnapLineMode being similar to DrawLine
  DrawLine.onStop.call(this, state);
};

export default SnapLineMode;
