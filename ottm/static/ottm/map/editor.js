import * as L from "../libs/leaflet/leaflet-src.esm.js";
import {Editable as LeafletEditable} from "../libs/leaflet/plugins/Leaflet.Editable.js";
import "../libs/leaflet/plugins/leaflet.snap.js";
import "../libs/split.min.js";

// region Common functions for Marker, VertexMarker, Polyline and Polygon classes.

/**
 * @param editor {MapEditor}
 */
const setMapEditor = function (editor) {
  this._mapEditor = editor;
}

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
 * @return {VertexMarker|null}
 */
const getVertexMarker = function (latlng) {
  for (const marker of this._markers) {
    if (marker.getLatLng().equals(latlng)) {
      return marker;
    }
  }
  return null;
}

// endregion Commons
// region Feature sub-classes

const Marker = L.Marker.extend({
  initialize: function (latlngs, options) {
    L.Marker.prototype.initialize.call(this, latlngs, options);

    /**
     * Reference to the map editor.
     * @type {MapEditor}
     */
    this._mapEditor = null;

    this.on("click", () => {
      this._mapEditor.updateSelection(this);
    });
    this.on("contextmenu", () => {
      this._mapEditor.onContextMenu(this);
    });
  },

  /**
   * Set the map editor.
   *
   * @param editor {MapEditor}
   */
  setMapEditor: setMapEditor,

  /**
   * Set the selection of this feature.
   *
   * @param selected {boolean}
   */
  setSelected: setSelected,
});

const VertexMarker = LeafletEditable.VertexMarker.extend({
  initialize: function (latlng, latlngs, editor, options) {
    LeafletEditable.VertexMarker.prototype.initialize.call(this, latlng, latlngs, editor, options);

    /**
     * Reference to the map editor.
     * @type {MapEditor}
     */
    this._mapEditor = null;
    /**
     * List of vertices this one is pinned to.
     * Only vertex markers are pinnable.
     * @type {Set<VertexMarker>}
     */
    this._pinnedTo = new Set();

    this.on("click", () => {
      this._mapEditor.updateSelection(this);
    });
    this.on("contextmenu", () => {
      this._mapEditor.onContextMenu(this);
    });
  },

  /**
   * Set the map editor.
   *
   * @param editor {MapEditor}
   */
  setMapEditor: setMapEditor,

  /**
   * Set the selection of this feature.
   *
   * @param selected {boolean}
   */
  setSelected: function (selected) {
    if (!this._icon) {
      return;
    }
    setSelected.call(this, selected)
  },

  onDrag: function (e, propagate = true) {
    console.log(this, propagate); // DEBUG
    LeafletEditable.VertexMarker.prototype.onDrag.call(this, e);
    if (propagate) {
      this._pinnedTo.forEach(v => {
        v.onDrag(e, false); // FIXME doesn’t move v
        // v._latlng = this._latlng;
        // console.log(v); // DEBUG
      });
    }
  },

  /**
   * Pin this vertex to the given one.
   *
   * @param vertex {VertexMarker}
   */
  pinTo: function (vertex) {
    if (this._pinnedTo.has(vertex)) {
      return;
    }
    this._pinnedTo.add(vertex);
    this._pinnedTo.forEach(v => {
      if (v === vertex) {
        return;
      }
      v.pinTo(vertex);
    });
    vertex.pinTo(this);
    console.log(this._pinnedTo.size, this.editor.feature._path); // DEBUG
  }
});

// TODO make draggable from context menu
const Polyline = L.Polyline.extend({
  initialize: function (latlngs, options) {
    // TODO set style options depending on underlying model data type
    options.weight = 4;
    options.color = "#fff";
    L.Polyline.prototype.initialize.call(this, latlngs, options);

    /**
     * Reference to the map editor.
     * @type {MapEditor}
     */
    this._mapEditor = null;
    /** @type {VertexMarker[]} */
    this._markers = [];

    this.on("click", function () {
      this._mapEditor.updateSelection(this);
    });
    this.on("contextmenu", () => {
      this._mapEditor.isFeatureMenuVisible = true;
      this._mapEditor.onContextMenu(this);
    });
    this.on("editable:vertex:new", e => {
      const latLngs = this.getLatLngs();
      const vertexPos = e.vertex.getLatLng();
      for (let i = 0, n = latLngs.length; i < n; i++) {
        if (vertexPos.equals(latLngs[i])) {
          this._markers.splice(i, 0, e.vertex); // Insert new vertex at i
        }
      }
      this._mapEditor.mergeVertices();
    });
  },

  /**
   * Set the map editor.
   *
   * @param editor {MapEditor}
   */
  setMapEditor: setMapEditor,

  /**
   * Set the selection of this feature.
   *
   * @param selected {boolean}
   */
  setSelected: setSelected,

  /**
   * Return the VertexMarker at the given position.
   *
   * @param latlng {L.LatLng} Vertex’ position.
   * @return {VertexMarker|null} The marker or null if none matched.
   */
  getVertexMarker: getVertexMarker,
});

