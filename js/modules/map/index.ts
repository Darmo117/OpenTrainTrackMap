import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import ZoomControl from "@mapbox-controls/zoom";
import "@mapbox-controls/zoom/src/index.css";
import StylesControl from "@mapbox-controls/styles";
import {Style} from "@mapbox-controls/styles";
import "@mapbox-controls/styles/src/index.css";
import CompassControl from "@mapbox-controls/compass";
import "@mapbox-controls/compass/src/index.css";
import $ from "jquery";

import GeocoderControl from "./geocoder-control";
import OpenExternalMapControl from "./open-external-map-control";
import initMapEditor from "./map-editor";
import {RasterSourceSpecification} from "@maplibre/maplibre-gl-style-spec";

declare global {
  interface Window {
    // Inject global properties
    // Cf. MapPageHandler class in ottm/page_handlers/_map_handler.py for values
    OTTM_MAP_CONFIG: {
      edit: boolean,
    };
  }
}

export default function initMap() {
  const mapStyles: maplibregl.StyleSpecification[] = [
    buildStyle(
      window.ottm.translations.get("map.controls.layers.base.osm"),
      "osm",
      "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
      'Map data © <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
    ),
    buildStyle(
      window.ottm.translations.get("map.controls.layers.base.satellite_esri"),
      "arcgis",
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
    ),
    buildStyle(
      window.ottm.translations.get("map.controls.layers.base.satellite_maptiler"),
      "maptiler",
      "/tile?provider=maptiler&x={x}&y={y}&z={z}",
      'Tiles © <a href="https://www.maptiler.com/copyright/" target="_blank">MapTiler</a>, Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
    ),
    buildStyle(
      window.ottm.translations.get("map.controls.layers.base.satellite_google"),
      "google",
      "http://www.google.com/maps/vt?lyrs=s@189&x={x}&y={y}&z={z}", // lyrs=s@189 -> satellite images
      "Tiles © Google",
      18
    ),
  ];

  const defaultMapStyle = mapStyles[0];
  const map = new maplibregl.Map({
    container: "map",
    style: defaultMapStyle,
    center: [0, 0],
    zoom: 1
  });

  /*
   * Add controls
   */

  map.addControl(new maplibregl.ScaleControl({
    maxWidth: 100,
    unit: 'imperial'
  }));
  map.addControl(new maplibregl.ScaleControl({
    maxWidth: 100,
    unit: 'metric'
  }));

  map.addControl(new GeocoderControl({
    language: window.ottm.getPageLanguage().code,
    searchButtonTitle: window.ottm.translations.get("map.controls.search.search_button.title"),
    eraseButtonTitle: window.ottm.translations.get("map.controls.search.erase_button.title"),
    placeholderText: window.ottm.translations.get("map.controls.search.placeholder"),
    noResultsMessage: window.ottm.translations.get("map.controls.search.no_results"),
    errorMessage: window.ottm.translations.get("map.controls.search.error"),
  }), "top-left");

  if (window.OTTM_MAP_CONFIG.edit) {
    initMapEditor(map);
  }

  const styles: Style[] = [];
  mapStyles.forEach(style => {
    styles.push({
      label: style.name,
      styleName: style.name,
      styleUrl: style as any,
    })
  });
  // FIXME clickable area is too wide
  // @ts-ignore
  map.addControl(new StylesControl({ // TODO translate
    styles: styles,
    onChange: style => onStyleChanged(style.styleUrl as any, true),
    compact: true,
  }), "top-left");

  // @ts-ignore
  map.addControl(new ZoomControl(), "top-right"); // TODO translate

  map.addControl(new OpenExternalMapControl({
    buttonTitle: window.ottm.translations.get("map.controls.google_maps_button.tooltip"),
    iconUrl: `${window.ottm.config.get("staticPath")}ottm/images/icons/GoogleMaps.png`,
    urlPattern: "https://www.google.com/maps/@{lat},{lng},{zoom}z",
    zoomMapping: zoom => (zoom + 1).toFixed(2),
  }), "top-right");

  map.addControl(new OpenExternalMapControl({
    buttonTitle: window.ottm.translations.get("map.controls.bing_maps_button.tooltip"),
    iconUrl: `${window.ottm.config.get("staticPath")}ottm/images/icons/Bing.ico`,
    urlPattern: "https://www.bing.com/maps/?cp={lat}~{lng}&lvl={zoom}",
    zoomMapping: zoom => (zoom + 1).toFixed(1),
  }), "top-right");

  map.addControl(new OpenExternalMapControl({
    buttonTitle: window.ottm.translations.get("map.controls.osm_button.tooltip"),
    iconUrl: `${window.ottm.config.get("staticPath")}ottm/images/icons/OSM.png`,
    urlPattern: "https://www.openstreetmap.org/#map={zoom}/{lat}/{lng}",
    zoomMapping: zoom => Math.round(zoom) + 1,
  }), "top-right");

  map.addControl(new OpenExternalMapControl({
    buttonTitle: window.ottm.translations.get("map.controls.ohm_button.tooltip"),
    iconUrl: `${window.ottm.config.get("staticPath")}ottm/images/icons/OHM.ico`,
    urlPattern: "https://www.openhistoricalmap.org/#map={zoom}/{lat}/{lng}",
    zoomMapping: zoom => Math.round(zoom) + 1,
  }), "top-right");

  map.addControl(new OpenExternalMapControl({
    buttonTitle: window.ottm.translations.get("map.controls.ign_compare_button.tooltip"),
    iconUrl: `${window.ottm.config.get("staticPath")}ottm/images/icons/IGN.ico`,
    urlPattern: "https://remonterletemps.ign.fr/comparer/basic?x={lng}&y={lat}&z={zoom}",
    zoomMapping: zoom => Math.round(zoom) + 1,
  }), "top-right");

  map.addControl(new OpenExternalMapControl({
    buttonTitle: window.ottm.translations.get("map.controls.geohack_button.tooltip"),
    iconUrl: `${window.ottm.config.get("staticPath")}ottm/images/icons/WikimediaCloudServices.svg`,
    urlPattern: "https://geohack.toolforge.org/geohack.php?params={lat}_N_{lng}_E_scale:{zoom}",
    // Function extrapolated by an exponential trend line in LibreOffice Calc, using the values at:
    // https://wiki.openstreetmap.org/w/index.php?title=Zoom_levels&oldid=2553097
    zoomMapping: zoom => (1080657321.02457 * Math.exp(-0.693992077826686 * (zoom + 2))).toFixed(5),
  }), "top-right");

  // @ts-ignore
  map.addControl(new CompassControl(), "top-right"); // TODO translate

  /*
   * Hook events
   */

  window.onhashchange = () => centerViewFromUrl();
  map.on("zoomend", () => updateUrlHash());
  map.on("moveend", () => updateUrlHash());
  map.on("resize", () => updateUrlHash());
  map.on("load", () => {
    patchCssClasses();
    onStyleChanged(defaultMapStyle);
    if (getPositionFromURL().found) {
      centerViewFromUrl();
    } else {
      centerViewToUserLocation();
    }
    // Delete config object and script tag
    delete window.OTTM_MAP_CONFIG;
    $("#ottm-map-config-script").remove();
  });

  /*
   * Functions
   */

  /**
   * Create a style object with the given data.
   * @param name Style’s readable name.
   * @param id Style’s internal ID.
   * @param tilesUrlPattern URL pattern to get map tiles.
   * @param attribution String to display in the bottom right of the map.
   * @param maxZoom Max zoom value.
   * @return The style object.
   */
  function buildStyle(
    name: string,
    id: string,
    tilesUrlPattern: string,
    attribution: string,
    maxZoom: number = 19
  ): maplibregl.StyleSpecification {
    const type = "raster";
    return {
      name: name,
      version: 8,
      sources: {
        tiles: {
          type: type,
          tiles: [tilesUrlPattern],
          tileSize: 256,
          attribution: attribution,
          maxzoom: maxZoom,
        },
      },
      layers: [
        {
          id: id,
          type: type,
          source: "tiles",
        }
      ],
    };
  }

  /**
   * Patch "maplibregl-ctrl*" classes.
   * @see https://github.com/mapbox/mapbox-gl-draw/issues/1182#issuecomment-1659480858
   */
  function patchCssClasses() {
    const classMappings = {
      "mapboxgl-ctrl": "maplibregl-ctrl",
      "mapboxgl-ctrl-group": "maplibregl-ctrl-group",
    };
    for (const [fromClass, toClass] of Object.entries(classMappings)) {
      $(`.${fromClass}:not(.${toClass})`).each((_, e) => {
        $(e).addClass(toClass);
      });
    }
  }

  /**
   * Called when the map style has changed.
   * @param style The new style.
   * @param shouldUpdateUrlHash Whether to update the URL hash.
   */
  function onStyleChanged(style: maplibregl.StyleSpecification, shouldUpdateUrlHash: boolean = false) {
    map.setMaxZoom((style.sources.tiles as RasterSourceSpecification).maxzoom);
    if (shouldUpdateUrlHash) {
      updateUrlHash(); // In case the new max zoom is less than the current one
    }
  }

  /**
   * Indicates whether the map’s view is being updated from the page’s URL hash.
   */
  let updatingView = false;
  /**
   * Indicates whether the page’s URL hash is being updated from the map’s view.
   */
  let updatingHash = false;

  /**
   * Ask the client if they want to allow geolocation.
   * If yes, the map view is centered on the position returned by the browser.
   * @async
   */
  function centerViewToUserLocation() {
    navigator.permissions
      .query({name: "geolocation"})
      .then(result => {
        switch (result.state) {
          case "granted":
          case "prompt":
            navigator.geolocation.getCurrentPosition(
              p => {
                map.setZoom(13);
                map.setCenter({lat: p.coords.latitude, lng: p.coords.longitude});
              },
              e => {
                console.log(e.message);
                updateUrlHash();
              },
              {
                enableHighAccuracy: false,
                maximumAge: 30000,
                timeout: 20000,
              }
            );
            break;
          default:
          case "denied":
            console.log("User does not allow geolocation");
            updateUrlHash();
            break;
        }
      });
  }

  /**
   * Return a map position from the current URL.
   *
   * @return An array containing the latitude, longitude and zoom,
   *  and a boolean indicating whether values could be extracted from the URL.
   */
  function getPositionFromURL(): { pos: [number, number, number], found: boolean } {
    const match = /^#map=(\d+\.?\d*)\/(-?\d+\.?\d*)\/(-?\d+\.?\d*)$/
      .exec(window.location.hash);
    if (match) {
      const minZoom = map.getMinZoom();
      const maxZoom = map.getMaxZoom();
      const zoom = Math.max(minZoom, Math.min(maxZoom, parseFloat(match[1])));
      const lat = parseFloat(match[2]);
      const lng = parseFloat(match[3]);
      return {pos: [lat, lng, zoom], found: true};
    }
    return {pos: [0, 0, 15], found: false};
  }

  /**
   * Update page’s URL hash from the current map view position.
   */
  function updateUrlHash() {
    if (updatingView) {
      updatingView = false;
    } else {
      updatingHash = true;
      const centerPos = map.getCenter();
      const lat = centerPos.lat.toFixed(5);
      const lng = centerPos.lng.toFixed(5);
      const zoom = map.getZoom().toFixed(5);
      const hash = `#map=${zoom}/${lat}/${lng}`
      window.location.hash = hash;
      const mapNavLinks = ["#nav-main-link", "#nav-edit-link", "#nav-history-link"];
      for (const linkId of mapNavLinks) {
        const $navLink = $(linkId);
        const url = new URL($navLink.prop("href"));
        url.hash = hash;
        $navLink.attr("href", url.href);
      }
      window.ottm.setReferer();
    }
  }

  /**
   * Center the view from the URL’s hash.
   */
  function centerViewFromUrl() {
    if (updatingHash) {
      updatingHash = false;
    } else {
      const {pos: [lat, lng, zoom], found} = getPositionFromURL();
      if (found) {
        updatingView = true;
        map.setZoom(zoom);
        map.setCenter({lat: lat, lng: lng});
      } else {
        updateUrlHash();
      }
    }
  }
}