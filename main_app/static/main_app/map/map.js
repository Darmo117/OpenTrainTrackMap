"use strict";

(function () {
  L.Control.Button = L.Control.extend({
    options: {
      position: "topright",
      label: "Button",
      tooltip: null,
      icon: null,
      action: function () {
      },
    },

    onAdd: function (map) {
      let div = L.DomUtil.create("div", "leaflet-bar");
      let link = L.DomUtil.create("a");

      if (this.options.icon) {
        link.style.width = "40px";
        link.style.height = "40px";
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
    }
  });

  L.control.button = function (options) {
    return new L.Control.Button(options);
  }

  class Map {
    /**
     * @private
     */
    _map;
    /**
     * @type {Object<string, L.TileLayer>}
     * @private
     */
    _layers = {};
    /**
     * @type {L.Zoom}
     * @private
     */
    _zoomControl;
    /**
     * @type {L.Scale}
     * @private
     */
    _scaleControl;

    _updatingHash = false;
    _updatingView = false;

    constructor(mapId) {
      let map = L.map(mapId, {
        zoomControl: false, // Remove default zoom control
        editable: true,
      }).setView([0, 0], 2);

      map.on("zoomend", this.updateUrl.bind(this));
      map.on("moveend", this.updateUrl.bind(this));
      map.on("resize", this.updateUrl.bind(this));
      window.onhashchange = this.centerViewFromUrl.bind(this);

      let osmTiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: 'Map data © <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      let mapnikBWTiles = L.tileLayer("https://tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png", {
        attribution: 'Map data © <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
        maxZoom: 18,
      });

      // TODO cacher la clé
      let maptilerSatelliteTiles = L.tileLayer("https://api.maptiler.com/tiles/satellite/{z}/{x}/{y}.jpg?key=5PelNcEc4zGc3OEutmIG", {
        attribution: 'Tiles © <a href="https://www.maptiler.com/copyright/" target="_blank">MapTiler</a>, Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });

      let esriSatelliteTiles = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: "Tiles © Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        maxZoom: 19,
      });

      this._zoomControl = L.control.zoom({
        zoomInTitle: OTTM_CONFIG["trans"]["map.controls.zoom_in.tooltip"],
        zoomOutTitle: OTTM_CONFIG["trans"]["map.controls.zoom_out.tooltip"],
        position: "topright",
      }).addTo(map);

      this._layers = {
        [OTTM_CONFIG["trans"]["map.controls.layers.standard"]]: osmTiles,
        [OTTM_CONFIG["trans"]["map.controls.layers.black_and_white"]]: mapnikBWTiles,
        [OTTM_CONFIG["trans"]["map.controls.layers.satellite_maptiler"]]: maptilerSatelliteTiles,
        [OTTM_CONFIG["trans"]["map.controls.layers.satellite_esri"]]: esriSatelliteTiles,
      };
      L.control.layers(this._layers).addTo(map);

      function openMapInTab(map, urlPattern) {
        let latLong = map.getCenter();
        let lat = latLong.lat;
        let long = latLong.lng;
        let zoom = map.getZoom();
        window.open(urlPattern
            .replace("{lat}", lat)
            .replace("{long}", long)
            .replace("{zoom}", zoom))
      }

      L.control.button({
        tooltip: OTTM_CONFIG["trans"]["map.controls.google_maps_button.tooltip"],
        icon: OTTM_CONFIG["static_path"] + "main_app/images/22px-Google_Maps_icon.webp",
        action: function (map) {
          openMapInTab(map, "https://www.google.com/maps/@{lat},{long},{zoom}z");
        },
      }).addTo(map);
      L.control.button({
        label: OTTM_CONFIG["trans"]["map.controls.ign_compare_button.label"],
        tooltip: OTTM_CONFIG["trans"]["map.controls.ign_compare_button.tooltip"],
        action: function (map) {
          openMapInTab(map, "https://remonterletemps.ign.fr/comparer/basic?x={long}&y={lat}&z={zoom}");
        },
      }).addTo(map);

      this._scaleControl = L.control.scale().addTo(map);

      // noinspection JSUnresolvedVariable,JSUnresolvedFunction
      L.esri.Geocoding.geosearch({
        title: OTTM_CONFIG["trans"]["map.controls.search.tooltip"],
        placeholder: OTTM_CONFIG["trans"]["map.controls.search.placeholder"],
        expanded: true,
        collapseAfterResult: false,
      }).addTo(map);

      // let editableLayers = (new L.FeatureGroup()).addTo(map);
      // (new L.Control.Draw({
      //   position: 'topleft',
      //   edit: {
      //     featureGroup: editableLayers,
      //     remove: true,
      //   },
      // })).addTo(map);
      //
      // map.on(L.Draw.Event.CREATED, function (e) {
      //   let type = e.layerType,
      //       layer = e.layer;
      //
      //   if (type === "marker") {
      //     layer.bindPopup("A popup!");
      //   }
      //
      //   editableLayers.addLayer(layer);
      // });

      // map.locate({setView: true, maxZoom: 16}); // TODO

      let polyline = L.polyline([[43.1, 1.2], [43.2, 1.3], [43.3, 1.2]]).addTo(map);
      polyline.enableEdit();

      this._map = map;
      this.centerViewFromUrl();

      delete window.OTTM_CONFIG;
    }

    updateUrl() {
      if (this._updatingView) {
        this._updatingView = false;
      } else {
        this._updatingHash = true;
        let zoom = this._map.getZoom();
        let centerPos = this._map.getCenter();
        let lat = parseFloat(centerPos.lat).toFixed(5);
        let long = parseFloat(centerPos.lng).toFixed(5);
        let hash = `#map=${zoom}/${lat}/${long}`
        window.location.hash = hash;

        let mapNavLinks = ["#nav-main-link", "#nav-edit-link", "#nav-history-link"];
        for (let linkId of mapNavLinks) {
          let $navLink = $(linkId);
          let url = new URL($navLink.prop("href"));
          url.hash = hash;
          $navLink.attr("href", url.href);
        }
        ottm.setReferer();
      }
    }

    centerViewFromUrl() {
      if (this._updatingHash) {
        this._updatingHash = false;
      } else {
        let lat, long, zoom;
        let match = /^#map=(\d+)\/(-?\d+\.?\d*)\/(-?\d+\.?\d*)$/.exec(window.location.hash);

        if (match) {
          this._updatingView = true;
          let minZoom = this._map.getMinZoom();
          let maxZoom = this._map.getMaxZoom();

          zoom = Math.max(minZoom, Math.min(maxZoom, parseInt(match[1])));
          lat = parseFloat(match[2]);
          long = parseFloat(match[3]);

          this._map.setView([lat, long], zoom);
        } else {
          this.updateUrl();
        }
      }
    }

    get leafletMap() {
      return this._map;
    }
  }

  window.ottm.map = new Map("map");
  window.ottm.Map = Map;
})();
