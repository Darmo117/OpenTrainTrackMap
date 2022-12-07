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

  L.EditControl = L.Control.extend({
    options: {
      position: "topleft",
      callback: null,
      kind: "",
      html: ""
    },

    onAdd: function (map) {
      const container = L.DomUtil.create("div", "leaflet-control leaflet-bar");
      const link = L.DomUtil.create("a", "", container);

      link.href = "#";
      link.title = window.OTTM_MAP_CONFIG["trans"][`map.controls.edit.${this.options.kind}.tooltip`];
      link.innerHTML = this.options.html;
      L.DomEvent.on(link, "click", L.DomEvent.stop)
        .on(link, "click", () => {
          window.LAYER = this.options.callback.call(map.editTools);
        }, this);

      return container;
    },
  });

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
     * Map’s tile layers.
     * @type {Object<string, L.TileLayer>}
     */
    #layers;
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
     * List of markers.
     * @type {?[]}
     */
    #markers = [];
    /**
     * List of polylines.
     * @type {?[]}
     */
    #lines = [];
    /**
     * List of polygons.
     * @type {?[]}
     */
    #polygons = [];
    /**
     * User’s IP address.
     * @type {string}
     */
    #userIP;

    /**
     * Create a map wrapper object.
     * @param mapID {string} Map’s HTML tag ID.
     * @param editMode {boolean} Whether the map should be editable.
     */
    constructor(mapID, editMode) {
      this.#userIP = window.OTTM_MAP_CONFIG["user_ip"];

      const map = L.map(mapID, {
        zoomControl: false, // Remove default zoom control
        editable: editMode,
      }).setView([0, 0], 2);

      map.on("zoomend", () => this.updateUrl());
      map.on("moveend", () => this.updateUrl());
      map.on("resize", () => this.updateUrl());
      window.onhashchange = () => this.centerViewFromUrl();

      this.#zoomControl = L.control.zoom({
        zoomInTitle: window.OTTM_MAP_CONFIG["trans"]["map.controls.zoom_in.tooltip"],
        zoomOutTitle: window.OTTM_MAP_CONFIG["trans"]["map.controls.zoom_out.tooltip"],
        position: "topright",
      }).addTo(map);

      const osmTiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: 'Map data © <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);
      const mapnikBWTiles = L.tileLayer("https://tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png", {
        attribution: 'Map data © <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
        maxZoom: 18,
      });
      // Make call to server to hide API key
      const maptilerSatelliteTiles = L.tileLayer("/tile?provider=maptiler&x={x}&y={y}&z={z}", {
        attribution: 'Tiles © <a href="https://www.maptiler.com/copyright/" target="_blank">MapTiler</a>, Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });
      const esriSatelliteTiles = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: "Tiles © Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        maxZoom: 19,
      });

      this.#layers = {
        [window.OTTM_MAP_CONFIG["trans"]["map.controls.layers.standard"]]: osmTiles,
        [window.OTTM_MAP_CONFIG["trans"]["map.controls.layers.black_and_white"]]: mapnikBWTiles,
        [window.OTTM_MAP_CONFIG["trans"]["map.controls.layers.satellite_maptiler"]]: maptilerSatelliteTiles,
        [window.OTTM_MAP_CONFIG["trans"]["map.controls.layers.satellite_esri"]]: esriSatelliteTiles,
      };
      L.control.layers(this.#layers).addTo(map);

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
        tooltip: window.OTTM_MAP_CONFIG["trans"]["map.controls.google_maps_button.tooltip"],
        icon: window.OTTM_MAP_CONFIG["static_path"] + "ottm/images/Google_Maps_icon.svg.png",
        action: map => openMapInTab(map, "https://www.google.com/maps/@{lat},{long},{zoom}z"),
      }).addTo(map);
      L.control.button({
        label: window.OTTM_MAP_CONFIG["trans"]["map.controls.ign_compare_button.label"],
        tooltip: window.OTTM_MAP_CONFIG["trans"]["map.controls.ign_compare_button.tooltip"],
        action: map => openMapInTab(map, "https://remonterletemps.ign.fr/comparer/basic?x={long}&y={lat}&z={zoom}"),
      }).addTo(map);

      this.#scaleControl = L.control.scale().addTo(map);

      L.esri.Geocoding.geosearch({
        title: window.OTTM_MAP_CONFIG["trans"]["map.controls.search.tooltip"],
        placeholder: window.OTTM_MAP_CONFIG["trans"]["map.controls.search.placeholder"],
        expanded: true,
        collapseAfterResult: false,
        providers: [
          L.esri.Geocoding.arcgisOnlineProvider({
            apikey: '5PelNcEc4zGc3OEutmIG', // FIXME wrong key?
          }),
        ],
      }).addTo(map);
      // L.Control.geocoder({
      //   title: window.OTTM_MAP_CONFIG["trans"]["map.controls.search.tooltip"],
      //   placeholder: window.OTTM_MAP_CONFIG["trans"]["map.controls.search.placeholder"],
      //   expanded: true,
      //   collapseAfterResult: false,
      //   position: 'topleft',
      // }).addTo(map);

      if (editMode) {
        L.NewLineControl = L.EditControl.extend({
          options: {
            position: "topleft",
            callback: map.editTools.startPolyline,
            kind: "new_line",
            html: '<span class="mdi mdi-vector-polyline"></span>',
          }
        });

        L.NewPolygonControl = L.EditControl.extend({
          options: {
            position: "topleft",
            callback: map.editTools.startPolygon,
            kind: "new_polygon",
            html: '<span class="mdi mdi-vector-polygon"></span>',
          }
        });

        L.NewMarkerControl = L.EditControl.extend({
          options: {
            position: "topleft",
            callback: map.editTools.startMarker,
            kind: "new_marker",
            html: '<span class="mdi mdi-vector-point"></span>',
          }
        });

        map.addControl(new L.NewMarkerControl());
        map.addControl(new L.NewLineControl());
        map.addControl(new L.NewPolygonControl());
      }

      this.#map = map;
      if (this.getPositionFromURL()[1]) {
        this.centerViewFromUrl();
      } else {
        this.centerViewToUserLocation();
      }
      // Delete config object and script tag
      delete window.OTTM_MAP_CONFIG;
      $("#ottm-map-config").remove();
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

  window.ottm.map = new Map("map", window.OTTM_MAP_CONFIG["edit"]);
})();
