import {Map} from "maplibre-gl";
import {DrawFeature} from "@mapbox/mapbox-gl-draw";
import {Feature, Geometries, Position,} from "@turf/helpers";

export type SnapOptions = {
  snapPx?: number;
  snapToMidPoints?: boolean;
  snapVertexPriorityDistance?: number;
  overlap?: boolean;
};

export type Options = {
  snap?: boolean;
  snapOptions?: SnapOptions;
  guides?: boolean;
};

export type State<O = Options> = {
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

export type GeometryState<O = Options> = State<O> & {
  moveendCallback?: () => void;
};
