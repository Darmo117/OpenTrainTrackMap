import {IControl, Map, MapLibreEvent} from "maplibre-gl";
import {RasterSourceSpecification} from "@maplibre/maplibre-gl-style-spec";

import {createControlButton, createControlContainer, parseSVG} from "../helpers";
import "./index.css";

const ICON = parseSVG(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="22" height="22" fill="currentColor">
  <path d="m24 41.5-18-14 2.5-1.85L24 37.7l15.5-12.05L42 27.5Zm0-7.6-18-14 18-14 18 14Zm0-15.05Zm0 11.25 13.1-10.2L24 9.7 10.9 19.9Z"/>
</svg>
`);

export type TilesChangedEvent = MapLibreEvent & {
  source: TilesSource;
};

export type TilesSource = {
  /**
   * Display-name of the tiles source.
   */
  label: string;
  /**
   * Internal ID of the style.
   */
  id: string;
  /**
   * A MapLibre raster tiles source specification object.
   */
  source: RasterSourceSpecification;
};

export type TilesSourcesControlOptions = {
  /**
   * List of styles to show in the control.
   */
  sources: TilesSource[];
  /**
   * Title of the control. Ignored if `compact` is `false`.
   */
  title?: string;
};

/**
 * A control that allows switching between multiple tiles sources.
 */
export default class TilesSourcesControl implements IControl {
  #map: Map;
  readonly #options: TilesSourcesControlOptions;
  readonly #container: HTMLDivElement;

  constructor(options: TilesSourcesControlOptions) {
    this.#options = {...options};
    this.#container = createControlContainer("maplibregl-ctrl-tiles-sources");
  }

  #findTilesSourceById(id: string): TilesSource {
    const tilesSource = this.#options.sources.find(source => source.id === id);
    if (!tilesSource) {
      throw Error(`Can’t find tiles source with ID ${id}`);
    }
    return tilesSource;
  }

  #setup() {
    if (!this.#map) {
      throw Error("map is undefined");
    }
    const button = createControlButton({
      title: this.#options.title ?? "Backgrounds",
      icon: ICON,
    });
    this.#container.appendChild(button);
    // FIXME select extends outside of button
    const select = document.createElement("select");
    button.appendChild(select);

    this.#options.sources.forEach(style => {
      const option = document.createElement("option");
      select.appendChild(option);
      option.textContent = style.label;
      option.value = style.id;
    });

    select.addEventListener("change", () => {
      if (!this.#map) {
        throw Error("map is undefined");
      }
      this.#changeTilesSource(this.#findTilesSourceById(select.value));
    });

    this.#map.on("styledata", () => {
      if (!this.#map) {
        throw Error("map is undefined");
      }
      const styleName = this.#map.getStyle().name;
      if (!styleName) {
        throw Error("Style must have name");
      }
      select.value = styleName;
    });
  }

  #changeTilesSource(source: TilesSource) {
    this.#map.removeLayer("tiles");
    this.#map.removeSource("tiles");
    this.#map.addSource("tiles", source.source);
    this.#map.addLayer({
      id: "tiles",
      type: "raster",
      source: "tiles",
    });
    this.#map.fire("controls.styles.tiles_changed", {
      type: "tiles",
      target: this.#map,
      originalEvent: null,
      source: source,
    });
  }

  onAdd(map: Map): HTMLElement {
    this.#map = map;
    this.#setup();
    return this.#container;
  }

  onRemove() {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
