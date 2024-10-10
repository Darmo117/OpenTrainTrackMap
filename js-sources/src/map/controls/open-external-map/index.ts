import { IControl, Map } from "maplibre-gl";

import { createControlButton, createControlContainer } from "../helpers";
import "./_index.css";

/**
 * Callback for transforming a zoom value.
 *
 * @param {number} zoom The zoom value.
 * @return {any} The transformed zoom value.
 */
export type ZoomTransformer = (zoom: number) => string;

/**
 * Options for the {@link OpenExternalMapControl} class.
 */
export interface OpenExternalMapControlOptions {
  /**
   * Title of the control’s button.
   */
  buttonTitle: string;
  /**
   * URL to the icon image to show.
   */
  iconUrl: string;
  /**
   * URL pattern for the target website.
   */
  urlPattern: string;
  /**
   * Optional. A function that transforms the current zoom level before it is passed to the URL pattern.
   */
  zoomMapping?: ZoomTransformer;
}

/**
 * A control that opens the map’s current location in the specified external map.
 */
export default class OpenExternalMapControl implements IControl {
  #map: Map | undefined;
  readonly #container: HTMLElement;
  readonly #urlPattern: string;
  readonly #zoomTransformer: ZoomTransformer;
  readonly #button: HTMLButtonElement;

  constructor(options: OpenExternalMapControlOptions) {
    this.#container = createControlContainer("maplibregl-ctrl-open-location");
    this.#urlPattern = options.urlPattern;
    this.#zoomTransformer = options.zoomMapping ?? Number.toString;
    const icon = document.createElement("img");
    icon.src = options.iconUrl;
    this.#button = createControlButton({
      title: options.buttonTitle,
      icon: icon,
      onClick: () => {
        this.#onButtonClick();
      },
    });
  }

  #onButtonClick(): void {
    if (!this.#map) return;
    const { lat, lng } = this.#map.getCenter();
    const zoom = this.#map.getZoom();
    window.open(
      this.#urlPattern
        .replace("{lat}", lat.toFixed(5))
        .replace("{lng}", lng.toFixed(5))
        .replace("{zoom}", this.#zoomTransformer(zoom)),
    );
  }

  onAdd(map: Map): HTMLElement {
    this.#map = map;
    this.#container.appendChild(this.#button);
    return this.#container;
  }

  onRemove(): void {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
