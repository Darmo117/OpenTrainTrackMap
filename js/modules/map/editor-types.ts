import {Feature, LineString, Point, Polygon} from "@turf/helpers";

export type ValidGeometry = Point | LineString | Polygon;

type FeaturesEvent = {
  features: Feature<ValidGeometry>[];
};

export type CreateFeaturesEvent = FeaturesEvent;

export type DeleteFeaturesEvent = FeaturesEvent;

export type SelectionChangedEvent = FeaturesEvent;

export type FeatureUpdateEvent = FeaturesEvent & {
  action: "move" | "change_coordinates";
};

export type ModeChangedEvent = {
  mode: "simple_select" | "direct_select" | "draw_point" | "draw_line_string" | "draw_polygon";
};
