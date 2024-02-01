import * as mgl from "maplibre-gl";
import $ from "jquery";

import * as st from "../../../streams";
import * as geom from "../../model/geometry";
import * as dtypes from "../../model/data-types";
import * as events from "../_events";
import FeatureTypeButton from "./_feature-type-button";
import "./index.css";

export default class EditorPanel {
  readonly #$panel: JQuery;
  readonly #featureTypeButton: FeatureTypeButton;
  readonly #selectedFeatures: Set<geom.MapFeature> = new Set();
  readonly #dataTypeProvider: geom.DataTypeProvider;

  constructor(map: mgl.Map, dataTypeProvider: geom.DataTypeProvider) {
    this.#dataTypeProvider = dataTypeProvider;
    this.#$panel = $("#editor-panel").show();
    this.#featureTypeButton = new FeatureTypeButton({
      onClick: () => this.#onTypeButtonClick(),
    });
    this.#featureTypeButton.visible = false;
    this.#$panel.append(this.#featureTypeButton.container);
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
    this.#reset();
    if (features.length === 1) {
      this.#setupSingleForm(features[0], editable);
    } else {
      this.#setupMultipleForm(features);
    }
  }

  #reset(): void {
    this.#featureTypeButton.disabled = true;
    this.#setType(null);
    // TODO
  }

  #setupSingleForm(feature: geom.MapFeature, editable: boolean): void {
    const type = feature.dataObject?.type ?? this.#getDefaultType(feature);
    this.#featureTypeButton.disabled = !editable;
    this.#setType(type);
    type.properties.forEach(property => {
      this.#createFieldForProperty(property);
      if (property.isUnique) {
        const value = feature.dataObject?.getPropertyValue(property.label);
        if (value !== null) {
          this.#setFieldValue(property, value);
        }
      } else {
        const values = feature.dataObject?.getPropertyValues(property.label) ?? st.emptyStream();
        this.#setFieldValues(property, values);
      }
    });
  }

  #setupMultipleForm(features: geom.MapFeature[]): void {
    const types = features.map(
        f => f.dataObject?.type ?? this.#getDefaultType(f));
    this.#featureTypeButton.disabled = true;
    this.#featureTypeButton.visible = !!features.length;
    this.#featureTypeButton.setFeatureTypes(types);
    if (features.length) {
      // TODO show only fields common to all features (as non-editable)
    }
  }

  #setType(type: dtypes.ObjectType | null): void {
    this.#featureTypeButton.visible = !!type;
    this.#featureTypeButton.setFeatureType(type);
  }

  #getDefaultType(feature: geom.MapFeature): dtypes.ObjectType {
    return this.#dataTypeProvider(feature.geometry.type.toLowerCase(), "ObjectType");
  }

  #onTypeButtonClick(): void {
    // TODO
    console.log("type button clicked"); // DEBUG
  }

  #createFieldForProperty(property: dtypes.ObjectProperty<unknown>): void {
    console.log("create field for", property.fullName); // DEBUG
    // TODO
  }

  #setFieldValue<T>(property: dtypes.ObjectProperty<T>, value: T): void {
    console.log("set field value for", property.fullName, "to", value); // DEBUG
    // TODO
  }

  #setFieldValues<T>(property: dtypes.ObjectProperty<T>, values: st.Stream<T>) {
    console.log("set field values for", property.fullName, "to", values.toArray()); // DEBUG
    // TODO
  }
}
