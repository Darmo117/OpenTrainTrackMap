import {Map} from "maplibre-gl";
import {DrawFeature} from "@mapbox/mapbox-gl-draw";
import {Feature, Geometries, Position,} from "@turf/helpers";
import {LngLatDict} from "./utils";

export type SnapSubOptions = {
  snapPx?: number;
  snapToMidPoints?: boolean;
  snapVertexPriorityDistance?: number;
  overlap?: boolean;
};

export type SnapOptions = {
  snap?: boolean;
  snapOptions?: SnapSubOptions;
  guides?: boolean;
};

export type State<O = SnapOptions> = {
  map: Map;
  vertices: Position[];
  snapList: Feature<Geometries>[];
  verticalGuide: DrawFeature;
  horizontalGuide: DrawFeature;
  options: O;
  optionsChangedCallBack?: (options: O) => void;
  showVerticalSnapLine?: boolean;
  showHorizontalSnapLine?: boolean;
  /**
   * The vertex the one being dragged has been snapped to.
   */
  snappedTo: LngLatDict | null;
};

export type GeometryState<O = SnapOptions> = State<O> & {
  moveendCallback?: () => void;
};
