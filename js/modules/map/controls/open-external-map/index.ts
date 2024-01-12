import * as mgl from "maplibre-gl";

import * as helpers from "../helpers";
import "./index.css";

/**
 * Callback for transforming a zoom value.
 *
 * @param {number} zoom The zoom value.
 * @return {any} The transformed zoom value.
 */
export type ZoomTransformer = (zoom: number) => any;

export type OpenExternalMapControlOptions = {
  buttonTitle: string;
  iconUrl: string;
  urlPattern: string;
  zoomMapping?: ZoomTransformer;
};

/**
 * A control that opens the map’s current location in the specified external map.
 */
export default class OpenExternalMapControl implements mgl.IControl {
  #map: mgl.Map;
  readonly #container: HTMLElement;
  readonly #urlPattern: string;
  readonly #zoomTransformer: ZoomTransformer;
  readonly #button: HTMLButtonElement;

  constructor(options?: OpenExternalMapControlOptions) {
    this.#container = helpers.createControlContainer("maplibregl-ctrl-open-location");
    this.#urlPattern = options.urlPattern;
    this.#zoomTransformer = options.zoomMapping ?? ((z: number) => z);
    const icon = document.createElement("img");
    icon.src = options.iconUrl;
    this.#button = helpers.createControlButton({
      title: options.buttonTitle,
      icon: icon,
      onClick: () => this.#onButtonClick(),
    });
  }

  #onButtonClick() {
    const {lat, lng} = this.#map.getCenter();
    const zoom = this.#map.getZoom();
    window.open(this.#urlPattern
      .replace("{lat}", lat.toFixed(5))
      .replace("{lng}", lng.toFixed(5))
      .replace("{zoom}", this.#zoomTransformer(zoom))
    );
  }

  onAdd(map: mgl.Map): HTMLElement {
    this.#map = map;
    this.#container.appendChild(this.#button);
    return this.#container;
  }

  onRemove() {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