// TODO make draggable from context menu
const Polygon = L.Polygon.extend({
  initialize: function (latlngs, options) {
    // TODO set style options depending on underlying model data type
    options.weight = 4;
    options.color = "#fff";
    L.Polygon.prototype.initialize.call(this, latlngs, options);

    /**
     * Reference to the map editor.
     * @type {MapEditor}
     */
    this._mapEditor = null;
    /** @type {VertexMarker[]} */
    this._markers = [];

    this.on("click", function () {
      this._mapEditor.updateSelection(this);
    });
    this.on("contextmenu", () => {
      this._mapEditor.isFeatureMenuVisible = true;
      this._mapEditor.onContextMenu(this);
    });
    this.on("editable:vertex:new", e => {
      const latLngs = this.getLatLngs()[0];
      const vertexPos = e.vertex.getLatLng();
      for (let i = 0, n = latLngs.length; i < n; i++) {
        if (vertexPos.equals(latLngs[i])) { // FIXME last middle marker added to start
          this._markers.splice(i, 0, e.vertex); // Insert new vertex at i
        }
      }
      this._mapEditor.mergeVertices();
    });
  },

  /**
   * Set the map editor.
   *
   * @param editor {MapEditor}
   */
  setMapEditor: setMapEditor,

  /**
   * Set the selection of this feature.
   *
   * @param selected {boolean}
   */
  setSelected: setSelected,

  /**
   * Return the VertexMarker at the given position.
   *
   * @param latlng {L.LatLng} Vertex’ position.
   * @return {VertexMarker|null} The marker or null if none matched.
   */
  getVertexMarker: getVertexMarker,
});

// endregion

class SnapData {
  /** @type {Polyline|Polygon} */
  feature;
  /** @type {Polyline|Polygon} */
  to;
  /** @type {VertexMarker|null} */
  draggedVertex = null;
  /** @type {L.LatLng} */
  latlng;

  /**
   * @param feature {Polyline|Polygon} Feature being edited.
   * @param to {Polyline|Polygon} Feature the vertex has been snapped to.
   * @param draggedVertex {VertexMarker|null} Vertex being dragged and snapped. Null if drawing.
   * @param latlng {L.LatLng} Position of the snapped vertex from the feature.
   */
  constructor(feature, to, draggedVertex, latlng) {
    this.feature = feature;
    this.to = to;
    this.draggedVertex = draggedVertex;
    this.latlng = latlng;
  }
}

export class MapEditor {
  // region Fields
  #map;
  /**
   * The currently selected feature.
   * @type {Marker|VertexMarker|Polyline|Polygon|null}
   */
  #selectedFeature = null;
  /**
   * Used to ignore the "click" event fired by the map right after a polyline or polygon is clicked.
   * @type {boolean}
   */
  #ignoreNextMapClick = false;
  /**
   * Used to ignore the "contextmenu" event fired by the map when right-clicking a feature.
   * @type {boolean}
   */
  #isFeatureMenuVisible = false;
  /**
   * @type {Polyline|Polygon|null}
   */
  #drawing = null;
  /**
   * @type {SnapData|null}
   */
  #snapData = null;
  /**
   * Panel containing forms to edit map features.
   * @type {MapEditorPanel}
   */
  #editorPanel = new MapEditorPanel("editor-panel");
  // endregion

  constructor() {
    this.#injectMixins();
  }

