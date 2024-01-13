import * as mgl from "maplibre-gl";

import * as helpers from "../controls/helpers";

/**
 * Options for the {@link DrawControl} class.
 */
export type DrawControlOptions = {
  /**
   * Callback for when the "Draw Point" button is clicked.
   */
  onDrawPoint: () => void;
  /**
   * Callback for when the "Draw Line" button is clicked.
   */
  onDrawLine: () => void;
  /**
   * Callback for when the "Draw Area" button is clicked.
   */
  onDrawPolygon: () => void;
  /**
   * The title of the "Draw Point" button.
   */
  drawPointButtonTitle?: string;
  /**
   * The title of the "Draw Line" button.
   */
  drawLineButtonTitle?: string;
  /**
   * The title of the "Draw Area" button.
   */
  drawPolygonButtonTitle?: string;
};

/**
 * A control that indicates the current bearing when the map is rotated.
 * Clicking this control will reset both the bearing and pitch to 0°.
 */
export default class DrawControl implements mgl.IControl {
  readonly #container: HTMLDivElement;
  readonly #buttons: HTMLButtonElement[] = [];

  constructor(options: DrawControlOptions) {
    this.#container = helpers.createControlContainer("maplibregl-ctrl-draw");
    this.#buttons.push(helpers.createControlButton({
      title: options.drawPointButtonTitle ?? "Draw Point",
      // icon: icon,
      onClick: () => options.onDrawPoint(),
    }));
    this.#buttons.push(helpers.createControlButton({
      title: options.drawLineButtonTitle ?? "Draw Line",
      // icon: icon,
      onClick: () => options.onDrawLine(),
    }));
    this.#buttons.push(helpers.createControlButton({
      title: options.drawPolygonButtonTitle ?? "Draw Area",
      // icon: icon,
      onClick: () => options.onDrawPolygon(),
    }));
  }

  onAdd(_: mgl.Map): HTMLElement {
    this.#container.append(...this.#buttons);
    return this.#container;
  }

  onRemove() {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
