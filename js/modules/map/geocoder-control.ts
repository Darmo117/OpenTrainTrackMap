import {IControl, Map, Marker, LngLatBoundsLike} from "maplibre-gl";
import {controlButton, controlContainer} from "@mapbox-controls/helpers";

export type GeocoderControlOptions = {
  language: string;
  searchButtonTitle?: string;
  eraseButtonTitle?: string;
  placeholderText?: string;
  noResultsMessage?: string;
  errorMessage?: string;
}

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
}

/**
 * Control with a search bar that allows searching for a location.
 */
export default class GeocoderControl implements IControl {
  private static readonly BASE_URL: string =
    "https://nominatim.openstreetmap.org/search?q={query}&format=jsonv2&accept-language={lang}";
  private readonly language: string;
  private readonly noResultsMessage: string;
  private readonly errorMessage: string;
  private readonly container: HTMLDivElement;
  private readonly textField: HTMLInputElement;
  private readonly eraseButton: HTMLButtonElement;
  private readonly searchButton: HTMLButtonElement;
  private readonly resultsPanel: HTMLDivElement;
  private marker: Marker;
  private map: Map;

  constructor(options?: GeocoderControlOptions) {
    this.language = options.language;
    this.noResultsMessage = options.noResultsMessage ?? "No results.";
    this.errorMessage = options.errorMessage ?? "An error occured.";

    this.container = controlContainer("maplibre-ctrl-geocoder");

    this.textField = document.createElement("input");
    this.textField.type = "text";
    this.textField.placeholder = options.placeholderText ?? "Search";
    this.textField.accessKey = "f";
    // Submit on enter key pressed
    this.textField.onkeyup = e => {
      if (e.key === "Enter") {
        this.onInputSubmit();
      }
    };
    // Hide results when the text changes
    this.textField.oninput = () => {
      this.hideResultsPanel();
    };

    const eraseIcon = document.createElement("span");
    eraseIcon.className = "mdi mdi-close";
    this.eraseButton = controlButton({
      title: options.eraseButtonTitle ?? "Erase",
      icon: eraseIcon,
      onClick: () => this.onErase(),
    });

    const searchIcon = document.createElement("span");
    searchIcon.className = "mdi mdi-magnify";
    this.searchButton = controlButton({
      title: options.searchButtonTitle ?? "Go",
      icon: searchIcon,
      onClick: () => this.onInputSubmit(),
    });

    this.resultsPanel = document.createElement("div");
    this.resultsPanel.className = "maplibre-ctrl-geocoder-results-panel";
    this.resultsPanel.style.display = "none";
  }

  onErase() {
    this.hideResultsPanel();
    this.textField.value = "";
    this.textField.focus();
  }

  onInputSubmit() {
    const query = (this.textField.value ?? "").trim();
    if (query) {
      const url = GeocoderControl.BASE_URL
        .replace("{query}", encodeURIComponent(query))
        .replace("{lang}", encodeURIComponent(this.language));
      $.get(url)
        .done(data => this.onResult(data))
        .fail(() => this.onFailure());
    }
  }

  /**
   * Called when a geocoding request succeeded.
   * @param results The list of results.
   */
  onResult(results: SearchResult[]) {
    this.resultsPanel.replaceChildren(); // Clear
    if (results.length === 0) {
      this.resultsPanel.textContent = this.noResultsMessage;
    } else {
      const list = document.createElement("ul");
      console.log(results); // DEBUG
      const specialAddressTypes = ["building", "amenity"];
      for (const result of results) {
        const type = result.type;
        const addressType = result.addresstype;
        const displayName = result.display_name;
        const boundingBox = result.boundingbox;
        const lat = result.lat;
        const lng = result.lon;
        let displayType;
        if (specialAddressTypes.includes(addressType) && type !== "yes") {
          displayType = type;
        } else {
          displayType = addressType;
        }

        const item = document.createElement("li");
        item.appendChild(document.createTextNode(`${displayType} – `)); // TODO translate type
        const link = document.createElement("a");
        link.textContent = displayName;
        link.href = "#";
        const bb: LngLatBoundsLike = [{
          lat: boundingBox[0],
          lng: boundingBox[2]
        }, {
          lat: boundingBox[1],
          lng: boundingBox[3]
        }];
        link.onclick = () => this.onResultClick(lat, lng, bb);
        item.appendChild(link);
        list.appendChild(item);
      }
      this.resultsPanel.appendChild(list);
    }
    this.showResultsPanel();
  }

  /**
   * Called when a geocoding request failed.
   */
  onFailure() {
    this.resultsPanel.replaceChildren(); // Clear
    this.resultsPanel.textContent = this.errorMessage;
    this.showResultsPanel();
  }

  /**
   * Called when a search result is clicked.
   * @param lat Result’s latitude.
   * @param lng Result’s longitude.
   * @param boundingBox Result’s bounding box.
   */
  onResultClick(lat: number, lng: number, boundingBox: LngLatBoundsLike) {
    this.marker?.remove();
    this.map.fitBounds(boundingBox);
    this.marker = new Marker({});
    this.marker.setLngLat({lat: lat, lng: lng});
    this.marker.addTo(this.map);
  }

  showResultsPanel() {
    this.resultsPanel.style.display = "block";
  }

  hideResultsPanel() {
    this.marker?.remove();
    this.resultsPanel.style.display = "none";
    this.resultsPanel.replaceChildren(); // Clear
  }

  onAdd(map: Map): HTMLElement {
    this.map = map;
    const inputContainer = document.createElement("div");
    inputContainer.className = "maplibre-ctrl-geocoder-search-bar";
    inputContainer.appendChild(this.searchButton);
    inputContainer.appendChild(this.textField);
    inputContainer.appendChild(this.eraseButton);
    this.container.appendChild(inputContainer);
    this.container.appendChild(this.resultsPanel);
    return this.container;
  }

  onRemove() {
    this.container.parentNode?.removeChild(this.container);
  }
}