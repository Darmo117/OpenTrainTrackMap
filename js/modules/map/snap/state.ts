import {Map} from "maplibre-gl";
import {DrawFeature} from "@mapbox/mapbox-gl-draw";
import {Feature, Geometries, Position,} from "@turf/helpers";

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
};

export type GeometryState<O = SnapOptions> = State<O> & {
  moveendCallback?: () => void;
};
