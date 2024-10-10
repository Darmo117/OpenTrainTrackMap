import {
  IControl,
  Map,
  MapLibreEvent,
  RasterSourceSpecification as MglRasterSourceSpecification,
  RasterTileSource,
} from "maplibre-gl";

import {
  createControlButton,
  createControlContainer,
  createMdiIcon,
} from "../helpers";
import "./_index.css";

/**
 * Type of the event fired whenever the user selects a tiles source.
 */
export type TilesChangedEvent = MapLibreEvent & {
  /**
   * The selected tiles source.
   */
  source: TilesSource;
};

/**
 * This type adds an ID to MapLibre’s {@link MglRasterSourceSpecification} type.
 */
export type RasterSourceSpecification = MglRasterSourceSpecification & {
  /**
   * The internal ID of the tiles source.
   */
  id: string;
};

/**
 * This type represents a tiles source.
 */
export interface TilesSource {
  /**
   * Display-name of the tiles source.
   */
  label: string;
  /**
   * The internal ID of the tiles source.
   */
  id: string;
  /**
   * A MapLibre raster tiles source specification object.
   */
  source: RasterSourceSpecification;
}

/**
 * Options for the {@link TilesSourcesControl} class.
 */
export interface TilesSourcesControlOptions {
  /**
   * List of tile sources to show in the control.
   */
  sources: TilesSource[];
  /**
   * Optional. Title of the control.
   */
  title?: string;
}

/**
 * A control that allows switching between multiple tiles sources.
 */
export default class TilesSourcesControl implements IControl {
  #map: Map | undefined;
  readonly #options: TilesSourcesControlOptions;
  readonly #container: HTMLDivElement;
  readonly #inputsContainer: HTMLDivElement;

  constructor(options: TilesSourcesControlOptions) {
    this.#options = { ...options };
    this.#container = createControlContainer("maplibregl-ctrl-tiles-sources");
    this.#inputsContainer = document.createElement("div");
    this.#inputsContainer.style.display = "none";
  }

  #findTilesSourceById(id: string): TilesSource {
    const tilesSource = this.#options.sources.find(
      (source) => source.id === id,
    );
    if (!tilesSource) throw Error(`Can’t find tiles source with ID ${id}`);
    return tilesSource;
  }

  #setup(): void {
    if (!this.#map) throw Error("map is undefined");
    const button = createControlButton({
      title: this.#options.title ?? "Backgrounds",
      icon: createMdiIcon("layers-outline"),
      onClick: () => {
        if (this.#inputsContainer.style.display === "none")
          this.#inputsContainer.style.display = "block";
        else this.#inputsContainer.style.display = "none";
      },
    });
    this.#map.on("click", () => (this.#inputsContainer.style.display = "none"));
    this.#container.appendChild(button);
    this.#container.appendChild(this.#inputsContainer);

    const inputsList = document.createElement("ul");
    this.#inputsContainer.append(inputsList);

    this.#options.sources.forEach((source) => {
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "tiles-sources";
      input.value = source.id;
      input.id = source.id;
      input.onchange = (e) => {
        this.#onSelectionChange(e);
      };
      const label = document.createElement("label");
      label.textContent = source.label;
      label.htmlFor = source.id;
      const item = document.createElement("li");
      item.append(input, " ", label);
      inputsList.appendChild(item);
    });

    this.#map.on("load", () => {
      if (!this.#map) return;
      // "id" property is added by buildStyle()
      const elementId = (
        (this.#map.getSource("tiles") as RasterTileSource)
          ._options as RasterSourceSpecification
      ).id;
      (document.getElementById(elementId) as HTMLInputElement).checked = true;
    });
  }

  #onSelectionChange(e: Event): void {
    const id = (e.target as HTMLInputElement).value;
    this.#changeTilesSource(this.#findTilesSourceById(id));
  }

  #changeTilesSource(source: TilesSource): void {
    if (!this.#map) return;
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

  onRemove(): void {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
