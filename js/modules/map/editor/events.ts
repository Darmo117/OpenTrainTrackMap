import * as geom from "./geometry";

/**
 * Base class for the map editor’s events.
 */
export abstract class MapEditorEvent {
  /**
   * This event’s type. Used by the `Map.fire` and `Map.on` methods.
   */
  readonly type: string;

  /**
   * Create a new event.
   * @param type The event’s type.
   */
  protected constructor(type: string) {
    this.type = type;
  }
}

/**
 * This event is fired when the feature selection changes.
 */
export class FeatureSelectionEvent extends MapEditorEvent {
  /**
   * This event’s type. For the `Map.on` method.
   */
  static readonly TYPE = "editor.selection";

  /**
   * The list of selected features.
   */
  readonly features: geom.MapFeature[];

  /**
   * Create a new event.
   * @param features The selected features.
   */
  constructor(features: geom.MapFeature[] = []) {
    super(FeatureSelectionEvent.TYPE);
    this.features = features;
  }
}

/**
 * This event is fired whenever a feature is hovered.
 */
export class FeatureHoverEvent extends MapEditorEvent {
  /**
   * This event’s type. For the `Map.on` method.
   */
  static readonly TYPE = "editor.hover";

  /**
   * The hovered feature or undefined if there are none.
   */
  readonly feature: geom.MapFeature | undefined;

  /**
   * Create a new event.
   * @param feature The hovered feature.
   */
  constructor(feature?: geom.MapFeature) {
    super(FeatureHoverEvent.TYPE);
    this.feature = feature;
  }
}
