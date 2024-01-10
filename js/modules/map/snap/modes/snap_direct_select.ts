import {MapMouseEvent} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import {Position} from "@turf/helpers";
import {createSnapList, snap} from "../utils";
import {SnapOptions, State} from "../types";
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

// Expose some implementation-only methods
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
    throw new TypeError("Direct_select mode doesn’t handle point features");
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
  };
  // FIXME lost when feature is deselected
  (feature as any).mergedVertices = {};

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
  // TODO remove bound features from snap list
  const {latLng: snapPos, snapped, target} = snap(state, e);
  if (snapPos) {
    if (snapped) {
      // Store the position and vertex we snapped to
      state.snappedTo = {
        latLng: snapPos,
        feature: target.feature,
        vertexIndex: target.vertexIndex,
      };
    } else {
      state.snappedTo = null;
    }
    const {lng, lat} = snapPos;
    const path = state.selectedCoordPaths[0];
    state.feature.updateCoordinate(path, lng, lat);
    if ((state.feature as any).mergedVertices[path]) {
      // Update coordinates of merged vertices
      for (const {feature, vertexIndex} of (state.feature as any).mergedVertices[path]) {
        if (vertexIndex === null) {
          continue;
        }
        if (feature.geometry.type === "Point") {
          feature.geometry.coordinates[0] = lng;
          feature.geometry.coordinates[1] = lat;
        } else if (feature.geometry.type === "LineString") {
          feature.geometry.coordinates[vertexIndex][0] = lng;
          feature.geometry.coordinates[vertexIndex][1] = lat;
        } else if (feature.geometry.type === "Polygon") {
          feature.geometry.coordinates[0][vertexIndex][0] = lng;
          feature.geometry.coordinates[0][vertexIndex][1] = lat;
        }
        this._ctx.api.add(feature); // Re-render feature
      }
    }
  }
};

SnapDirectSelect.stopDragging = function (state: DirectSelectState) {
  if (state.snappedTo) {
    console.log("stopDragging", state.snappedTo); // DEBUG
    if (state.snappedTo.vertexIndex !== null || state.snappedTo.feature.geometry.type === "Point") {
      // Merge the dragged vertex with the one(s) it snapped to
      const path = state.selectedCoordPaths[0];
      if (!(state.feature as any).mergedVertices[path]) {
        (state.feature as any).mergedVertices[path] = [];
      }
      (state.feature as any).mergedVertices[path].push({
        feature: state.snappedTo.feature,
        vertexIndex: state.snappedTo.vertexIndex,
      });
    } else {
      // TODO create a new point on the target feature at the snap location
    }
    state.snappedTo = null; // Reset
  }
  (DirectSelect as DirectSelectDrawCustomMode).stopDragging.call(this, state);
};

SnapDirectSelect.onStop = function (state: DirectSelectState) {
  this.map.off("draw.snap.options_changed", state.optionsChangedCallBack);
  DirectSelect.onStop.call(this, state);
};

export default SnapDirectSelect;