  #injectMixins() {
    const thisEditor = this;
    // Replace LeafletEditable.PathEditor.addVertexMarker() by a custom function
    // that passes this editor instance to the new VertexMarker
    const addVertexMarker = LeafletEditable.PathEditor.prototype.addVertexMarker; // Local copy to avoid recursion loop
    LeafletEditable.PathEditor.include({
      addVertexMarker: function (latlng, latlngs) {
        const vertexMarker = addVertexMarker.call(this, latlng, latlngs);
        vertexMarker.setMapEditor(thisEditor);
        return vertexMarker;
      },
    });
  }

  /**
   * Return the edit options for the map.
   */
  getMapEditOptions() {
    return {
      polylineClass: Polyline,
      polygonClass: Polygon,
      markerClass: Marker,
      vertexMarkerClass: VertexMarker,
    };
  }

  /**
   * Hook the editor to the given map.
   *
   * @param map A Leaflet map object.
   */
  initEditor(map) {
    this.#map = map;

    // region Edit control classes
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
        callback: (latlng, options) => {
          const marker = map.editTools.startMarker(latlng, options);
          marker.setMapEditor(this);
          return marker;
        },
        kind: "new_marker",
        html: '<span class="mdi mdi-vector-point"></span>',
      }
    });

    const NewLineControl = EditControl.extend({
      options: {
        callback: (latlng, options) => {
          const polyline = map.editTools.startPolyline(latlng, options);
          polyline.setMapEditor(this);
          return polyline;
        },
        kind: "new_line",
        html: '<span class="mdi mdi-vector-polyline"></span>',
      }
    });

    const NewPolygonControl = EditControl.extend({
      options: {
        callback: (latlng, options) => {
          const polygon = map.editTools.startPolygon(latlng, options);
          polygon.setMapEditor(this);
          return polygon;
        },
        kind: "new_polygon",
        html: '<span class="mdi mdi-vector-polygon"></span>',
      }
    });
    // endregion

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
      if (!(g instanceof Marker)) {
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
      if (this.#ignoreNextMapClick) {
        this.#ignoreNextMapClick = false;
        return;
      }
      this.updateSelection(null);
    });
    map.on("contextmenu", () => {
      if (this.#isFeatureMenuVisible) {
        this.#isFeatureMenuVisible = false;
        return;
      }
      this.onContextMenu(null);
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
      vertex.on("snap", ev => {
        this.#onSnap(feature, vertex, ev.latlng, ev.layer);
      });
      vertex.on("unsnap", _ => this.#onUnsnap());
    });
    map.on("editable:vertex:dragend", e => {
      addSnapGuide(e.layer);
      snapHandler.unwatchMarker(e.vertex);
      e.vertex.off("snap");
      e.vertex.off("unsnap");
      L.DomUtil.removeClass(e.vertex._icon, "marker-snapped");
      if (this.#snapData?.draggedVertex) {
        // Fix actual position of dragged vertex if snapped
        // noinspection JSUnresolvedReference
        const ll = this.#snapData.draggedVertex._latlng;
        ll.lat = this.#snapData.latlng.lat;
        ll.lng = this.#snapData.latlng.lng;
      }
      this.mergeVertices();
    });
    map.on("editable:drawing:start", e => {
      removeSnapGuide(e.layer);
      if (!(e.layer instanceof Marker)) {
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
      // Leaflet copies event data to another object when firing,
      // so the event object we have here is not the one fired by
      // LeafletEditable; it's not a deep copy though, so we can change
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
      if (!(e.layer instanceof Marker)) {
        e.cancel(); // Disable default behavior: delete vertex
      }
    });
    snapMarker.on("snap", e => this.#onSnap(this.#drawing, null, e.latlng, e.layer));
    snapMarker.on("unsnap", () => this.#onUnsnap());

    $("#editor-panel").css({display: "block"}).addClass("split");
    $("#map").addClass("split");
    window.Split(["#editor-panel", "#map"], {
      sizes: [20, 80],
      minSize: [0, 100],
      gutterSize: 5,
    });

    this.updateSelection(null);
  }

  /**
   * Set the feature to show in the editor panel.
   *
   * @param feature {Marker|VertexMarker|Polyline|Polygon|null} Feature to show in the editor panel. May be null.
   */
  updateSelection(feature) {
    this.#ignoreNextMapClick = feature instanceof Polyline || feature instanceof Polygon;
    if (feature && feature === this.#selectedFeature) {
      return;
    }
    this.#selectedFeature?.setSelected(false);
    this.#selectedFeature = feature;
    this.#selectedFeature?.setSelected(true);
    this.#editorPanel.setFeature(feature);
  }

  /**
   * Show a context menu for the given object.
   *
   * @param feature {Marker|VertexMarker|Polyline|Polygon|null} Feature being edited.
   */
  onContextMenu(feature) {
    this.updateSelection(feature);
    // TODO context menu
    console.log(feature); // DEBUG
  }

  /**
   * If this.#snapData is not null, merge relevant vertices.
   */
  mergeVertices() {
    if (!this.#snapData) {
      return;
    }
    const sourceFeature = this.#snapData.feature;
    const targetFeature = this.#snapData.to;
    const snapPoint = this.#snapData.latlng;
    const sourceVertex = sourceFeature.getVertexMarker(snapPoint);
    const targetVertex = targetFeature.getVertexMarker(snapPoint);
    sourceVertex.pinTo(targetVertex);
  }

  /**
   * Register a vertex snap.
   *
   * @param feature {Polyline|Polygon} Feature being edited.
   * @param draggedVertex {VertexMarker|null} Vertex being dragged and snapped. Null if drawing.
   * @param latlng {L.LatLng} Position of the snapped vertex from the feature.
   * @param to {Polyline|Polygon} Feature the vertex has been snapped to.
   */
  #onSnap(feature, draggedVertex, latlng, to) {
    this.#snapData = new SnapData(
      feature,
      to,
      draggedVertex,
      latlng,
    );
  }

  /**
   * Unregister the current snap data.
   */
  #onUnsnap() {
    this.#snapData = null;
  }
}

class MapEditorPanel {
  #$title;

  /**
   * The feature being edited.
   * @type {Marker|VertexMarker|Polyline|Polygon|null}
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
   * @param feature {Marker|VertexMarker|Polyline|Polygon|null}
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
