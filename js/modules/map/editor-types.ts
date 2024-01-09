import {Feature} from "@turf/helpers";

type FeaturesEvent = {
  features: Feature[];
};

export type CreateFeaturesEvent = FeaturesEvent;

export type DeleteFeaturesEvent = FeaturesEvent;

export type SelectionChangedEvent = FeaturesEvent;

export type FeatureUpdateEvent = FeaturesEvent & {
  action: "move" | "change_coordinates";
};

export type SelectionModeChangedEvent = {
  mode: "simple_select" | "direct_select" | "draw_point" | "draw_line_string" | "draw_polygon";
};
