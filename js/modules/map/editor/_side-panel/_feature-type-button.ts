import * as st from "../../../streams";
import * as dtypes from "../../model/data-types";
import Component from "./_component";

export type FeatureTypeButtonConfig = {
  onClick: () => void;
};

export default class FeatureTypeButton implements Component {
  readonly #button: HTMLButtonElement;
  readonly #buttonIcon: HTMLImageElement;
  readonly #buttonText: HTMLSpanElement;

  constructor(config: FeatureTypeButtonConfig) {
    this.#button = document.createElement("button");
    this.#button.id = "feature-type-btn";
    this.#button.classList.add("btn", "btn-secondary");
    this.#button.onclick = config.onClick;
    this.#buttonIcon = document.createElement("img");
    this.#buttonText = document.createElement("span");
    this.#button.append(this.#buttonIcon, this.#buttonText);
  }

  get disabled(): boolean {
    return this.#button.disabled;
  }

  set disabled(disable: boolean) {
    this.#button.disabled = disable;
  }

  // TODO type icons
  setFeatureType(type: dtypes.ObjectType | null): void {
    this.#buttonText.textContent = type?.localizedName ?? "";
  }

  setFeatureTypes(types: dtypes.ObjectType[]): void {
    if (!types.length) {
      this.setFeatureType(null);
    }
    this.#buttonText.textContent = st.stream(types)
        .map(t => t.localizedName)
        .distinct()
        .reduce("", (r, e) => r ? r + ", " + e : e);
  }

  get container(): HTMLElement {
    return this.#button;
  }

  get visible(): boolean {
    return this.#button.style.display !== "none";
  }

  set visible(visible: boolean) {
    this.#button.style.display = visible ? "block" : "none";
  }
}
