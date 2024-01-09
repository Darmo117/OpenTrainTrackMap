import {MapMouseEvent} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import {Position} from "@turf/helpers";

import {shallowCopy} from "../../../utils";
import {createSnapList, snap} from "../utils";
import {SnapOptions, State} from "../state";
import {DrawCustomModeWithContext} from "./patch";

const {doubleClickZoom} = MapboxDraw.lib;
const DirectSelect = MapboxDraw.modes.direct_select;

type DirectSelectState = State & {
  /**
   * ID of the currently selected feature.
   */
  featureId: string;
  /**
   * The currently selected feature.
   */
  feature: MapboxDraw.DrawFeature;
  dragMoveLocation: Position | null;
  dragMoving: boolean;
  canDragMove: boolean;
  selectedCoordPaths: string[];
};

// Expose implementation-only methods
interface DirectSelectDrawCustomMode extends DrawCustomModeWithContext<DirectSelectState> {
  dragVertex(state: DirectSelectState, e: MapMouseEvent): void;

  stopDragging(state: DirectSelectState): void;

  pathsToCoordinates(featureId: string, path: string[]): { coord_path: string; feature_id: string }[];
}

const SnapDirectSelect = {...DirectSelect} as DirectSelectDrawCustomMode;

SnapDirectSelect.onSetup = function (options: { featureId: string, startPos: Position, coordPath: string }) {
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
    options: this._ctx.options,
    snappedTo: null,
  };

  this.setSelectedCoordinates(this.pathsToCoordinates(featureId, state.selectedCoordPaths));
  this.setSelected(featureId);
  doubleClickZoom.disable(this);

  this.setActionableState({
    trash: true,
    combineFeatures: false,
    uncombineFeatures: false,
  });

  const optionsChangedCallBack = (options: SnapOptions) => {
    state.options = options;
  };

  // For removing listener later on close
  state.optionsChangedCallBack = optionsChangedCallBack;
  this.map.on("draw.snap.options_changed", optionsChangedCallBack);

  return state;
};

SnapDirectSelect.dragVertex = function (state: DirectSelectState, e: MapMouseEvent) {
  const [snapPos, snapped] = snap(state, e);
  if (snapPos) {
    if (snapped) {
      // Store the position of the vertex we snapped to
      state.snappedTo = shallowCopy(snapPos);
      // TODO store vertex itself
    } else {
      state.snappedTo = null;
    }
    const {lng, lat} = snapPos;
    state.feature.updateCoordinate(state.selectedCoordPaths[0], lng, lat);
    // TODO update coordinates of merged vertices
  }
};

SnapDirectSelect.stopDragging = function (state: DirectSelectState) {
  if (state.snappedTo) {
    // TODO merge points
    console.log("stopDragging", state.snappedTo);
    state.snappedTo = null; // Reset
  }
  (DirectSelect as DirectSelectDrawCustomMode).stopDragging.call(this, state);
};

SnapDirectSelect.onStop = function (state: DirectSelectState) {
  this.map.off("draw.snap.options_changed", state.optionsChangedCallBack);
  DirectSelect.onStop.call(this, state);
};

export default SnapDirectSelect;
