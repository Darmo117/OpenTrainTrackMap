import * as geom from "./geometry";
import * as mgl from "maplibre-gl";
import $ from "jquery";
import * as events from "./events";

export default class EditorPanel {
  readonly #$sidePanel: JQuery;
  readonly #$featureType: JQuery;
  readonly #selectedFeatures: Set<geom.MapFeature> = new Set();

  constructor(map: mgl.Map) {
    this.#$sidePanel = $("#editor-panel").show().addClass("split");
    this.#$sidePanel.append(this.#$featureType = $('<h1 id="feature-type"></h1>'));
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

  #setupForm(features: geom.MapFeature[], editable: boolean): void {
    if (!features.length) {
      this.#$featureType.text("");
    } else {
      this.#$featureType.text(features.map(f => f.id).join(", ")); // TEMP
      // TODO setup edit form
    }
  }

  getContainer(): HTMLElement {
    return this.#$sidePanel[0];
  }
}
