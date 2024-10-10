import $ from "jquery";

import { ObjectType } from "../../model/types";
import Component from "./_component";

export interface FeatureTypeButtonConfig {
  onClick: () => void;
}

export default class FeatureTypeButton extends Component {
  readonly #$button: JQuery<HTMLButtonElement>;
  readonly #$buttonIcon: JQuery<HTMLImageElement>;
  readonly #$buttonText: JQuery<HTMLSpanElement>;

  constructor(config: FeatureTypeButtonConfig) {
    super();
    this.#$button = $(
      `<button id="feature-type-btn" class="btn btn-secondary"></button>`,
    );
    this.#$button.on("click", config.onClick);
    // noinspection HtmlRequiredAltAttribute,RequiredAttributes
    this.#$buttonIcon = $("<img>");
    this.#$buttonText = $("<span></span>");
    this.#$button.append(this.#$buttonIcon, this.#$buttonText);
  }

  get disabled(): boolean {
    return !!this.#$button.prop("disabled");
  }

  set disabled(disable: boolean) {
    this.#$button.prop("disabled", disable);
  }

  setFeatureType(type: ObjectType | null): void {
    // TODO set icon
    this.#$buttonText.text(type?.localizedName ?? "");
  }

  setFeatureTypes(types: ObjectType[]): void {
    if (!types.length) {
      this.setFeatureType(null);
    } else {
      // TODO set icon
      const strings = types.map((t) => t.localizedName);
      this.#$buttonText.text([...strings].join(", "));
    }
  }

  get container(): JQuery {
    return this.#$button;
  }

  get visible(): boolean {
    return this.#$button.is(":visible");
  }

  set visible(visible: boolean) {
    if (visible) this.#$button.show();
    else this.#$button.hide();
  }
}
