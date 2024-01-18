import * as mgl from "maplibre-gl";

import Map from "../../map";
import * as helpers from "../helpers";
import $ from "jquery";

const PLUS_ICON = helpers.parseSVG(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
  <rect fill="none" height="24" width="24"/>
  <path d="M18,13h-5v5c0,0.55-0.45,1-1,1l0,0c-0.55,0-1-0.45-1-1v-5H6c-0.55,0-1-0.45-1-1l0,0c0-0.55,0.45-1,1-1h5V6 c0-0.55,0.45-1,1-1l0,0c0.55,0,1,0.45,1,1v5h5c0.55,0,1,0.45,1,1l0,0C19,12.55,18.55,13,18,13z"/>
</svg>
`);
const MINUS_ICON = helpers.parseSVG(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
  <rect fill="none" height="24" width="24"/>
  <path d="M18,13H6c-0.55,0-1-0.45-1-1l0,0c0-0.55,0.45-1,1-1h12c0.55,0,1,0.45,1,1l0,0C19,12.55,18.55,13,18,13z"/>
</svg>
`);

/**
 * Options for the {@link ZoomControl} class.
 */
export type ZoomControlOptions = {
  /**
   * Optional. Title of the "Zoom In" button.
   */
  zoomInTitle?: string;
  /**
   * Optional. Title of the "Zoom Out" button.
   */
  zoomOutTitle?: string;
};

/**
 * A control that adds a button to zoom in and another to zoom out the map.
 */
export default class ZoomControl implements mgl.IControl {
  #map: mgl.Map;
  readonly #container: HTMLDivElement;
  readonly #buttonIn: HTMLButtonElement;
  readonly #buttonOut: HTMLButtonElement;

  constructor(options: ZoomControlOptions = {}) {
    this.#container = helpers.createControlContainer("maplibregl-ctrl-zoom");
    this.#buttonIn = helpers.createControlButton({
      title: options.zoomInTitle ?? "Zoom In",
      icon: PLUS_ICON,
      onClick: () => this.#map.zoomIn(),
      shortcut: ["+"],
    });
    this.#buttonOut = helpers.createControlButton({
      title: options.zoomOutTitle ?? "Zoom Out",
      icon: MINUS_ICON,
      onClick: () => this.#map.zoomOut(),
      shortcut: ["-"],
    });
  }

  /**
   * Set whether the "Zoom In" button should be disabled.
   * @param disable True to disable, false to enable.
   */
  setZoomInButtonDisabled(disable: boolean): void {
    this.#buttonIn.disabled = disable;
  }

  /**
   * Set whether the "Zoom Out" button should be disabled.
   * @param disable True to disable, false to enable.
   */
  setZoomOutButtonDisabled(disable: boolean): void {
    this.#buttonOut.disabled = disable;
  }

  onAdd(map: mgl.Map): HTMLElement {
    this.#map = map;
    this.#container.appendChild(this.#buttonIn);
    this.#container.appendChild(this.#buttonOut);
    $(this.#map.getContainer()).on("keydown", e => {
      if (this.#map instanceof Map && this.#map.textFieldHasFocus) {
        return;
      }
      switch (e.key) {
        case "+":
          this.#map.zoomIn();
          break;
        case "-":
          this.#map.zoomOut();
          break;
      }
    });
    return this.#container;
  }

  onRemove(): void {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
