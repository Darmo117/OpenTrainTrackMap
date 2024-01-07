import {controlButton, controlContainer} from "@mapbox-controls/helpers";
import {IControl, Map} from "maplibre-gl";

/**
 * Callback for transforming a zoom value.
 *
 * @param {number} zoom The zoom value.
 * @return {any} The transformed zoom value.
 */
export type ZoomTransformer = (zoom: number) => any

export type OpenExternalMapControlOptions = {
  buttonTitle: string,
  iconUrl: string,
  urlPattern: string,
  zoomMapping?: ZoomTransformer,
}

/**
 * Control that opens the map’s current location in the specified external map.
 */
export default class OpenExternalMapControl implements IControl {
  readonly #container: HTMLElement;
  readonly #urlPattern: string;
  readonly #zoomTransformer: ZoomTransformer;
  readonly #button: HTMLButtonElement;
  #map: Map;

  constructor(options?: OpenExternalMapControlOptions) {
    this.#container = controlContainer("maplibre-ctrl-open-location");
    this.#urlPattern = options.urlPattern;
    this.#zoomTransformer = options.zoomMapping ?? ((z: number) => z);
    const icon = document.createElement("img");
    icon.src = options.iconUrl;
    this.#button = controlButton({
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

  onAdd(map: Map): HTMLElement {
    this.#map = map;
    this.#container.appendChild(this.#button);
    return this.#container;
  }

  onRemove() {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
