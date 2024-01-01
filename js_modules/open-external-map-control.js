import {controlButton, controlContainer} from "@mapbox-controls/helpers";

/**
 * Callback for transforming a zoom value.
 *
 * @callback transformZoom
 * @param {number} zoom The zoom value.
 * @return {any} The transformed zoom value.
 */

/**
 * @typedef {{
 *  buttonTitle: string,
 *  iconUrl: HTMLElement,
 *  urlPattern: string,
 *  zoomMapping?: transformZoom,
 * }} OpenExternalMapControlOptions
 */

/**
 * Control that opens the map’s current location in the specified external map.
 */
export default class OpenExternalMapControl {
  /**
   * @param {OpenExternalMapControlOptions} options
   */
  constructor(options = {}) {
    this.options = {...options};
    this.container = controlContainer("maplibre-ctrl-open-location");
    this.urlPattern = this.options.urlPattern;
    this.transformZoom = this.options.zoomMapping ?? (z => z);
    const icon = document.createElement("img");
    icon.src = this.options.iconUrl;
    this.button = controlButton({
      title: this.options.buttonTitle,
      icon: icon,
      onClick: () => this.onButtonClick(),
    });
  }

  onButtonClick() {
    const {
      /** @type {number} */
      lat,
      /** @type {number} */
      lng
    } = this.map.getCenter();
    /** @type {number} */
    const zoom = this.map.getZoom();
    window.open(this.urlPattern
      .replace("{lat}", lat.toFixed(5))
      .replace("{lng}", lng.toFixed(5))
      .replace("{zoom}", this.transformZoom(zoom))
    );
  }

  /**
   * @param {import("mapbox-gl").Map} map
   * @returns {HTMLElement}
   */
  onAdd(map) {
    this.map = map;
    this.container.appendChild(this.button);
    return this.container;
  }

  onRemove() {
    this.container.parentNode?.removeChild(this.container);
  }
}
