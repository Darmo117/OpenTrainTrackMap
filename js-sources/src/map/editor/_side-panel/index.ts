import { Map } from "maplibre-gl";
import $ from "jquery";

import { DataTypeProvider, MapFeature } from "../../model/geometry";
import { ObjectProperty, ObjectType } from "../../model/types";
import { FeatureHoverEvent, FeatureSelectionEvent } from "../_events";
import FeatureTypeButton from "./_feature-type-button";

import "./index.css";

export default class EditorPanel {
  readonly #$panel: JQuery;
  readonly #featureTypeButton: FeatureTypeButton;
  readonly #selectedFeatures = new Set<MapFeature>();
  readonly #dataTypeProvider: DataTypeProvider;

  constructor(map: Map, dataTypeProvider: DataTypeProvider) {
    this.#dataTypeProvider = dataTypeProvider;
    this.#$panel = $("#editor-panel").show();
    this.#featureTypeButton = new FeatureTypeButton({
      onClick: () => {
        this.#onTypeButtonClick();
      },
    });
    this.#featureTypeButton.visible = false;
    this.#$panel.append(this.#featureTypeButton.container);
    map.on(FeatureSelectionEvent.TYPE, (e: FeatureSelectionEvent) => {
      this.#selectedFeatures.clear();
      e.features.forEach((f) => this.#selectedFeatures.add(f));
      this.#setupForm(e.features, true);
    });
    map.on(FeatureHoverEvent.TYPE, (e: FeatureHoverEvent) => {
      if (!this.#selectedFeatures.size) {
        this.#setupForm(e.feature ? [e.feature] : [], false);
      }
    });
  }

  getContainer(): JQuery {
    return this.#$panel;
  }

  #setupForm(features: MapFeature[], editable: boolean): void {
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

  #setupSingleForm(feature: MapFeature, editable: boolean): void {
    const type = feature.dataObject?.type ?? this.#getDefaultType(feature);
    this.#featureTypeButton.disabled = !editable;
    this.#setType(type);
    type.properties.forEach((property) => {
      this.#createFieldForProperty(property);
      if (property.isUnique) {
        const value = feature.dataObject?.getPropertyValue(property.label);
        if (value !== null) {
          this.#setFieldValue(property, value);
        }
      } else {
        const values =
          feature.dataObject?.getPropertyValues(property.label) ?? [];
        this.#setFieldValues(property, values);
      }
    });
  }

  #setupMultipleForm(features: MapFeature[]): void {
    const types = features.map(
      (f) => f.dataObject?.type ?? this.#getDefaultType(f),
    );
    this.#featureTypeButton.disabled = true;
    this.#featureTypeButton.visible = !!features.length;
    this.#featureTypeButton.setFeatureTypes(types);
    if (features.length) {
      // TODO show only fields common to all features (as non-editable)
    }
  }

  #setType(type: ObjectType | null): void {
    this.#featureTypeButton.visible = !!type;
    this.#featureTypeButton.setFeatureType(type);
  }

  #getDefaultType(feature: MapFeature): ObjectType {
    return this.#dataTypeProvider(
      feature.geometry.type.toLowerCase(),
      "ObjectType",
    );
  }

  #onTypeButtonClick(): void {
    // TODO
    console.log("type button clicked"); // DEBUG
  }

  #createFieldForProperty(property: ObjectProperty<unknown>): void {
    console.log("create field for", property.fullName); // DEBUG
    // TODO
  }

  #setFieldValue<T>(property: ObjectProperty<T>, value: T): void {
    console.log("set field value for", property.fullName, "to", value); // DEBUG
    // TODO
  }

  #setFieldValues<T>(property: ObjectProperty<T>, values: T[]) {
    console.log("set field values for", property.fullName, "to", values); // DEBUG
    // TODO
  }
}
