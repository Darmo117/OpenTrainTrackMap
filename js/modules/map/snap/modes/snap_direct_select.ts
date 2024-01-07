import {MapMouseEvent} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import {Position} from "@turf/helpers";

import {Dict} from "../../../types";
import {createSnapList, getGuideFeature, IDS, LngLatDict, snap} from "../utils";
import {Options, State} from "../state";
import {DrawCustomModeWithContext} from "./patch";

const {doubleClickZoom} = MapboxDraw.lib;
const DirectSelect = MapboxDraw.modes.direct_select;

type DirectSelectState = State & {
  featureId: number;
  feature: MapboxDraw.DrawFeature;
  dragMoveLocation: Position | null;
  dragMoving: boolean;
  canDragMove: boolean;
  selectedCoordPaths: Position[];
};

interface DirectSelectDrawCustomMode extends DrawCustomModeWithContext<DirectSelectState> {
  // Patch in custom method
  dragVertex(state: DirectSelectState, e: MapMouseEvent): void;

  // Expose implementation-only method
  pathsToCoordinates(featureId: string, path: Position[]): { coord_path: string; feature_id: string }[];
}

// @ts-ignore
const SnapDirectSelect: DirectSelectDrawCustomMode = {...DirectSelect};

SnapDirectSelect.onSetup = function (options: Dict) {
  const featureId = options.featureId;
  const feature = this.getFeature(featureId);

  if (!feature) {
    throw new Error("You must provide a featureId to enter direct_select mode");
  }

  if (feature.type === MapboxDraw.constants.geojsonTypes.POINT) {
    throw new TypeError("direct_select mode doesn't handle point features");
  }

  const [snapList, vertices] =
    createSnapList(this.map as any, this._ctx.api, feature as any);

  const verticalGuide = this.newFeature(getGuideFeature(IDS.VERTICAL_GUIDE));
  const horizontalGuide = this.newFeature(
    getGuideFeature(IDS.HORIZONTAL_GUIDE)
  );

  this.addFeature(verticalGuide);
  this.addFeature(horizontalGuide);

  const state: DirectSelectState = {
    map: this.map as any,
    featureId,
    feature,
    dragMoveLocation: options.startPos || null,
    dragMoving: false,
    canDragMove: false,
    selectedCoordPaths: options.coordPath ? [options.coordPath] : [],
    vertices,
    snapList,
    verticalGuide,
    horizontalGuide,
    options: this._ctx.options,
  };

  this.setSelectedCoordinates(this.pathsToCoordinates(featureId, state.selectedCoordPaths));
  this.setSelected(featureId);
  doubleClickZoom.disable(this);

  this.setActionableState({
    trash: true,
    combineFeatures: false,
    uncombineFeatures: false,
  });

  const optionsChangedCallBack = (options: Options) => {
    state.options = options;
  };

  // for removing listener later on close
  state.optionsChangedCallBack = optionsChangedCallBack;
  this.map.on("draw.snap.options_changed", optionsChangedCallBack);

  return state;
};

SnapDirectSelect.dragVertex = function (state: DirectSelectState, e: MapMouseEvent) {
  const snapPos = snap(state, e);
  if (snapPos) {
    const {lng, lat} = snapPos as LngLatDict;
    state.feature.updateCoordinate(state.selectedCoordPaths[0].toString(), lng, lat);
  }
};

SnapDirectSelect.onStop = function (state: DirectSelectState) {
  this.deleteFeature(IDS.VERTICAL_GUIDE, {silent: true});
  this.deleteFeature(IDS.HORIZONTAL_GUIDE, {silent: true});

  // remove moveemd callback
  //   this.map.off("moveend", state.moveendCallback);
  this.map.off("draw.snap.options_changed", state.optionsChangedCallBack);

  // This relies on the the state of SnapPolygonMode being similar to DrawPolygon
  DirectSelect.onStop.call(this, state);
};

export default SnapDirectSelect;
