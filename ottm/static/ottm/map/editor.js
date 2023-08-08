class MapEditor {
  #map;
  /**
   * The currently selected feature.
   * @type {MapEditor.Marker|MapEditor.VertexMarker|MapEditor.Polyline|MapEditor.Polygon|null}
   */
  #selectedFeature = null;
  /**
   * Used to ignore the "click" event fired by the map right after a polyline or polygon is clicked.
   * @type {boolean}
   */
  #layerClicked = false;
  /**
   * Used to ignore the "contextmenu" event fired by the map when right-clicking a feature.
   * @type {boolean}
   */
  #isFeatureMenuVisible = false;
  /**
   * @type {MapEditor.Polyline|MapEditor.Polygon|null}
   */
  #drawing = null;
  /**
   * @type {{feature:MapEditor.Polyline|MapEditor.Polygon,latlng:L.LatLng,to:MapEditor.Polyline|MapEditor.Polygon}|null}
   */
  #snap = null;
  /**
   * Panel containing forms to edit map features.
   * @type {MapEditorPanel}
   */
  #editorPanel = new MapEditorPanel("editor-panel");

  Marker;
  VertexMarker;
  Polyline;
  Polygon;

  constructor() {
    const thisEditor = this;

    /**
     * @param selected {boolean}
     */
    const setSelected = function (selected) {
      const v = this.hasOwnProperty("_icon") ? this._icon : this._path;
      if (selected) {
        L.DomUtil.addClass(v, "layer-selected");
      } else {
        L.DomUtil.removeClass(v, "layer-selected");
      }
    };

    /**
     * @param latlng {L.LatLng}
     * @return {MapEditor.VertexMarker|null}
     */
    const getVertexMarker = function (latlng) {
      return null; // TODO
    }

    this.Marker = L.Marker.extend({
      initialize: function (latlngs, options) {
        L.Marker.prototype.initialize.call(this, latlngs, options);
        this.on("click", () => {
          thisEditor.#updateSelection(this);
        });
        this.on("contextmenu", () => {
          thisEditor.#onContextMenu(this);
        });
      },

      setSelected: setSelected,
    });

    this.VertexMarker = L.Editable.VertexMarker.extend({
      initialize: function (latlng, latlngs, editor, options) {
        L.Editable.VertexMarker.prototype.initialize.call(this, latlng, latlngs, editor, options);
        this.on("click", () => {
          thisEditor.#updateSelection(this);
        });
        this.on("contextmenu", () => {
          thisEditor.#onContextMenu(this);
        });
      },

      /**
       * @param selected {boolean}
       */
      setSelected: function (selected) {
        if (!this._icon) {
          return;
        }
        setSelected.call(this, selected)
      },
    });

    // TODO make draggable
    this.Polyline = L.Polyline.extend({
      initialize: function (latlngs, options) {
        // TODO set style options depending on underlying model data type
        options.weight = 4;
        options.color = "#fff";
        L.Polyline.prototype.initialize.call(this, latlngs, options);
        this.on("click", function () {
          thisEditor.#layerClicked = true;
          thisEditor.#updateSelection(this);
        });
        this.on("contextmenu", () => {
          thisEditor.#isFeatureMenuVisible = true;
          thisEditor.#onContextMenu(this);
        });
      },

      setSelected: setSelected,

      getVertexMarker: getVertexMarker,
    });

    // TODO make draggable
    this.Polygon = L.Polygon.extend({
      initialize: function (latlngs, options) {
        // TODO set style options depending on underlying model data type
        options.weight = 4;
        options.color = "#fff";
        L.Polygon.prototype.initialize.call(this, latlngs, options);
        this.on("click", function () {
          thisEditor.#layerClicked = true;
          thisEditor.#updateSelection(this);
        });
        this.on("contextmenu", () => {
          thisEditor.#isFeatureMenuVisible = true;
          thisEditor.#onContextMenu(this);
        });
      },

      setSelected: setSelected,

      getVertexMarker: getVertexMarker,
    });
  }

  /**
   * Set the feature to show in the editor panel.
   *
   * @param feature {MapEditor.Marker|MapEditor.VertexMarker|MapEditor.Polyline|MapEditor.Polygon|null}
   *  Feature to show in the editor panel. May be null.
   */
  #updateSelection(feature) {
    this.#selectedFeature?.setSelected(false);
    this.#selectedFeature = feature;
    this.#selectedFeature?.setSelected(true);
    this.#editorPanel.setFeature(feature);
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
    };
  }

  /**
   * Hook the editor to the given map.
   *
   * @param map A Leaflet map object.
   */
  initEditor(map) {
    this.#map = map;

    const EditControl = L.Control.extend({
      options: {
        position: "topcenter",
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

    const snapHandler = new L.Handler.MarkerSnap(map, null, {
      onlyVertices: true,
    });
    const snapMarker = L.marker(map.getCenter(), {
      icon: map.editTools.createVertexIcon({className: "leaflet-div-icon leaflet-drawing-icon"}),
      zIndexOffset: 1000
    });
    snapHandler.watchMarker(snapMarker);

    const addSnapGuide = g => {
      if (!(g instanceof this.Marker)) {
        snapHandler.addGuideLayer(g);
      }
    };

    function removeSnapGuide(g) {
      const i = snapHandler._guides.indexOf(g);
      if (i >= 0) {
        // No clean way to remove a guide from the list
        snapHandler._guides.splice(i, 1);
      }
    }

    function followMouse(e) {
      snapMarker.setLatLng(e.latlng);
    }

    map.on("click", () => {
      // Prevent instant deselection when clicking polylines/polygons
      if (this.#layerClicked) {
        this.#layerClicked = false;
        return;
      }
      this.#updateSelection(null);
    });
    map.on("contextmenu", () => {
      if (this.#isFeatureMenuVisible) {
        this.#isFeatureMenuVisible = false;
        return;
      }
      this.#onContextMenu(null);
    });
    // We have to remove the currently dragged feature from the guides list
    // as otherwise geometryutils would throw errors.
    // The object is added back into the list after the drag has stopped.
    map.on("editable:created", e => addSnapGuide(e.layer));
    map.on("editable:vertex:dragstart", e => {
      const feature = e.layer;
      const vertex = e.vertex;
      removeSnapGuide(feature);
      snapHandler.watchMarker(vertex);
      vertex.on("snap", ev => this.#onSnap(feature, vertex.latlng, ev.layer));
      vertex.on("unsnap", _ => this.#onUnsnap());
    });
    map.on("editable:vertex:dragend", e => {
      this.#mergeSnap();
      addSnapGuide(e.layer);
      snapHandler.unwatchMarker(e.vertex);
      e.vertex.off("snap");
      e.vertex.off("unsnap");
    });
    map.on("editable:drawing:start", e => {
      removeSnapGuide(e.layer);
      if (!(e.layer instanceof this.Marker)) {
        snapMarker.addTo(map);
        this.#drawing = e.layer;
      }
      map.on("mousemove", followMouse);
    });
    map.on("editable:drawing:end", e => {
      addSnapGuide(e.layer);
      map.off("mousemove", followMouse);
      snapMarker.remove();
      this.#drawing = null;
    });
    map.on("editable:drawing:click", e => {
      this.#mergeSnap();
      // Leaflet copies event data to another object when firing,
      // so the event object we have here is not the one fired by
      // Leaflet.Editable; it's not a deep copy though, so we can change
      // the other objects that have a reference here.
      const latlng = snapMarker.getLatLng();
      e.latlng.lat = latlng.lat;
      e.latlng.lng = latlng.lng;
    });
    // Continue editing on Ctrl+LMB on first or last vertex of polyline
    map.on("editable:vertex:ctrlclick editable:vertex:metakeyclick", e => { // TODO put in context menu
      e.vertex.continue();
    });
    map.on("editable:vertex:rawclick", e => {
      if (!(e.layer instanceof this.Marker)) {
        e.cancel(); // Disable default behavior: delete vertex
      }
    });
    snapMarker.on("snap", e => this.#onSnap(this.#drawing, e.latlng, e.layer));
    snapMarker.on("unsnap", () => this.#onUnsnap());

    $("#editor-panel").css({display: "block"}).addClass("split");
    $("#map").addClass("split");
    window.Split(["#editor-panel", "#map"], {
      sizes: [20, 80],
      minSize: [0, 100],
      gutterSize: 5,
    });

    this.#updateSelection(null);
  }

  /**
   * Register a vertex snap.
   *
   * @param feature {MapEditor.Polyline|MapEditor.Polygon} Feature being edited.
   * @param latlng {L.LatLng} Position of the snapped vertex from the feature.
   * @param to {MapEditor.Polyline|MapEditor.Polygon} Feature the vertex has been snapped to.
   */
  #onSnap(feature, latlng, to) {
    this.#snap = {
      feature: feature,
      latlng: latlng,
      to: to,
    };
  }

  /**
   * Unregister the current snap data.
   */
  #onUnsnap() {
    this.#snap = null;
  }

  /**
   * If #snap is not null, merge or create relevant vertices.
   */
  #mergeSnap() {
    if (!this.#snap) {
      return;
    }
    console.log("mergeSnap", this.#snap);
    const sourceFeature = this.#snap.feature;
    const targetFeature = this.#snap.to;
    const snapPoint = this.#snap.latlng;
    let sourceVertex = sourceFeature.getVertexMarker(snapPoint);
    let targetVertex = targetFeature.getVertexMarker(snapPoint);
    console.log(sourceVertex, targetVertex);
    // TODO merge vertices
  }

  /**
   * Show a context menu for the given object.
   *
   * @param feature {MapEditor.Marker|MapEditor.VertexMarker|MapEditor.Polyline|MapEditor.Polygon|null}
   *  Feature being edited.
   */
  #onContextMenu(feature) {
    this.#updateSelection(feature);
    // TODO context menu
    console.log(feature);
  }
}

class MapEditorPanel {
  #$title;

  /**
   * The feature being edited.
   * @type {MapEditor.Marker|MapEditor.VertexMarker|MapEditor.Polyline|MapEditor.Polygon|null}
   */
  #feature;

  /**
   * Create an editor panel.
   *
   * @param divID {string} ID of the div element to use as an editor panel.
   */
  constructor(divID) {
    const $div = $(`#${divID}`);
    this.#$title = $('<h1 id="editor-panel-title"></h1>');
    $div.append(this.#$title);
  }

  /**
   * Set the feature to edit.
   *
   * @param feature {MapEditor.Marker|MapEditor.VertexMarker|MapEditor.Polyline|MapEditor.Polygon|null}
   */
  setFeature(feature) {
    this.#feature = feature;
    if (feature) {
      this.#$title.text(ottm.translations.get("map.editor_panel.title.edit_feature"));
    } else {
      this.#$title.text(ottm.translations.get("map.editor_panel.title.select_feature"));
    }
  }
}
