import $ from "jquery";
import {
  IControl,
  LngLatBounds,
  Map as MglMap,
  RasterSourceSpecification,
  RequestParameters,
  ResourceType,
} from "maplibre-gl";
import { intersect } from "@turf/intersect";
import { featureCollection, polygon } from "@turf/helpers";

import {
  createControlButton,
  createControlContainer,
  createMdiIcon,
} from "../helpers";
import {
  TilesSourceBounds,
  TilesSourceCategory,
  TilesSourceDate,
} from "../../tiles-sources.ts";
import "./_index.css";

/**
 * Type of the event fired whenever the user selects a tiles source.
 */
export interface TilesSourceChangedEvent {
  type: "tiles";
  /**
   * The selected tiles source.
   */
  source: TilesSource;
  target: MglMap;
}

/**
 * This type adds an ID to MapLibre’s {@link RasterSourceSpecification} type.
 */
export type RasterSourceSpecificationWithId = RasterSourceSpecification & {
  /**
   * The internal ID of the tiles source.
   */
  id: string;
};

export type TilesSourceType = "photo" | "map";

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
  type: TilesSourceType;
  category: TilesSourceCategory;
  source: RasterSourceSpecificationWithId;
  description?: string;
  defaultForType?: boolean;
  bounds?: TilesSourceBounds;
  privacyPolicyUrl?: string;
  permissionRef?: string;
  icon?: string;
  date?: TilesSourceDate;
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
   * Whether the map is in edit mode.
   */
  editMode: boolean;
  /**
   * Optional. Title of the control.
   */
  title?: string;
}

/**
 * The order in which category lists should appear in the control.
 */
const categoryOrder: TilesSourceCategory[] = [
  "photo",
  "historicphoto",
  "osmbasedmap",
  "map",
  "historicmap",
  "elevation",
  "other",
];

/**
 * A control that allows switching between multiple tiles sources.
 */
