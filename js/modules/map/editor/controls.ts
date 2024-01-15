import * as mgl from "maplibre-gl";
import $ from "jquery";

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
 * A control that shows 3 buttons to draw points, lines and polygons.
 * When a button is clicked, it remains active until the {@link deactivateButton} method is called
 * for that button’s index. Indices are the following:
 * * 0: draw point button
 * * 1: draw line button
 * * 2: draw polygon button
 */
export default class DrawControl implements mgl.IControl {
  readonly #container: HTMLDivElement;
  readonly #buttons: HTMLButtonElement[] = [];

  constructor(options: DrawControlOptions) {
    this.#container = helpers.createControlContainer("maplibregl-ctrl-draw");
    this.#buttons.push(helpers.createControlButton({
      title: (options.drawPointButtonTitle ?? "Draw Point") + " [1]",
      icon: helpers.createMdiIcon("map-marker-outline"),
      onClick: button => {
        button.classList.add("active");
        options.onDrawPoint();
      },
    }));
    this.#buttons.push(helpers.createControlButton({
      title: (options.drawLineButtonTitle ?? "Draw Line") + " [2]",
      icon: helpers.createMdiIcon("vector-line"),
      onClick: button => {
        button.classList.add("active");
        options.onDrawLine();
      },
    }));
    this.#buttons.push(helpers.createControlButton({
      title: (options.drawPolygonButtonTitle ?? "Draw Area") + " [3]",
      icon: helpers.createMdiIcon("vector-square"),
      onClick: button => {
        button.classList.add("active");
        options.onDrawPolygon();
      },
    }));
    $("body").on("keydown", e => {
      const key = +e.key - 1;
      if (key >= 0 && key < this.#buttons.length) {
        this.#buttons[key].click();
      }
    });
  }

  /**
   * Deactivate the button at the given index.
   * @param index The button’s index. Should be between 0 and 3 inclusive.
   */
  deactivateButton(index: number): void {
    this.#buttons[index]?.classList.remove("active");
  }

  /**
   * Disable/Enable the button at the given index.
   * @param index The button’s index. Should be between 0 and 3 inclusive.
   * @param disabled True to disable the button, false to enable it.
   */
  setButtonDisabled(index: number, disabled: boolean): void {
    if (this.#buttons[index]) {
      this.#buttons[index].disabled = disabled;
    }
  }

  onAdd(_: mgl.Map): HTMLElement {
    this.#container.append(...this.#buttons);
    return this.#container;
  }

  onRemove(): void {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
