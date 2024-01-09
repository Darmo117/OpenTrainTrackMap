import {Map} from "maplibre-gl";
import {Feature, Position} from "@turf/helpers";

import {ValidGeometry} from "../editor-types";

export type SnapSubOptions = {
  snapPx?: number;
  snapToMidPoints?: boolean;
  snapVertexPriorityDistance?: number;
  overlap?: boolean;
};

export type SnapOptions = {
  snap?: boolean;
  snapOptions?: SnapSubOptions;
};

export type State<O = SnapOptions> = {
  map: Map;
  vertices: Position[];
  snapList: Feature<ValidGeometry>[];
  options: O;
  optionsChangedCallBack?: (options: O) => void;
  /**
   * The vertex the one being dragged has been snapped to.
   */
  snappedTo?: {
    feature: Feature<ValidGeometry>,
    path: string,
  };
};

export type GeometryState<O = SnapOptions> = State<O> & {
  moveendCallback?: () => void;
};
