import {IControl, Map} from "maplibre-gl";

import {createControlButton, createControlContainer, parseSVG} from "../helpers";

const ICON = parseSVG(`
<svg viewBox="0 0 24 24" width="22" height="22" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" fill-rule="evenodd">
    <path d="M0 0h24v24H0z"/>
    <path fill="#f44336" d="M12 3l4 8H8z"/>
    <path fill="#9E9E9E" d="M12 21l-4-8h8z"/>
  </g>
</svg>
`);

export type CompassControlOptions = {
  /**
   * The control’s title.
   */
  title?: string;
  /**
   * If true, the bearing/pitch reset will be instantaneous and the controll will always be shown.
   */
  instant?: boolean;
};

/**
 * A control that indicates the current bearing when the map is rotated.
 * Clicking this control will reset both the bearing and pitch to 0°.
 */
export default class CompassControl implements IControl {
  #map: Map;
  readonly #options: CompassControlOptions;
  readonly #container: HTMLDivElement;
  readonly #button: HTMLButtonElement;
  readonly #icon: SVGElement;

  constructor(options: CompassControlOptions = {}) {
    this.#options = {...options};
    this.#container = createControlContainer("maplibregl-ctrl-compass");
    this.#icon = ICON;
    this.#button = createControlButton({
      title: this.#options.title ?? "Compass",
      icon: ICON,
      onClick: () => this.#onControlButtonClick(),
    });
  }

  #onControlButtonClick() {
    if (!this.#map) {
      throw Error("map is undefined");
    }
    this.#map.easeTo({bearing: 0, pitch: 0});
  }

  #onRotate() {
    if (!this.#map) {
      throw Error("map is undefined");
    }
    const angle = -this.#map.getBearing();
    if (!this.#options.instant) {
      this.#container.hidden = angle === 0;
    }
    this.#icon.style.transform = `rotate(${angle}deg)`;
  }

  onAdd(map: Map): HTMLElement {
    this.#map = map;
    if (!this.#options.instant) {
      this.#container.hidden = true;
    }
    this.#container.appendChild(this.#button);
    this.#onRotate();
    this.#map.on("rotate", () => this.#onRotate());
    return this.#container;
  }

  onRemove() {
    this.#container.parentNode?.removeChild(this.#container);
  }
}