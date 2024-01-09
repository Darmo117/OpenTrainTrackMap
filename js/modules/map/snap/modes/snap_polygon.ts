import MapboxDraw from "@mapbox/mapbox-gl-draw";
import booleanIntersects from "@turf/boolean-intersects";
import {Feature, Polygon,} from "@turf/helpers";
import * as turf from "@turf/turf";

import {addPointToList, createSnapList, snap} from "../utils";
import {GeometryState, SnapOptions} from "../types";
import {DrawCustomModeWithContext} from "./patch";

const {geojsonTypes, modes, cursors} = MapboxDraw.constants;
const {doubleClickZoom} = MapboxDraw.lib;
const DrawPolygon = MapboxDraw.modes.draw_polygon;

type PolygonOptions = SnapOptions & {
  overlap: boolean;
};

type PolygonState = GeometryState<PolygonOptions> & {
  polygon: MapboxDraw.DrawPolygon;
  currentVertexPosition: number;
  selectedFeatures: MapboxDraw.DrawFeature[];
  snappedLng?: number;
  snappedLat?: number;
  lastVertex?: any;
};

const SnapPolygonMode = {...DrawPolygon} as DrawCustomModeWithContext<PolygonState, PolygonOptions>;

SnapPolygonMode.onSetup = function () {
  const polygon = this.newFeature({
    type: geojsonTypes.FEATURE,
    properties: {},
    geometry: {
      type: geojsonTypes.POLYGON,
      coordinates: [[]],
    },
  }) as MapboxDraw.DrawPolygon;

  this.addFeature(polygon);

  const selectedFeatures = this.getSelected();
  this.clearSelectedFeatures();
  doubleClickZoom.disable(this);

  const [snapList, vertices] =
    createSnapList(this.map as any, this._ctx.api, polygon as any);

  const state: PolygonState = {
    map: this.map as any,
    polygon,
    currentVertexPosition: 0,
    vertices,
    snapList,
    selectedFeatures,
    // Adding default options
    options: Object.assign(this._ctx.options, {overlap: true}),
  };

  const moveendCallback = () => {
    const [snapList, vertices] = createSnapList(
      this.map as any,
      this._ctx.api,
      polygon as any
    );
    state.vertices = vertices;
    state.snapList = snapList;
  };
  state.moveendCallback = moveendCallback;

  const optionsChangedCallBack = (options: PolygonOptions) => {
    state.options = options;
  };
  state.optionsChangedCallBack = optionsChangedCallBack;

  this.map.on("moveend", moveendCallback);
  this.map.on("draw.snap.options_changed", optionsChangedCallBack);

  return state;
};

SnapPolygonMode.onClick = function (state: PolygonState) {
  // We save some processing by rounding on click, not mousemove
  const lng = state.snappedLng;
  const lat = state.snappedLat;

  if (state.currentVertexPosition > 0) {
    const lastVertex = state.polygon.coordinates[0][state.currentVertexPosition - 1];
    state.lastVertex = lastVertex;
    // End the drawing if this click is on the previous position
    if (lastVertex[0] === lng && lastVertex[1] === lat) {
      return this.changeMode(modes.SIMPLE_SELECT, {
        featureIds: [state.polygon.id],
      });
    }
  }

  // TODO fire add event
  addPointToList(state.map, state.vertices, [lng, lat]);
  state.polygon.updateCoordinate(`0.${state.currentVertexPosition}`, lng, lat);
  state.currentVertexPosition++;
  state.polygon.updateCoordinate(`0.${state.currentVertexPosition}`, lng, lat);
};

SnapPolygonMode.onMouseMove = function (state: PolygonState, e) {
  const {latLng: snapPos, snapped, target} = snap(state, e as any);
  if (!snapPos) {
    return;
  }

  const {lng, lat} = snapPos;
  state.polygon.updateCoordinate(`0.${state.currentVertexPosition}`, lng, lat);
  state.snappedLng = lng;
  state.snappedLat = lat;
  let cursor = state.lastVertex && state.lastVertex[0] === lng && state.lastVertex[1] === lat
    ? cursors.POINTER
    : cursors.ADD;
  this.updateUIClasses({mouse: cursor});
};

SnapPolygonMode.onStop = function (state: PolygonState) {
  this.map.off("moveend", state.moveendCallback);
  this.map.off("draw.snap.options_changed", state.optionsChangedCallBack);

  const userPolygon = state.polygon;
  if (state.options.overlap) {
    DrawPolygon.onStop.call(this, state);
    return;
  }
  // If overlap is false, mutate polygon so it doesn’t overlap with existing ones
  // get all editable features to check for intersections
  const features: Feature<Polygon>[] = this._ctx.store.getAll();

  try {
    let edited: Feature<Polygon> | MapboxDraw.DrawPolygon = userPolygon;
    features.forEach(function (feature) {
      if (userPolygon.id === feature.id) {
        return;
      }
      if (!booleanIntersects(feature, edited)) {
        return;
      }
      edited = turf.difference(edited, feature) as Feature<Polygon>;
    });
    // Convert to any as "coordinates" property is readonly in TS definition
    (state.polygon as any).coordinates =
      edited.coordinates || (edited as unknown as Feature<Polygon>).geometry.coordinates;
  } catch (e) {
    // Cancel this polygon if a difference cannot be calculated
    DrawPolygon.onStop.call(this, state);
    this.deleteFeature(state.polygon.id as string, {silent: true});
    return;
  }

  // Monkeypatch so DrawPolygon.onStop doesn’t error
  const rc = state.polygon.removeCoordinate;
  state.polygon.removeCoordinate = () => {
  };
  DrawPolygon.onStop.call(this, state);
  state.polygon.removeCoordinate = rc.bind(state.polygon);
};

export default SnapPolygonMode;