export default class TilesSourcesControl implements IControl {
  #map: MglMap | undefined;
  readonly #title: string | undefined;
  readonly #sourcesByCategory = new Map<TilesSourceCategory, TilesSource[]>();
  readonly #sourcesByType: Record<TilesSourceType, TilesSource[]> = {
    photo: [],
    map: [],
  };
  readonly #editMode: boolean;
  readonly #container: HTMLDivElement;
  readonly #$inputsContainer: JQuery;

  constructor(options: TilesSourcesControlOptions) {
    this.#title = options.title;
    for (const source of options.sources) {
      const category = source.category;
      if (!this.#sourcesByCategory.has(category))
        this.#sourcesByCategory.set(category, []);
      this.#sourcesByCategory.get(category)?.push(source);

      this.#sourcesByType[source.type].push(source);
    }
    this.#editMode = options.editMode;
    this.#container = createControlContainer("maplibregl-ctrl-tiles-sources");
    this.#$inputsContainer = $('<div class="sources-categories">').hide();
  }

  #setup(): void {
    const map = this.#map;
    if (!map) throw Error("Map is undefined");

    const button = createControlButton({
      title: this.#title ?? "Backgrounds",
      icon: createMdiIcon("layers-outline"),
      onClick: () => {
        if (!this.#$inputsContainer.is(":visible"))
          this.#$inputsContainer.show();
        else this.#$inputsContainer.hide();
      },
    });

    map.on("click", () => {
      this.#$inputsContainer.hide();
    });
    this.#container.appendChild(button);
    this.#container.appendChild(this.#$inputsContainer[0]);

    const entries = [...this.#sourcesByCategory.entries()];
    entries.sort(
      (e1, e2) => categoryOrder.indexOf(e1[0]) - categoryOrder.indexOf(e2[0]),
    );
    for (const [category, sources] of entries) {
      const $listContainer = $(
        `<div class="sources-category-box" id="category-${category}">`,
      );
      this.#$inputsContainer.append($listContainer);
      const categoryTitle = window.ottm.translate(
        "map.controls.layers.categories." + category,
      );
      $listContainer.append(
        `<span class="sources-category-title">${categoryTitle}</span>`,
      );
      const $inputsList = $("<ul>");
      $listContainer.append($inputsList);

      for (const source of sources) {
        const $input: JQuery<HTMLInputElement> = $(
          `<input type="radio" name="tiles-sources" value="${source.id}" id="source-${source.id}">`,
        );
        $input.on("change", (e) => {
          this.#changeTilesSource(this.#findTilesSourceById(e.target.value));
        });
        const $item: JQuery<HTMLLIElement> = $("<li>");
        $item.append(
          $input,
          ` <label for="source-${source.id}">${source.label}</label>`,
        );
        $inputsList.append($item);
      }
    }

    map.setTransformRequest((url, resourceType) =>
      this.#transformRequest(url, resourceType),
    );

    map.on("zoomend", () => {
      this.#filterSources();
    });
    map.on("moveend", () => {
      this.#filterSources();
    });
    map.on("resize", () => {
      this.#filterSources();
    });

    map.on("load", () => {
      // Select the default photo source if in edit mode, otherwise select default map source
      const key = this.#editMode ? "photo" : "map";
      const source = this.#sourcesByType[key].find((s) => s.defaultForType);
      if (source) this.#changeTilesSource(source);
    });
  }

  #findTilesSourceById(id: string): TilesSource {
    let tilesSource: TilesSource | undefined;
    for (const sources of this.#sourcesByCategory.values()) {
      for (const source of sources) {
        if (source.id === id) {
          tilesSource = source;
          break;
        }
      }
    }
    if (!tilesSource) throw Error(`Can’t find tiles source with ID ${id}`);
    return tilesSource;
  }

  #changeTilesSource(source: TilesSource): void {
    const map = this.#map;
    if (!map) return;

    const layerId = "tiles";
    const sourceId = "tiles";
    if (map.getLayer(layerId)) map.removeLayer(layerId);
    if (map.getSource(sourceId)) map.removeSource(sourceId);
    console.log("Selected source:", source, source.source); // DEBUG
    map.addSource(sourceId, source.source);
    map.addLayer({
      id: layerId,
      type: "raster",
      source: sourceId,
    });
    const event: TilesSourceChangedEvent = {
      type: "tiles",
      target: map,
      source: source,
    };
    map.fire("controls.styles.tiles_changed", event);

    // Source may not have been changed by interacting with this control, select the corresponding radio button
    const $input = $("#source-" + source.id);
    if (!$input.prop("checked")) $input.prop("checked", true);
  }

  /**
   * Filter which sources are shown in the control depending on the current zoom and viewport bounds.
   *
   * Sources (that are not selected) that match any of the following criteria are hidden:
   * * Its min zoom is less than the current zoom.
   * * Its max zoom is greater than the current zoom.
   * * It has bounds and they do not intersect the current viewport bounds.
   */
  #filterSources(): void {
    const map = this.#map;
    if (!map) return;

    const zoom = map.getZoom();

    const viewportBounds = map.getBounds();
    const viewportBoundsVertices = [
      viewportBounds.getNorthWest().toArray(),
      viewportBounds.getNorthEast().toArray(),
      viewportBounds.getSouthEast().toArray(),
      viewportBounds.getSouthWest().toArray(),
      viewportBounds.getNorthWest().toArray(), // GeoJSON expects the first vertex to also be the last
    ];

    for (const [category, sources] of this.#sourcesByCategory.entries()) {
      let count = 0;

      for (const source of sources) {
        const $input = $("#source-" + source.id);

        const sourceBounds = source.bounds;
        const hide =
          !$input.prop("checked") &&
          ((!!source.source.minzoom && zoom < source.source.minzoom) ||
            (!!source.source.maxzoom && zoom > source.source.maxzoom) ||
            (!!sourceBounds &&
              !intersect(
                // TODO check shapes intersections instead of sourceBounds if available
                featureCollection([
                  polygon([getPolygon(sourceBounds)]),
                  polygon([viewportBoundsVertices]),
                ]),
              )));

        const $listItem = $input.parent();
        if (hide) $listItem.hide();
        else {
          count++;
          $listItem.show();
        }
      }

      const $categoryDiv = $("#category-" + category);
      if (count === 0) $categoryDiv.hide();
      else $categoryDiv.show();
    }

    function getPolygon(sourceBounds: TilesSourceBounds): [number, number][] {
      const bounds = new LngLatBounds([
        sourceBounds.bbox.minLon,
        sourceBounds.bbox.minLat,
        sourceBounds.bbox.maxLon,
        sourceBounds.bbox.maxLat,
      ]);
      return [
        bounds.getNorthWest().toArray(),
        bounds.getNorthEast().toArray(),
        bounds.getSouthEast().toArray(),
        bounds.getSouthWest().toArray(),
        bounds.getNorthWest().toArray(), // GeoJSON expects the first vertex to also be the last
      ];
    }
  }

  #transformRequest(
    url: string,
    resourceType?: ResourceType,
  ): RequestParameters | undefined {
    if (!resourceType || resourceType.valueOf() !== "Tile") return { url };
    const map = this.#map;
    if (!map) return undefined;

    const match = /{switch:(\w*(?:,\w*)*)}/.exec(url);
    if (match) {
      const parts = match[1].split(",");
      url = url.replace(match[0], encodeURIComponent(parts[0])); // TODO select random value for each user?
    }
    return { url };
  }

  onAdd(map: MglMap): HTMLElement {
    this.#map = map;
    this.#setup();
    return this.#container;
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  onRemove(): void {}
}
