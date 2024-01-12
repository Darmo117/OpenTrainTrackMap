import {MapFeature} from "./geometry";

export abstract class MapEditorEvent {
  readonly type: string;

  protected constructor(type: string) {
    this.type = type;
  }
}

export class FeatureSelectionEvent extends MapEditorEvent {
  static readonly TYPE = "editor.selection";

  readonly features: MapFeature[];

  constructor(features: MapFeature[]) {
    super(FeatureSelectionEvent.TYPE);
    this.features = features;
  }
}

export class FeatureHoverEvent extends MapEditorEvent {
  static readonly TYPE = "editor.hover";

  readonly feature: MapFeature | undefined;

  constructor(feature?: MapFeature) {
    super(FeatureHoverEvent.TYPE);
    this.feature = feature;
  }
}
