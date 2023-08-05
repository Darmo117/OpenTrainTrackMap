class MapEditor {
  /**
   * The currently selected layer.
   * @type {null}
   */
  #selectedLayer = null;
  /**
   * Used to ignore the "click" event fired by the map right after a polyline or polygon is clicked.
   * @type {boolean}
   */
  #layerClicked = false;

  constructor() {
    const thisEditor = this;

    this.Marker = L.Marker.extend({
      initialize: function (latlngs, options) {
        L.Marker.prototype.initialize.call(this, latlngs, options);
        this.on("click", function () {
          thisEditor.#updateSelection(this);
        });
      },

      /**
       * @param selected {boolean}
       */
      setSelected: function (selected) {
        if (selected) {
          L.DomUtil.addClass(this._icon, "layer-selected");
        } else {
          L.DomUtil.removeClass(this._icon, "layer-selected");
        }
      },
    });

    this.VertexMarker = L.Editable.VertexMarker.extend({
      initialize: function (latlng, latlngs, editor, options) {
        L.Editable.VertexMarker.prototype.initialize.call(this, latlng, latlngs, editor, options);
        this.on("click", function () {
          thisEditor.#updateSelection(this);
        });
      },

      /**
       * @param selected {boolean}
       */
      setSelected: function (selected) {
        if (!this._icon) {
          return;
        }
        if (selected) {
          L.DomUtil.addClass(this._icon, "layer-selected");
        } else {
          L.DomUtil.removeClass(this._icon, "layer-selected");
        }
      },
    });

    this.Polyline = L.Polyline.extend({
      initialize: function (latlngs, options) {
        options.weight = 4;
        options.color = '#fff';
        L.Polyline.prototype.initialize.call(this, latlngs, options);
        this.on("click", function () {
          thisEditor.#layerClicked = true;
          thisEditor.#updateSelection(this);
        });
      },

      /**
       * @param selected {boolean}
       */
      setSelected: function (selected) {
        if (selected) {
          L.DomUtil.addClass(this._path, "layer-selected");
        } else {
          L.DomUtil.removeClass(this._path, "layer-selected");
        }
      },
    });

    this.Polygon = L.Polygon.extend({
      initialize: function (latlngs, options) {
        L.Polygon.prototype.initialize.call(this, latlngs, options);
        this.on("click", function () {
          thisEditor.#layerClicked = true;
          thisEditor.#updateSelection(this);
        });
      },

      /**
       * @param selected {boolean}
       */
      setSelected: function (selected) {
        if (selected) {
          L.DomUtil.addClass(this._path, "layer-selected");
        } else {
          L.DomUtil.removeClass(this._path, "layer-selected");
        }
      },
    });
  }

  #updateSelection(layer) {
    this.#selectedLayer?.setSelected(false);
    this.#selectedLayer = layer;
    this.#selectedLayer?.setSelected(true);
  }

  /**
   * Return the edit options for the map.
   */
  getMapEditOptions() {
    return {
      polylineClass: this.Polyline,
      polygonClass: this.Polygon,
      markerClass: this.Marker,
      vertexMarkerClass: this.VertexMarker,
      // middleMarkerClass: this.VertexMarker,
    };
  }

  /**
   * Hook the editor to the given map.
   *
   * @param map A Leaflet map object.
   */
  initEditor(map) {
    const EditControl = L.Control.extend({
      options: {
        position: "topleft",
      },

      onAdd: function (map) {
        const container = L.DomUtil.create("div", "leaflet-control leaflet-bar");
        const link = L.DomUtil.create("a", "", container);

        link.href = "#";
        link.title = ottm.translations.get(`map.controls.edit.${this.options.kind}.tooltip`);
        link.innerHTML = this.options.html;
        L.DomEvent.on(link, "click", L.DomEvent.stop)
          .on(link, "click", () => {
            window.LAYER = this.options.callback.call(map.editTools);
          }, this);

        return container;
      },
    });

    const NewMarkerControl = EditControl.extend({
      options: {
        callback: map.editTools.startMarker,
        kind: "new_marker",
        html: '<span class="mdi mdi-vector-point"></span>',
      }
    });

    const NewLineControl = EditControl.extend({
      options: {
        callback: map.editTools.startPolyline,
        kind: "new_line",
        html: '<span class="mdi mdi-vector-polyline"></span>',
      }
    });

    const NewPolygonControl = EditControl.extend({
      options: {
        callback: map.editTools.startPolygon,
        kind: "new_polygon",
        html: '<span class="mdi mdi-vector-polygon"></span>',
      }
    });

    map.addControl(new NewMarkerControl());
    map.addControl(new NewLineControl());
    map.addControl(new NewPolygonControl());

    const snapHandler = new L.Handler.MarkerSnap(map);
    const snapMarker = L.marker(map.getCenter(), {
      icon: map.editTools.createVertexIcon({className: "leaflet-div-icon leaflet-drawing-icon"}),
      zIndexOffset: 1000
    });
    snapHandler.watchMarker(snapMarker);

    function addSnapGuide(g) {
      snapHandler.addGuideLayer(g);
    }

    function removeSnapGuide(g) {
      // No clean way to remove a guide from the list
      snapHandler._guides.splice(snapHandler._guides.indexOf(g), 1);
    }

    function followMouse(e) {
      snapMarker.setLatLng(e.latlng);
    }

    map.on("click", () => {
      if (this.#layerClicked) {
        this.#layerClicked = false;
      } else {
        this.#updateSelection(null);
      }
    });
    map.on("contextmenu", function (e) {
      // Disable browser’s context menu
    });
    // We have to remove the currently dragged layer from the guides list
    // as otherwise geometryutils would throw errors.
    // The object is added back into the list after the drag has stopped.
    // TODO "merge" points on snap
    map.on("editable:created", e => {
      const layer = e.layer;
      addSnapGuide(layer);
      if (layer instanceof L.Marker) {
        // Markers do not fire "editable:vertex:*" events on their own
        layer.on("dragstart", () => {
          map.fire("editable:vertex:dragstart", {layer: layer, vertex: layer});
        });
        layer.on("dragend", () => {
          map.fire("editable:vertex:dragend", {layer: layer, vertex: layer});
        });
        layer.on("click", () => {
          map.fire("editable:vertex:rawclick", {layer: layer, vertex: layer});
        })
      }
    });
    map.on("editable:vertex:dragstart", e => {
      removeSnapGuide(e.layer);
      snapHandler.watchMarker(e.vertex);
    });
    map.on("editable:vertex:dragend", e => {
      addSnapGuide(e.layer);
      snapHandler.unwatchMarker(e.vertex);
    });
    map.on("editable:drawing:start", function (e) {
      removeSnapGuide(e.layer);
      snapMarker.addTo(map);
      this.on("mousemove", followMouse);
    });
    map.on("editable:drawing:end", function (e) {
      addSnapGuide(e.layer);
      this.off("mousemove", followMouse);
      snapMarker.remove();
    });
    map.on("editable:drawing:click", e => {
      // Leaflet copy event data to another object when firing,
      // so the event object we have here is not the one fired by
      // Leaflet.Editable; it's not a deep copy though, so we can change
      // the other objects that have a reference here.
      let latlng = snapMarker.getLatLng();
      e.latlng.lat = latlng.lat;
      e.latlng.lng = latlng.lng;
    });
    // Continue editing on Ctrl+LMB on first or last vertex of polyline
    map.on("editable:vertex:ctrlclick editable:vertex:metakeyclick", e => { // TODO put in context menu
      e.vertex.continue();
    });
    map.on("editable:vertex:rawclick", e => {
      if (!(e.layer instanceof L.Marker)) {
        e.cancel(); // Disable default behavior: delete vertex
      }
    });
  }
}
