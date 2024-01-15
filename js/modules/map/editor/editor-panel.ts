import * as mgl from "maplibre-gl";
import $ from "jquery";

import * as geom from "./geometry";
import * as events from "./events";

export default class EditorPanel {
  readonly #$panel: JQuery;
  readonly #$featureTypeLabel: JQuery;
  readonly #selectedFeatures: Set<geom.MapFeature> = new Set();

  constructor(map: mgl.Map) {
    this.#$panel = $("#editor-panel").show();
    this.#$panel.append(this.#$featureTypeLabel = $('<h1 id="feature-type"></h1>'));
    map.on(events.FeatureSelectionEvent.TYPE, (e: events.FeatureSelectionEvent) => {
      this.#selectedFeatures.clear();
      e.features.forEach(f => this.#selectedFeatures.add(f));
      this.#setupForm(e.features, true);
    });
    map.on(events.FeatureHoverEvent.TYPE, (e: events.FeatureHoverEvent) => {
      if (!this.#selectedFeatures.size) {
        this.#setupForm(e.feature ? [e.feature] : [], false);
      }
    });
  }

  getContainer(): JQuery {
    return this.#$panel;
  }

  #setupForm(features: geom.MapFeature[], editable: boolean): void {
    if (!features.length) {
      this.#$featureTypeLabel.text("");
    } else {
      this.#$featureTypeLabel.text(features.map(f => f.id).join(", ")); // TEMP
      // TODO setup edit form
    }
  }
}
