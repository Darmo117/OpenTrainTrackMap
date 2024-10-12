import { GeolocateControl, ScaleControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import $ from "jquery";

import OttmMap from "./map";
import CompassControl from "./controls/compass";
import GeocoderControl from "./controls/geocoder";
import TilesSourcesControl, {
  TilesSource,
  TilesSourceChangedEvent,
} from "./controls/tiles-sources";
import OpenExternalMapControl from "./controls/open-external-map";
import ZoomControl from "./controls/zoom";
import loadTilesSources from "./tiles-sources.ts";
import initMapEditor from "./editor/index";

declare global {
  interface Window {
    // Inject global properties
    // Cf. MapPageHandler class in ottm/page_handlers/_map_handler.py for values
    OTTM_MAP_CONFIG?: {
      edit: boolean;
    };
  }
}

/**
 * Initalize the map view.
 */
export default function initMap(): void {
  if (!window.OTTM_MAP_CONFIG)
    throw new Error("Missing global OTTM_MAP_CONFIG object");

  const editMode = window.OTTM_MAP_CONFIG.edit;
  const map = new OttmMap({
    container: "map",
    antialias: true,
    locale: {
      "AttributionControl.ToggleAttribution": window.ottm.translate(
        "map.controls.toggle_attribution.tooltip",
      ),
      "GeolocateControl.FindMyLocation": window.ottm.translate(
        "map.controls.geolocation.find_my_location",
      ),
      "GeolocateControl.LocationNotAvailable": window.ottm.translate(
        "map.controls.geolocation.location_unavailable",
      ),
    },
    style: {
      name: "base",
      version: 8,
      sources: {},
      layers: [],
      transition: {
        duration: 0,
      },
      // Custom fonts: https://maplibre.org/maplibre-style-spec/glyphs/
      // Custom fonts generator: https://maplibre.org/font-maker/
    },
  });
  map.keyboard.disable(); // Disable default keyboard actions

  /*
   * Add controls
   */

  map.addControl(
    new ScaleControl({
      maxWidth: 100,
      unit: "imperial",
    }),
  );
  map.addControl(
    new ScaleControl({
      maxWidth: 100,
      unit: "metric",
    }),
  );

  if (editMode) {
    initMapEditor(map);
  } else {
    map.addControl(
      new GeocoderControl({
        language: window.ottm.getPageLanguage().code,
        translator: (key, defaultValue) =>
          window.ottm.translate(key, defaultValue),
        searchButtonTitle: window.ottm.translate(
          "map.controls.search.search_button.title",
        ),
        eraseButtonTitle: window.ottm.translate(
          "map.controls.search.erase_button.title",
        ),
        placeholderText: window.ottm.translate(
          "map.controls.search.placeholder",
        ),
        noResultsMessage: window.ottm.translate(
          "map.controls.search.no_results",
        ),
        errorMessage: window.ottm.translate("map.controls.search.error"),
      }),
      "top-left",
    );
  }

  map.addControl(
    new TilesSourcesControl({
      title: window.ottm.translate("map.controls.layers.tooltip"),
      sources: loadTilesSources(),
      editMode: editMode,
    }),
    "top-left",
  );

  const zoomControl = new ZoomControl({
    zoomInTitle: window.ottm.translate("map.controls.zoom_in.tooltip"),
    zoomOutTitle: window.ottm.translate("map.controls.zoom_out.tooltip"),
  });
  map.addControl(zoomControl, "top-right");
  map.boxZoom.disable();
  map.doubleClickZoom.disable();

  const staticPath = window.ottm.config.get("staticPath");

  map.addControl(
    new OpenExternalMapControl({
      buttonTitle: window.ottm.translate(
        "map.controls.google_maps_button.tooltip",
      ),
      iconUrl: `${staticPath}ottm/images/icons/GoogleMaps.png`,
      urlPattern: "https://www.google.com/maps/@{lat},{lng},{zoom}z",
      zoomMapping: (zoom) => (zoom + 1).toFixed(2),
    }),
    "top-right",
  );

  map.addControl(
    new OpenExternalMapControl({
      buttonTitle: window.ottm.translate(
        "map.controls.bing_maps_button.tooltip",
      ),
      iconUrl: `${staticPath}ottm/images/icons/Bing.ico`,
      urlPattern: "https://www.bing.com/maps/?cp={lat}~{lng}&lvl={zoom}",
      zoomMapping: (zoom) => (zoom + 1).toFixed(1),
    }),
    "top-right",
  );

  map.addControl(
    new OpenExternalMapControl({
      buttonTitle: window.ottm.translate("map.controls.osm_button.tooltip"),
      iconUrl: `${staticPath}ottm/images/icons/OSM.png`,
      urlPattern: "https://www.openstreetmap.org/#map={zoom}/{lat}/{lng}",
      zoomMapping: (zoom) => (Math.round(zoom) + 1).toString(),
    }),
    "top-right",
  );

  map.addControl(
    new OpenExternalMapControl({
      buttonTitle: window.ottm.translate("map.controls.ohm_button.tooltip"),
      iconUrl: `${staticPath}ottm/images/icons/OHM.ico`,
      urlPattern: "https://www.openhistoricalmap.org/#map={zoom}/{lat}/{lng}",
      zoomMapping: (zoom) => (Math.round(zoom) + 1).toString(),
    }),
    "top-right",
  );

  map.addControl(
    new OpenExternalMapControl({
      buttonTitle: window.ottm.translate(
        "map.controls.ign_compare_button.tooltip",
      ),
      iconUrl: `${staticPath}ottm/images/icons/IGN.ico`,
      urlPattern:
        "https://remonterletemps.ign.fr/comparer/basic?x={lng}&y={lat}&z={zoom}",
      zoomMapping: (zoom) => (Math.round(zoom) + 1).toString(),
    }),
    "top-right",
  );

  map.addControl(
    new OpenExternalMapControl({
      buttonTitle: window.ottm.translate("map.controls.geohack_button.tooltip"),
      iconUrl: `${staticPath}ottm/images/icons/WikimediaCloudServices.svg`,
      urlPattern:
        "https://geohack.toolforge.org/geohack.php?params={lat}_N_{lng}_E_scale:{zoom}",
      // Function extrapolated by an exponential trend line in LibreOffice Calc, using the values at:
      // https://wiki.openstreetmap.org/w/index.php?title=Zoom_levels&oldid=2553097
      zoomMapping: (zoom) =>
        (1080657321.02457 * Math.exp(-0.693992077826686 * (zoom + 2))).toFixed(
          5,
        ),
    }),
    "top-right",
  );

  map.addControl(
    new GeolocateControl({
      positionOptions: {
        enableHighAccuracy: true,
      },
      showUserLocation: false,
    }),
    "top-right",
  );

  map.addControl(
    new CompassControl({
      title: window.ottm.translate("map.controls.compass.tooltip"),
    }),
    "top-right",
  );

  /*
   * Hook events
   */

  window.onhashchange = () => {
    centerViewFromUrl();
  };
  map.on("zoomend", () => {
    updateUrlHash();
    const zoom = map.getZoom();
    zoomControl.setZoomOutButtonDisabled(zoom === map.getMinZoom());
    zoomControl.setZoomInButtonDisabled(zoom === map.getMaxZoom());
  });
  map.on("moveend", () => {
    updateUrlHash();
  });
  map.on("resize", () => {
    updateUrlHash();
  });
  map.on("load", () => {
    // Delete config object and script tag
    delete window.OTTM_MAP_CONFIG;
    $("#ottm-map-config-script").remove();
  });
  map.on("controls.styles.tiles_changed", (e: TilesSourceChangedEvent) => {
    onTilesSourceChanged(e.source, true);
  });

  $("body").on("keydown", (e) => {
    if (map.textFieldHasFocus) return;
    switch (e.key) {
      case "ArrowUp":
        map.panBy([0, -100]);
        break;
      case "ArrowDown":
        map.panBy([0, 100]);
        break;
      case "ArrowLeft":
        map.panBy([-100, 0]);
        break;
      case "ArrowRight":
        map.panBy([100, 0]);
        break;
    }
  });

  map.hookTextFieldsFocusEvents();

  /**
   * Indicates whether the map’s view is being updated from the page’s URL hash.
   */
  let updatingView = false;
  /**
   * Indicates whether the page’s URL hash is being updated from the map’s view.
   */
  let updatingHash = false;

  if (getPositionFromURL().found) centerViewFromUrl();

  /*
   * Functions
   */

  /**
   * Called when the map tiles source has changed.
   * @param source The new tiles source.
   * @param shouldUpdateUrlHash Whether to update the URL hash.
   */
  function onTilesSourceChanged(
    source: TilesSource,
    shouldUpdateUrlHash = false,
  ): void {
    map.setMaxZoom(source.source.maxzoom);
    if (shouldUpdateUrlHash) updateUrlHash(); // In case the new max zoom is less than the current one
  }

  /**
   * Return a map position from the current URL.
   *
   * @return An array containing the latitude, longitude and zoom,
   *  and a boolean indicating whether values could be extracted from the URL.
   */
  function getPositionFromURL(): {
    pos: [number, number, number];
    found: boolean;
  } {
    const match = /^#map=(\d+\.?\d*)\/(-?\d+\.?\d*)\/(-?\d+\.?\d*)$/.exec(
      window.location.hash,
    );
    if (match) {
      const minZoom = map.getMinZoom();
      const maxZoom = map.getMaxZoom();
      const zoom = Math.max(minZoom, Math.min(maxZoom, parseFloat(match[1])));
      const lat = parseFloat(match[2]);
      const lng = parseFloat(match[3]);
      return { pos: [lat, lng, zoom], found: true };
    }
    return { pos: [0, 0, 15], found: false };
  }

  /**
   * Update page’s URL hash from the current map view position.
   */
  function updateUrlHash(): void {
    if (updatingView) {
      updatingView = false;
    } else {
      updatingHash = true;
      const centerPos = map.getCenter();
      const lat = centerPos.lat.toFixed(5);
      const lng = centerPos.lng.toFixed(5);
      const zoom = map.getZoom().toFixed(5);
      const hash = `#map=${zoom}/${lat}/${lng}`;
      window.location.hash = hash;
      const mapNavLinks = [
        "#nav-main-link",
        "#nav-edit-link",
        "#nav-history-link",
      ];
      for (const linkId of mapNavLinks) {
        const $navLink = $(linkId);
        if (!$navLink.length) continue;
        const url = new URL($navLink.prop("href") as string);
        url.hash = hash;
        $navLink.attr("href", url.href);
      }
      window.ottm.setReferrer();
    }
  }

  /**
   * Center the view from the URL’s hash.
   */
  function centerViewFromUrl(): void {
    if (updatingHash) {
      updatingHash = false;
    } else {
      const {
        pos: [lat, lng, zoom],
        found,
      } = getPositionFromURL();
      if (found) {
        updatingView = true;
        map.setZoom(zoom);
        map.setCenter({ lat, lng });
      } else {
        updateUrlHash();
      }
    }
  }
}
