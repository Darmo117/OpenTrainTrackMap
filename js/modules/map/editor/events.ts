import * as geom from "./geometry";

export abstract class MapEditorEvent {
  readonly type: string;

  protected constructor(type: string) {
    this.type = type;
  }
}

export class FeatureSelectionEvent extends MapEditorEvent {
  static readonly TYPE = "editor.selection";

  readonly features: geom.MapFeature[];

  constructor(features: geom.MapFeature[]) {
    super(FeatureSelectionEvent.TYPE);
    this.features = features;
  }
}

export class FeatureHoverEvent extends MapEditorEvent {
  static readonly TYPE = "editor.hover";

  readonly feature: geom.MapFeature | undefined;

  constructor(feature?: geom.MapFeature) {
    super(FeatureHoverEvent.TYPE);
    this.feature = feature;
  }
}
