/**
 * Script for the Leaflet map view.
 */
"use strict";

(function () {
  L.Control.Button = L.Control.extend({
    options: {
      position: "topright",
      label: "Button",
      tooltip: null,
      icon: null,
      action: () => {
      },
    },

    onAdd: function (map) {
      const div = L.DomUtil.create("div", "leaflet-bar");
      const link = L.DomUtil.create("a");

      if (this.options.icon) {
        link.style.width = "30px";
        link.style.height = "30px";
        link.style.backgroundImage = `url("${this.options.icon}")`;
      } else {
        link.innerHTML = this.options.label;
      }
      link.title = this.options.tooltip || this.options.label;
      link.href = "#";
      link.onclick = () => this.options.action(map);
      div.appendChild(link);

      return div;
    },

    onRemove: function (map) {
      // Nothing to do here
    },
  });

  L.control.button = options => new L.Control.Button(options);

  /**
   * Wrapper class around a Leaflet map object.
   * Adds various buttons to control the map’s view.
   * Uses the page’s URL hash to update the view and vice-versa.
   */
  class Map {
    /**
     * Leaflet map object.
     */
    #map;
    /**
     * Map’s base tile layers.
     * @type {Object<string, L.TileLayer>}
     */
    #baseLayers;
    /**
     * Map’s overlay layers.
     * @type {Object<string, L.Layer>}
     */
    #overlayLayers = {};
    /**
     * View zoom control.
     * @type {L.Zoom}
     */
    #zoomControl;
    /**
     * View scale control.
     * @type {L.Scale}
     */
    #scaleControl;
    /**
     * Indicates whether the page’s URL hash is being updated from the map’s view.
     * @type {boolean}
     */
    #updatingHash = false;
    /**
     * Indicates whether the map’s view is being updated from the page’s URL hash.
     * @type {boolean}
     */
    #updatingView = false;

    /**
     * Create a map wrapper object.
     * @param mapID {string} Map’s HTML tag ID.
     * @param editable {boolean} Whether the map should be editable.
     */
    constructor(mapID, editable) {
      // Add center position
      // Code from https://stackoverflow.com/a/60391674/3779986
      L.Map.include({
        _initControlPos: function () {
          const l = "leaflet-";
          this._controlCorners = {};
          this._controlContainer = L.DomUtil.create("div", l + "control-container", this._container);

          const createCorner = (vSide, hSide) => {
            const className = l + vSide + " " + l + hSide;
            this._controlCorners[vSide + hSide] = L.DomUtil.create("div", className, this._controlContainer);
          };

          createCorner("top", "left");
          createCorner("top", "right");
          createCorner("bottom", "left");
          createCorner("bottom", "right");
          createCorner("top", "center");
          createCorner("bottom", "center");
        }
      });

      const editor = editable ? new MapEditor() : null;
      const map = L.map(mapID, {
        zoomControl: false, // Remove default zoom control
        editable: editable,
        editOptions: editable ? editor.getMapEditOptions() : {},
      }).setView([0, 0], 2);
      if (editable) {
        editor.initEditor(map);
      }

      map.off("dblclick"); // Disable zoom-in on double-click
      map.on("zoomend", () => this.updateUrl());
      map.on("moveend", () => this.updateUrl());
      map.on("resize", () => this.updateUrl());
      window.onhashchange = () => this.centerViewFromUrl();

      this.#zoomControl = L.control.zoom({
        zoomInTitle: ottm.translations.get("map.controls.zoom_in.tooltip"),
        zoomOutTitle: ottm.translations.get("map.controls.zoom_out.tooltip"),
        position: "topright",
      }).addTo(map);

      const osmGrayscaleTiles = L.tileLayer.grayscale("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: 'Map data © <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });
      const osmColoredTiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: 'Map data © <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });
      const maptilerSatelliteTiles = L.tileLayer("/tile?provider=maptiler&x={x}&y={y}&z={z}", {
        attribution: 'Tiles © <a href="https://www.maptiler.com/copyright/" target="_blank">MapTiler</a>, Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });
      const esriSatelliteTiles = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        maxZoom: 19,
      });
      const googleSatelliteTiles = L.tileLayer('http://www.google.com/maps/vt?lyrs=s@189&x={x}&y={y}&z={z}', { // lyrs=s@189 -> satellite images
        attribution: 'Tiles © Google',
        maxZoom: 18,
      });

      if (editable) {
        maptilerSatelliteTiles.addTo(map);
      } else {
        osmGrayscaleTiles.addTo(map);
      }

      this.#baseLayers = {
        [ottm.translations.get("map.controls.layers.base.black_and_white")]: osmGrayscaleTiles,
        [ottm.translations.get("map.controls.layers.base.colored")]: osmColoredTiles,
        [ottm.translations.get("map.controls.layers.base.satellite_maptiler")]: maptilerSatelliteTiles,
        [ottm.translations.get("map.controls.layers.base.satellite_esri")]: esriSatelliteTiles,
        [ottm.translations.get("map.controls.layers.base.satellite_google")]: googleSatelliteTiles,
      };

      L.control.layers(this.#baseLayers, this.#overlayLayers).addTo(map);

      /**
       * Open the current view in the given online mapping service.
       * @param map Leaflet map object.
       * @param urlPattern {string} Mapping service’s URL pattern.
       */
      function openMapInTab(map, urlPattern) {
        const latLong = map.getCenter();
        window.open(urlPattern
          .replace("{lat}", latLong.lat)
          .replace("{long}", latLong.lng)
          .replace("{zoom}", map.getZoom()))
      }

      L.control.button({
        tooltip: ottm.translations.get("map.controls.google_maps_button.tooltip"),
        icon: `${ottm.config.get("staticPath")}ottm/images/Google_Maps_icon.svg.png`,
        action: map => openMapInTab(map, "https://www.google.com/maps/@{lat},{long},{zoom}z"),
      }).addTo(map);
      L.control.button({
        label: "IGN",
        tooltip: ottm.translations.get("map.controls.ign_compare_button.tooltip"),
        action: map => openMapInTab(map, "https://remonterletemps.ign.fr/comparer/basic?x={long}&y={lat}&z={zoom}"),
      }).addTo(map);

      this.#scaleControl = L.control.scale().addTo(map);

      // TODO restrict API key usage to production site’s host only (will require a new key)
      //  cf. https://documentation.maptiler.com/hc/en-us/articles/360020806037-Protect-your-map-key
      const c = L.control.maptilerGeocoding({
        apiKey: "5PelNcEc4zGc3OEutmIG",
      }).setPosition("topleft").addTo(map);
      const $control = $(c._container);
      $control.addClass("leaflet-bar");
      $control.find("input").attr("placeholder", ottm.translations.get("map.controls.search.placeholder"));
      $control.find("button.search-button svg").remove()
      $control.find("button.search-button").append('<span class="mdi mdi-magnify"></span>');
      $control.find("button.clear-button-container svg").remove()
      $control.find("button.clear-button-container").append('<span class="mdi mdi-window-close"></span>');

      this.#map = map;
      if (this.getPositionFromURL()[1]) {
        this.centerViewFromUrl();
      } else {
        this.centerViewToUserLocation();
      }
      // Delete config object and script tag
      delete window.OTTM_MAP_CONFIG;
      $("#ottm-map-config-script").remove();
    }

    /**
     * Ask the client if they want to allow geolocation.
     * If yes, the map view is centered on the position returned by the browser.
     * @async
     */
    centerViewToUserLocation() {
      navigator.permissions.query({name: "geolocation"}).then(result => {
        if (result.state === "granted" || result.state === "prompt") {
          navigator.geolocation.getCurrentPosition(
            p => this.#map.setView([p.coords.latitude, p.coords.longitude], 13),
            e => {
              console.log(e.message);
              this.updateUrl();
            },
            {
              enableHighAccuracy: false,
              maximumAge: 30000,
              timeout: 20000,
            }
          );
        } else if (result.state === "denied") {
          console.log("User does not allow geolocation");
          this.updateUrl();
        }
      });
    }

    getPositionFromURL() {
      const match = /^#map=(\d+)\/(-?\d+\.?\d*)\/(-?\d+\.?\d*)$/.exec(window.location.hash);
      if (match) {
        const minZoom = this.#map.getMinZoom();
        const maxZoom = this.#map.getMaxZoom();
        const zoom = Math.max(minZoom, Math.min(maxZoom, parseInt(match[1])));
        const lat = parseFloat(match[2]);
        const long = parseFloat(match[3]);
        return [[lat, long, zoom], true];
      }
      return [[0, 0, 15], false];
    }

    /**
     * Update page’s URL hash from the current map view.
     */
    updateUrl() {
      if (this.#updatingView) {
        this.#updatingView = false;
      } else {
        this.#updatingHash = true;
        const centerPos = this.#map.getCenter();
        const lat = parseFloat(centerPos.lat).toFixed(5);
        const long = parseFloat(centerPos.lng).toFixed(5);
        const hash = `#map=${this.#map.getZoom()}/${lat}/${long}`
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
    centerViewFromUrl() {
      if (this.#updatingHash) {
        this.#updatingHash = false;
      } else {
        const [[lat, long, zoom], found] = this.getPositionFromURL();
        if (found) {
          this.#updatingView = true;
          this.#map.setView([lat, long], zoom);
        } else {
          this.updateUrl();
        }
      }
    }

    /**
     * @return {L.Map} The Leaflet map object.
     */
    get leafletMap() {
      return this.#map;
    }
  }

  // noinspection JSCheckFunctionSignatures
  ottm.map = new Map("map", window.OTTM_MAP_CONFIG["edit"]);
})();
