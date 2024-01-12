import * as mgl from "maplibre-gl";

import * as utils from "../../../utils";
import * as helpers from "../helpers";
import "./index.css";

export type GeocoderControlOptions = {
  language: string;
  searchButtonTitle?: string;
  eraseButtonTitle?: string;
  placeholderText?: string;
  noResultsMessage?: string;
  errorMessage?: string;
};

type SearchResult = {
  addresstype: string;
  boundingbox: [number, number, number, number];
  category: string;
  display_name: string;
  importance: number;
  lat: number;
  licence: string;
  lon: number;
  name: string;
  osm_id: number;
  osm_type: string;
  place_id: number;
  place_rank: number;
  type: string;
};

/**
 * A control with a search bar that allows searching for a location.
 *
 * @see https://wiki.openstreetmap.org/wiki/Nominatim/FAQ#Where_are_the_translations_of_features%3f
 * @see https://github.com/openstreetmap/openstreetmap-website/tree/master/config/locales
 */
export default class GeocoderControl implements mgl.IControl {
  static readonly #BASE_URL: string =
      "https://nominatim.openstreetmap.org/search?q={query}&format=jsonv2&accept-language={lang}";

  #map: mgl.Map;
  #marker: mgl.Marker;
  readonly #language: string;
  readonly #noResultsMessage: string;
  readonly #errorMessage: string;
  readonly #container: HTMLDivElement;
  readonly #textField: HTMLInputElement;
  readonly #eraseButton: HTMLButtonElement;
  readonly #searchButton: HTMLButtonElement;
  readonly #resultsPanel: HTMLDivElement;

  constructor(options?: GeocoderControlOptions) {
    this.#language = options.language;
    this.#noResultsMessage = options.noResultsMessage ?? "No results.";
    this.#errorMessage = options.errorMessage ?? "An error occured.";

    this.#container = helpers.createControlContainer("maplibregl-ctrl-geocoder");

    this.#textField = document.createElement("input");
    this.#textField.type = "text";
    this.#textField.placeholder = options.placeholderText ?? "Search";
    this.#textField.accessKey = "f";
    // Submit on enter key pressed
    this.#textField.onkeyup = e => {
      if (e.key === "Enter") {
        this.#onInputSubmit();
      }
    };
    // Hide results when the text changes
    this.#textField.oninput = () => {
      this.#hideResultsPanel();
    };

    const eraseIcon = document.createElement("span");
    eraseIcon.className = "mdi mdi-close";
    this.#eraseButton = helpers.createControlButton({
      title: options.eraseButtonTitle ?? "Erase",
      icon: eraseIcon,
      onClick: () => this.#onErase(),
    });

    const searchIcon = document.createElement("span");
    searchIcon.className = "mdi mdi-magnify";
    this.#searchButton = helpers.createControlButton({
      title: options.searchButtonTitle ?? "Go",
      icon: searchIcon,
      onClick: () => this.#onInputSubmit(),
    });

    this.#resultsPanel = document.createElement("div");
    this.#resultsPanel.className = "maplibregl-ctrl-geocoder-results-panel";
    this.#resultsPanel.style.display = "none";
  }

  #onErase() {
    this.#hideResultsPanel();
    this.#textField.value = "";
    this.#textField.focus();
  }

  #onInputSubmit() {
    const query = (this.#textField.value ?? "").trim();
    if (query) {
      const url = GeocoderControl.#BASE_URL
          .replace("{query}", encodeURIComponent(query))
          .replace("{lang}", encodeURIComponent(this.#language));
      $.get(url)
          .done(data => this.#onResult(data))
          .fail(() => this.#onFailure());
    }
  }

  /**
   * Called when a geocoding request succeeded.
   * @param results The list of results.
   */
  #onResult(results: SearchResult[]) {
    this.#resultsPanel.replaceChildren(); // Clear
    if (results.length === 0) {
      this.#resultsPanel.textContent = this.#noResultsMessage;
    } else {
      const list = document.createElement("ul");
      const noTranslationsMark = "```";
      for (const result of results) {
        const type = result.type;
        const category = result.category;
        // Prefix name translation algorithm from
        // https://github.com/openstreetmap/openstreetmap-website/blob/master/app/controllers/geocoder_controller.rb#L109
        let prefixName = window.ottm.translate(
            `osm_feature_type.prefix.${category}.${type}`,
            () => noTranslationsMark + utils.capitalize(type.replace("_", " "))
        );
        if (category === "boundary" && type === "administrative") {
          // Check if a better translation exists
          prefixName = window.ottm.translate(
              `osm_feature_type.prefix.place.${result.addresstype}`,
              () => window.ottm.translate(
                  `osm_feature_type.admin_levels.level${Math.floor((result.place_rank + 1) / 2)}`,
                  prefixName
              )
          );
        }

        const item = document.createElement("li");
        if (prefixName.includes(noTranslationsMark)) {
          // Italicize if no translation
          const emNode = document.createElement("em");
          emNode.appendChild(document.createTextNode(prefixName.slice(noTranslationsMark.length)))
          item.appendChild(emNode);
        } else {
          item.appendChild(document.createTextNode(prefixName));
        }
        item.appendChild(document.createTextNode(" – "));
        const link = document.createElement("a");
        link.textContent = result.display_name;
        link.href = "#";
        const boundingBox = result.boundingbox;
        const bb: mgl.LngLatBoundsLike = [{
          lat: boundingBox[0],
          lng: boundingBox[2]
        }, {
          lat: boundingBox[1],
          lng: boundingBox[3]
        }];
        link.onclick = () => this.#onResultClick(result.lat, result.lon, bb);
        item.appendChild(link);
        list.appendChild(item);
      }
      this.#resultsPanel.appendChild(list);
    }
    this.#showResultsPanel();
  }

  /**
   * Called when a geocoding request failed.
   */
  #onFailure() {
    this.#resultsPanel.replaceChildren(); // Clear
    this.#resultsPanel.textContent = this.#errorMessage;
    this.#showResultsPanel();
  }

  /**
   * Called when a search result is clicked.
   * @param lat Result’s latitude.
   * @param lng Result’s longitude.
   * @param boundingBox Result’s bounding box.
   */
  #onResultClick(lat: number, lng: number, boundingBox: mgl.LngLatBoundsLike) {
    this.#marker?.remove();
    this.#map.fitBounds(boundingBox);
    this.#marker = new mgl.Marker({});
    this.#marker.setLngLat({lat: lat, lng: lng});
    this.#marker.addTo(this.#map);
  }

  #showResultsPanel() {
    this.#resultsPanel.style.display = "block";
  }

  #hideResultsPanel() {
    this.#marker?.remove();
    this.#resultsPanel.style.display = "none";
    this.#resultsPanel.replaceChildren(); // Clear
  }

  onAdd(map: mgl.Map): HTMLElement {
    this.#map = map;
    const inputContainer = document.createElement("div");
    inputContainer.className = "maplibregl-ctrl-geocoder-search-bar";
    inputContainer.appendChild(this.#searchButton);
    inputContainer.appendChild(this.#textField);
    inputContainer.appendChild(this.#eraseButton);
    this.#container.appendChild(inputContainer);
    this.#container.appendChild(this.#resultsPanel);
    return this.#container;
  }

  onRemove() {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
