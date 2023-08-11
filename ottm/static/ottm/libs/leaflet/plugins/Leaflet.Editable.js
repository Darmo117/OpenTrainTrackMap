import * as L from "../leaflet-src.esm.js";

/**
 * miniclass CancelableEvent (Event objects)
 * method cancel()
 * Cancel any subsequent action.
 *
 * miniclass VertexEvent (Event objects)
 * property vertex: VertexMarker
 * The vertex that fires the event.
 *
 * miniclass ShapeEvent (Event objects)
 * property shape: Array
 * The shape (LatLngs array) subject of the action.
 *
 * miniclass CancelableVertexEvent (Event objects)
 * inherits VertexEvent
 * inherits CancelableEvent
 *
 * miniclass CancelableShapeEvent (Event objects)
 * inherits ShapeEvent
 * inherits CancelableEvent
 *
 * miniclass LayerEvent (Event objects)
 * property layer: object
 * The Layer (Marker, Polyline…) subject of the action.
 *
 * namespace Editable; class Editable; aka Editable
 * Main edition handler. By default, it is attached to the map
 * as `map.editTools` property.
 * Leaflet.Editable is made to be fully extendable. You have three ways to customize
 * the behaviour: using options, listening to events, or extending.
 *
 * @class
 */
export const Editable = L.Evented.extend({
  statics: {
    FORWARD: 1,
    BACKWARD: -1
  },

  /**
   * You can pass them when creating a map using the `editOptions` key.
   */
  options: {
    /**
     * The default zIndex of the editing tools.
     * @type {number}
     */
    zIndex: 1000,

    /**
     * Class to be used when creating a new Polygon.
     */
    polygonClass: L.Polygon,

    /**
     * Class to be used when creating a new Polyline.
     */
    polylineClass: L.Polyline,

    /**
     * Class to be used when creating a new Marker.
     */
    markerClass: L.Marker,

    /**
     * Class to be used when creating a new Rectangle.
     */
    rectangleClass: L.Rectangle,

    /**
     * Class to be used when creating a new Circle.
     */
    circleClass: L.Circle,

    /**
     * CSS class to be added to the map container while drawing.
     * @type {string}
     */
    drawingCSSClass: "leaflet-editable-drawing",

    /**
     * Cursor mode set to the map while drawing.
     * @type {string}
     */
    drawingCursor: "crosshair",

    /**
     * Layer used to store edit tools (vertex, line guide…).
     * @type {L.Layer}
     */
    editLayer: undefined,

    /**
     * Default layer used to store drawn features (Marker, Polyline…).
     * @type {L.Layer}
     */
    featuresLayer: undefined,

    /**
     * Class to be used as Polyline editor.
     */
    polylineEditorClass: undefined,

    /**
     * Class to be used as Polygon editor.
     */
    polygonEditorClass: undefined,

    /**
     * Class to be used as Marker editor.
     */
    markerEditorClass: undefined,

    /**
     * Class to be used as Rectangle editor.
     */
    rectangleEditorClass: undefined,

    /**
     * Class to be used as Circle editor.
     */
    circleEditorClass: undefined,

    /**
     * Options to be passed to the line guides.
     * @type {Object}
     */
    lineGuideOptions: {},

    /**
     * Set this to true if you don't want middle markers.
     * @type {boolean}
     */
    skipMiddleMarkers: false,
  },

  initialize: function (map, options) {
    L.setOptions(this, options);
    this._lastZIndex = this.options.zIndex;
    this.map = map;
    this.editLayer = this.createEditLayer();
    this.featuresLayer = this.createFeaturesLayer();
    this.forwardLineGuide = this.createLineGuide();
    this.backwardLineGuide = this.createLineGuide();
  },

  fireAndForward: function (type, e) {
    e = e || {};
    e.editTools = this;
    this.fire(type, e);
    this.map.fire(type, e);
  },

  createLineGuide: function () {
    const options = L.extend({dashArray: "5,10", weight: 1, interactive: false}, this.options.lineGuideOptions);
    return L.polyline([], options);
  },

  createVertexIcon: function (options) {
    return L.Browser.mobile && L.Browser.touch
      ? new Editable.TouchVertexIcon(options)
      : new Editable.VertexIcon(options);
  },

  createEditLayer: function () {
    return this.options.editLayer ?? new L.LayerGroup().addTo(this.map);
  },

  createFeaturesLayer: function () {
    return this.options.featuresLayer ?? new L.LayerGroup().addTo(this.map);
  },

  moveForwardLineGuide: function (latlng) {
    if (this.forwardLineGuide._latlngs.length) {
      this.forwardLineGuide._latlngs[1] = latlng;
      this.forwardLineGuide._bounds.extend(latlng);
      this.forwardLineGuide.redraw();
    }
  },

  moveBackwardLineGuide: function (latlng) {
    if (this.backwardLineGuide._latlngs.length) {
      this.backwardLineGuide._latlngs[1] = latlng;
      this.backwardLineGuide._bounds.extend(latlng);
      this.backwardLineGuide.redraw();
    }
  },

  anchorForwardLineGuide: function (latlng) {
    this.forwardLineGuide._latlngs[0] = latlng;
    this.forwardLineGuide._bounds.extend(latlng);
    this.forwardLineGuide.redraw();
  },

  anchorBackwardLineGuide: function (latlng) {
    this.backwardLineGuide._latlngs[0] = latlng;
    this.backwardLineGuide._bounds.extend(latlng);
    this.backwardLineGuide.redraw();
  },

  attachForwardLineGuide: function () {
    this.editLayer.addLayer(this.forwardLineGuide);
  },

  attachBackwardLineGuide: function () {
    this.editLayer.addLayer(this.backwardLineGuide);
  },

  detachForwardLineGuide: function () {
    this.forwardLineGuide.setLatLngs([]);
    this.editLayer.removeLayer(this.forwardLineGuide);
  },

  detachBackwardLineGuide: function () {
    this.backwardLineGuide.setLatLngs([]);
    this.editLayer.removeLayer(this.backwardLineGuide);
  },

  blockEvents: function () {
    // Hack: force map not to listen to other layers events while drawing.
    if (!this._oldTargets) {
      this._oldTargets = this.map._targets;
      this.map._targets = {};
    }
  },

  unblockEvents: function () {
    if (this._oldTargets) {
      // Reset, but keep targets created while drawing.
      this.map._targets = L.extend(this.map._targets, this._oldTargets);
      delete this._oldTargets;
    }
  },

  registerForDrawing: function (editor) {
    if (this._drawingEditor) {
      this.unregisterForDrawing(this._drawingEditor);
    }
    this.blockEvents();
    editor.reset();  // Make sure editor tools still receive events.
    this._drawingEditor = editor;
    this.map.on("mousemove touchmove", editor.onDrawingMouseMove, editor);
    this.map.on("mousedown", this.onMousedown, this);
    this.map.on("mouseup", this.onMouseup, this);
    L.DomUtil.addClass(this.map._container, this.options.drawingCSSClass);
    this.defaultMapCursor = this.map._container.style.cursor;
    this.map._container.style.cursor = this.options.drawingCursor;
  },

  unregisterForDrawing: function (editor) {
    this.unblockEvents();
    L.DomUtil.removeClass(this.map._container, this.options.drawingCSSClass);
    this.map._container.style.cursor = this.defaultMapCursor;
    editor = editor ?? this._drawingEditor;
    if (!editor) {
      return;
    }
    this.map.off("mousemove touchmove", editor.onDrawingMouseMove, editor);
    this.map.off("mousedown", this.onMousedown, this);
    this.map.off("mouseup", this.onMouseup, this);
    if (editor !== this._drawingEditor) {
      return;
    }
    delete this._drawingEditor;
    if (editor._drawing) {
      editor.cancelDrawing();
    }
  },

  onMousedown: function (e) {
    if (e.originalEvent.which !== 1) {
      return;
    }
    this._mouseDown = e;
    this._drawingEditor.onDrawingMouseDown(e);
  },

  onMouseup: function (e) {
    if (this._mouseDown) {
      const editor = this._drawingEditor;
      const mouseDown = this._mouseDown;
      this._mouseDown = null;
      editor.onDrawingMouseUp(e);
      if (this._drawingEditor !== editor) {
        return;
      }  // onDrawingMouseUp may call unregisterFromDrawing.
      const origin = L.point(mouseDown.originalEvent.clientX, mouseDown.originalEvent.clientY);
      const distance = L.point(e.originalEvent.clientX, e.originalEvent.clientY).distanceTo(origin);
      if (Math.abs(distance) < 9 * (window.devicePixelRatio || 1)) {
        this._drawingEditor.onDrawingClick(e);
      }
    }
  },

  /*
   * Public methods
   *
   * You will generally access them by the `map.editTools` instance:
   * `map.editTools.startPolyline();`
   */

  /**
   * @return {boolean} true if any drawing action is ongoing.
   */
  drawing: function () {
    return this._drawingEditor && this._drawingEditor.drawing();
  },

  /**
   * When you need to stop any ongoing drawing, without needing to know which editor is active.
   */
  stopDrawing: function () {
    this.unregisterForDrawing();
  },

  /**
   * When you need to commit any ongoing drawing, without needing to know which editor is active.
   */
  commitDrawing: function (e) {
    if (!this._drawingEditor) {
      return;
    }
    this._drawingEditor.commitDrawing(e);
  },

  connectCreatedToMap: function (layer) {
    return this.featuresLayer.addLayer(layer);
  },

  /**
   * Start drawing a Polyline.
   *
   * @param latlng {?L.LatLng} If given, the point to start with. In any case, continuing on user click.
   * @param options {?Object} Options to pass to the Polyline class constructor.
   * @return {L.Polyline} The polyline object.
   */
  startPolyline: function (latlng, options) {
    const line = this.createPolyline([], options);
    line.enableEdit(this.map).newShape(latlng);
    return line;
  },

  /**
   * Start drawing a Polygon.
   *
   * @param latlng {?L.LatLng} If given, the point to start with. In any case, continuing on user click.
   * @param options {?Object} Options to pass to the Polygon class constructor.
   * @return {L.Polygon} The polygon object.
   */
  startPolygon: function (latlng, options) {
    const polygon = this.createPolygon([], options);
    polygon.enableEdit(this.map).newShape(latlng);
    return polygon;
  },

  /**
   * Start adding a Marker.
   *
   * @param latlng {?L.LatLng} If given, the marker will be shown at this point.
   *  In any case, it will follow the user mouse, and will have a final `latlng` on next click (or touch).
   * @param options {?Object} Options to pass to the Marker class constructor.
   * @return {L.Marker} The marker object.
   */
  startMarker: function (latlng, options) {
    latlng = latlng ?? this.map.getCenter().clone();
    const marker = this.createMarker(latlng, options);
    marker.enableEdit(this.map).startDrawing();
    return marker;
  },

  /**
   * Start drawing a Rectangle.
   *
   * @param latlng {?L.LatLng} If given, the point to use as the anchor. In any case, continuing on user drag.
   * @param options {?Object} Options to pass to the Rectangle class constructor.
   * @return {L.Rectangle} The rectangle object.
   */
  startRectangle: function (latlng = L.latLng([0, 0]), options) {
    const rectangle = this.createRectangle(new L.LatLngBounds(latlng, latlng), options);
    rectangle.enableEdit(this.map).startDrawing();
    return rectangle;
  },

  /**
   * Start drawing a Circle.
   *
   * @param latlng {?L.LatLng} If given, the point to use as the anchor. In any case, continuing on user drag.
   * @param options {?Object} Options to pass to the Circle class constructor.
   * @return {L.Circle} The circle object.
   */
  startCircle: function (latlng, options) {
    latlng = latlng ?? this.map.getCenter().clone();
    const circle = this.createCircle(latlng, options);
    circle.enableEdit(this.map).startDrawing();
    return circle;
  },

  startHole: function (editor, latlng) {
    editor.newHole(latlng);
  },

  createLayer: function (klass, latlngs, options) {
    options = L.Util.extend({editOptions: {editTools: this}}, options);
    const layer = new klass(latlngs, options);
    this.fireAndForward("editable:created", {layer: layer});
    return layer;
  },

  createPolyline: function (latlngs, options) {
    return this.createLayer(options?.polylineClass ?? this.options.polylineClass, latlngs, options);
  },

  createPolygon: function (latlngs, options) {
    return this.createLayer(options?.polygonClass ?? this.options.polygonClass, latlngs, options);
  },

  createMarker: function (latlng, options) {
    return this.createLayer(options?.markerClass ?? this.options.markerClass, latlng, options);
  },

  createRectangle: function (bounds, options) {
    return this.createLayer(options?.rectangleClass ?? this.options.rectangleClass, bounds, options);
  },

  createCircle: function (latlng, options) {
    return this.createLayer(options?.circleClass ?? this.options.circleClass, latlng, options);
  }
});

L.extend(Editable, {
  makeCancellable: function (e) {
    e.cancel = function () {
      e._cancelled = true;
    };
  }
});

/**
 * Leaflet.Editable adds options and events to the `L.Map` object.
 * See `Editable` events for the list of events fired on the Map.
 *
 * Example:
 * ```js
 * const map = L.map("map", {
 *  editable: true,
 *  editOptions: {
 *    …
 *  }
 * });
 * ```
 */
L.Map.mergeOptions({
  /**
   * Class to be used as vertex, for path editing.
   */
  editToolsClass: Editable,

  /**
   * Whether to create a Editable instance at map init.
   * @type {boolean}
   */
  editable: false,

  /**
   * Options to pass to Editable when instantiating.
   * @type {Object}
   */
  editOptions: {}
});

L.Map.addInitHook(function () {
  this.whenReady(function () {
    if (this.options.editable) {
      this.editTools = new this.options.editToolsClass(this, this.options.editOptions);
    }
  });
});

/**
 * @class
 */
Editable.VertexIcon = L.DivIcon.extend({
  options: {
    iconSize: new L.Point(8, 8)
  }
});

/**
 * @class
 */
Editable.TouchVertexIcon = Editable.VertexIcon.extend({
  options: {
    iconSize: new L.Point(20, 20)
  }
});

/**
 * Handler for dragging path vertices.
 *
 * The marker used to handle path vertex. You will usually interact with a `VertexMarker`
 * instance when listening for events like `editable:vertex:ctrlclick`.
 *
 * @class
 */
Editable.VertexMarker = L.Marker.extend({
  options: {
    draggable: true,
    className: "leaflet-div-icon leaflet-vertex-icon"
  },

  /*
   * Public methods
   */

  initialize: function (latlng, latlngs, editor, options) {
    // We don't use this._latlng, because on drag Leaflet replace it while
    // we want to keep reference.
    this.latlng = latlng;
    this.latlngs = latlngs;
    this.editor = editor;
    L.Marker.prototype.initialize.call(this, latlng, options);
    this.options.icon = this.editor.tools.createVertexIcon({className: this.options.className});
    this.latlng.__vertex = this;
    this.editor.editLayer.addLayer(this);
    this.setZIndexOffset(editor.tools._lastZIndex + 1);
  },

  onAdd: function (map) {
    L.Marker.prototype.onAdd.call(this, map);
    this.on("drag", this.onDrag);
    this.on("dragstart", this.onDragStart);
    this.on("dragend", this.onDragEnd);
    this.on("mouseup", this.onMouseup);
    this.on("click", this.onClick);
    this.on("contextmenu", this.onContextMenu);
    this.on("mousedown touchstart", this.onMouseDown);
    this.on("mouseover", this.onMouseOver);
    this.on("mouseout", this.onMouseOut);
    this.addMiddleMarkers();
  },

  onRemove: function (map) {
    if (this.middleMarker) {
      this.middleMarker.delete();
    }
    delete this.latlng.__vertex;
    this.off("drag", this.onDrag);
    this.off("dragstart", this.onDragStart);
    this.off("dragend", this.onDragEnd);
    this.off("mouseup", this.onMouseup);
    this.off("click", this.onClick);
    this.off("contextmenu", this.onContextMenu);
    this.off("mousedown touchstart", this.onMouseDown);
    this.off("mouseover", this.onMouseOver);
    this.off("mouseout", this.onMouseOut);
    L.Marker.prototype.onRemove.call(this, map);
  },

  onDrag: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerDrag(e);
    const iconPos = L.DomUtil.getPosition(this._icon);
    const latlng = this._map.layerPointToLatLng(iconPos);
    this.latlng.update(latlng);
    this._latlng = this.latlng;  // Push back to Leaflet our reference.
    this.editor.refresh();
    this.middleMarker?.updateLatLng();
    this.getNext()?.middleMarker?.updateLatLng();
  },

  onDragStart: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerDragStart(e);
  },

  onDragEnd: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerDragEnd(e);
  },

  onClick: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerClick(e);
  },

  onMouseup: function (e) {
    L.DomEvent.stop(e);
    e.vertex = this;
    this.editor.map.fire("mouseup", e);
  },

  onContextMenu: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerContextMenu(e);
  },

  onMouseDown: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerMouseDown(e);
  },

  onMouseOver: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerMouseOver(e);
  },

  onMouseOut: function (e) {
    e.vertex = this;
    this.editor.onVertexMarkerMouseOut(e);
  },

  /**
   * Delete a vertex and the related LatLng.
   */
  delete: function () {
    const next = this.getNext();  // Compute before changing latlng
    this.latlngs.splice(this.getIndex(), 1);
    this.editor.editLayer.removeLayer(this);
    this.editor.onVertexDeleted({latlng: this.latlng, vertex: this});
    if (!this.latlngs.length) {
      this.editor.deleteShape(this.latlngs);
    }
    next?.resetMiddleMarker();
    this.editor.refresh();
  },

  /**
   * Get the index of the current vertex among others of the same LatLngs group.
   * @return {number} The index of the first occurrence of the current vertex, or -1 if not found.
   */
  getIndex: function () {
    return this.latlngs.indexOf(this.latlng);
  },

  /**
   * Get last vertex index of the LatLngs group of the current vertex.
   * @return {number} `this.latlngs.length - 1`
   */
  getLastIndex: function () {
    return this.latlngs.length - 1;
  },

  /**
   * Get the previous VertexMarker in the same LatLngs group.
   * @return {?Editable.VertexMarker}
   */
  getPrevious: function () {
    if (this.latlngs.length < 2) {
      return null;
    }
    const index = this.getIndex();
    let previousIndex = index - 1;
    if (index === 0 && this.editor.CLOSED) {
      previousIndex = this.getLastIndex();
    }
    return this.latlngs[previousIndex]?.__vertex ?? null;
  },

  /**
   * Get the next VertexMarker in the same LatLngs group.
   * @return {?Editable.VertexMarker}
   */
  getNext: function () {
    if (this.latlngs.length < 2) {
      return null;
    }
    const index = this.getIndex();
    let nextIndex = index + 1;
    if (index === this.getLastIndex() && this.editor.CLOSED) {
      nextIndex = 0;
    }
    return this.latlngs[nextIndex]?.__vertex ?? null;
  },

  addMiddleMarker: function (previous) {
    if (!this.editor.hasMiddleMarkers()) {
      return;
    }
    previous = previous ?? this.getPrevious();
    if (previous && !this.middleMarker) {
      this.middleMarker = this.editor.addMiddleMarker(previous, this, this.latlngs, this.editor);
    }
  },

  addMiddleMarkers: function () {
    if (!this.editor.hasMiddleMarkers()) {
      return;
    }
    const previous = this.getPrevious();
    if (previous) {
      this.addMiddleMarker(previous);
    }
    this.getNext()?.resetMiddleMarker();
  },

  resetMiddleMarker: function () {
    this.middleMarker?.delete();
    this.addMiddleMarker();
  },

  /**
   * Split the vertex LatLngs group at its index, if possible.
   */
  split: function () {
    if (!this.editor.splitShape) {
      return;
    }  // Only for PolylineEditor
    this.editor.splitShape(this.latlngs, this.getIndex());
  },

  /**
   * Continue the vertex LatLngs from this vertex. Only active for first and last vertices of a Polyline.
   */
  continue: function () {
    if (!this.editor.continueBackward) {
      return;
    }  // Only for PolylineEditor
    const index = this.getIndex();
    if (index === 0) {
      this.editor.continueBackward(this.latlngs);
    } else if (index === this.getLastIndex()) {
      this.editor.continueForward(this.latlngs);
    }
  }
});

Editable.mergeOptions({
  /**
   * Class to be used as vertex, for path editing.
   */
  vertexMarkerClass: Editable.VertexMarker,
});

/**
 * @class
 */
Editable.MiddleMarker = L.Marker.extend({
  options: {
    opacity: 0.5,
    className: "leaflet-div-icon leaflet-middle-icon",
    draggable: true
  },

  initialize: function (left, right, latlngs, editor, options) {
    this.left = left;
    this.right = right;
    this.editor = editor;
    this.latlngs = latlngs;
    L.Marker.prototype.initialize.call(this, this.computeLatLng(), options);
    this._opacity = this.options.opacity;
    this.options.icon = this.editor.tools.createVertexIcon({className: this.options.className});
    this.editor.editLayer.addLayer(this);
    this.setVisibility();
  },

  setVisibility: function () {
    const leftPoint = this._map.latLngToContainerPoint(this.left.latlng);
    const rightPoint = this._map.latLngToContainerPoint(this.right.latlng);
    const size = L.point(this.options.icon.options.iconSize);
    if (leftPoint.distanceTo(rightPoint) < size.x * 3) {
      this.hide();
    } else {
      this.show();
    }
  },

  show: function () {
    this.setOpacity(this._opacity);
  },

  hide: function () {
    this.setOpacity(0);
  },

  updateLatLng: function () {
    this.setLatLng(this.computeLatLng());
    this.setVisibility();
  },

  computeLatLng: function () {
    const leftPoint = this.editor.map.latLngToContainerPoint(this.left.latlng);
    const rightPoint = this.editor.map.latLngToContainerPoint(this.right.latlng);
    const y = (leftPoint.y + rightPoint.y) / 2;
    const x = (leftPoint.x + rightPoint.x) / 2;
    return this.editor.map.containerPointToLatLng([x, y]);
  },

  onAdd: function (map) {
    L.Marker.prototype.onAdd.call(this, map);
    L.DomEvent.on(this._icon, "mousedown touchstart", this.onMouseDown, this);
    map.on("zoomend", this.setVisibility, this);
  },

  onRemove: function (map) {
    delete this.right.middleMarker;
    L.DomEvent.off(this._icon, "mousedown touchstart", this.onMouseDown, this);
    map.off("zoomend", this.setVisibility, this);
    L.Marker.prototype.onRemove.call(this, map);
  },

  onMouseDown: function (e) {
    const iconPos = L.DomUtil.getPosition(this._icon);
    const latlng = this.editor.map.layerPointToLatLng(iconPos);
    e = {
      originalEvent: e,
      latlng: latlng
    };
    if (this.options.opacity === 0) {
      return;
    }
    Editable.makeCancellable(e);
    this.editor.onMiddleMarkerMouseDown(e);
    if (e._cancelled) {
      return;
    }
    this.latlngs.splice(this.index(), 0, e.latlng);
    this.editor.refresh();
    const icon = this._icon;
    const marker = this.editor.addVertexMarker(e.latlng, this.latlngs);
    this.editor.onNewVertex(marker);
    /* Hack to workaround browser not firing touchend when element is no more on DOM */
    const parent = marker._icon.parentNode;
    parent.removeChild(marker._icon);
    marker._icon = icon;
    parent.appendChild(marker._icon);
    marker._initIcon();
    marker._initInteraction();
    marker.setOpacity(1);
    /* End hack */
    // Transfer ongoing dragging to real marker
    L.Draggable._dragging = false;
    marker.dragging._draggable._onDown(e.originalEvent);
    this.delete();
  },

  delete: function () {
    this.editor.editLayer.removeLayer(this);
  },

  index: function () {
    return this.latlngs.indexOf(this.right.latlng);
  }
});

Editable.mergeOptions({
  /**
   * Class to be used as middle vertex, pulled by the user to create a new point in the middle of a path.
   */
  middleMarkerClass: Editable.MiddleMarker,
});

/**
 * When editing a feature (Marker, Polyline…), an editor is attached to it.
 * This editor basically knows how to handle the edition.
 * @class
 */
Editable.BaseEditor = L.Handler.extend({
  initialize: function (map, feature, options) {
    L.setOptions(this, options);
    this.map = map;
    this.feature = feature;
    this.feature.editor = this;
    this.editLayer = new L.LayerGroup();
    this.tools = this.options.editTools ?? map.editTools;
  },

  /**
   * Set up the drawing tools for the feature to be editable.
   * @return {Editable.BaseEditor} This editor.
   */
  addHooks: function () {
    if (this.isConnected()) {
      this.onFeatureAdd();
    } else {
      this.feature.once("add", this.onFeatureAdd, this);
    }
    this.onEnable();
    this.feature.on(this._getEvents(), this);
  },

  /**
   * Remove the drawing tools for the feature.
   * @return {Editable.BaseEditor} This editor.
   */
  removeHooks: function () {
    this.feature.off(this._getEvents(), this);
    if (this.feature.dragging) {
      this.feature.dragging.disable();
    }
    this.editLayer.clearLayers();
    this.tools.editLayer.removeLayer(this.editLayer);
    this.onDisable();
    if (this._drawing) {
      this.cancelDrawing();
    }
  },

  /**
   * Return whether any drawing action is ongoing with this editor.
   * @return {boolean} true if any drawing action is ongoing with this editor.
   */
  drawing: function () {
    return !!this._drawing;
  },

  reset: function () {
  },

  onFeatureAdd: function () {
    this.tools.editLayer.addLayer(this.editLayer);
    this.feature.dragging?.enable();
  },

  hasMiddleMarkers: function () {
    return !this.options.skipMiddleMarkers && !this.tools.options.skipMiddleMarkers;
  },

  fireAndForward: function (type, e = {}) {
    e.layer = this.feature;
    this.feature.fire(type, e);
    this.tools.fireAndForward(type, e);
  },

  onEnable: function () {
    // Fired when an existing feature is ready to be edited.
    this.fireAndForward("editable:enable");
  },

  onDisable: function () {
    // Fired when an existing feature is not ready anymore to be edited.
    this.fireAndForward("editable:disable");
  },

  onEditing: function () {
    // Fired as soon as any change is made to the feature geometry.
    this.fireAndForward("editable:editing");
  },

  onStartDrawing: function () {
    // Fired when a feature is to be drawn.
    this.fireAndForward("editable:drawing:start");
  },

  onEndDrawing: function () {
    // Fired when a feature is not drawn anymore.
    this.fireAndForward("editable:drawing:end");
  },

  onCancelDrawing: function () {
    // Fired when user cancel drawing while a feature is being drawn.
    this.fireAndForward("editable:drawing:cancel");
  },

  onCommitDrawing: function (e) {
    // Fired when user finish drawing a feature.
    this.fireAndForward("editable:drawing:commit", e);
  },

  onDrawingMouseDown: function (e) {
    // Fired when user `mousedown` while drawing.
    this.fireAndForward("editable:drawing:mousedown", e);
  },

  onDrawingMouseUp: function (e) {
    // Fired when user `mouseup` while drawing.
    this.fireAndForward("editable:drawing:mouseup", e);
  },

  startDrawing: function () {
    if (!this._drawing) {
      this._drawing = Editable.FORWARD;
    }
    this.tools.registerForDrawing(this);
    this.onStartDrawing();
  },

  commitDrawing: function (e) {
    this.onCommitDrawing(e);
    this.endDrawing();
  },

  cancelDrawing: function () {
    // If called during a vertex drag, the vertex will be removed before
    // the mouseup fires on it. This is a workaround. Maybe better fix is
    // To have L.Draggable reset it's status on disable (Leaflet side).
    L.Draggable._dragging = false;
    this.onCancelDrawing();
    this.endDrawing();
  },

  endDrawing: function () {
    this._drawing = false;
    this.tools.unregisterForDrawing(this);
    this.onEndDrawing();
  },

  onDrawingClick: function (e) {
    if (!this.drawing()) {
      return;
    }
    Editable.makeCancellable(e);
    // Fired when user `click` while drawing, before any internal action is being processed.
    this.fireAndForward("editable:drawing:click", e);
    if (e._cancelled) {
      return;
    }
    if (!this.isConnected()) {
      this.connect(e);
    }
    this.processDrawingClick(e);
  },

  isConnected: function () {
    return this.map.hasLayer(this.feature);
  },

  connect: function () {
    this.tools.connectCreatedToMap(this.feature);
    this.tools.editLayer.addLayer(this.editLayer);
  },

  onMove: function (e) {
    // Fired when `move` mouse while drawing, while dragging a marker, and while dragging a vertex.
    this.fireAndForward("editable:drawing:move", e);
  },

  onDrawingMouseMove: function (e) {
    this.onMove(e);
  },

  _getEvents: function () {
    return {
      dragstart: this.onDragStart,
      drag: this.onDrag,
      dragend: this.onDragEnd,
      remove: this.disable
    };
  },

  onDragStart: function (e) {
    this.onEditing();
    // Fired before a path feature is dragged.
    this.fireAndForward("editable:dragstart", e);
  },

  onDrag: function (e) {
    this.onMove(e);
    // Fired when a path feature is being dragged.
    this.fireAndForward("editable:drag", e);
  },

  onDragEnd: function (e) {
    // Fired after a path feature has been dragged.
    this.fireAndForward("editable:dragend", e);
  }
});

/**
 * Editor for Marker.
 *
 * @class
 */
Editable.MarkerEditor = Editable.BaseEditor.extend({
  onDrawingMouseMove: function (e) {
    Editable.BaseEditor.prototype.onDrawingMouseMove.call(this, e);
    if (this._drawing) {
      this.feature.setLatLng(e.latlng);
    }
  },

  processDrawingClick: function (e) {
    // Fired when user `click` while drawing, after all internal actions.
    this.fireAndForward("editable:drawing:clicked", e);
    this.commitDrawing(e);
  },

  connect: function (e) {
    // On touch, the latlng has not been updated because there is no mousemove.
    if (e) {
      this.feature._latlng = e.latlng;
    }
    Editable.BaseEditor.prototype.connect.call(this, e);
  }
});

const isFlat = L.LineUtil.isFlat || L.LineUtil._flat || L.Polyline._flat; // <=> 1.1 compat.

/**
 * Base class for all path editors.
 *
 * @class
 */
Editable.PathEditor = Editable.BaseEditor.extend({
  CLOSED: false,
  MIN_VERTEX: 2,

  addHooks: function () {
    Editable.BaseEditor.prototype.addHooks.call(this);
    if (this.feature) {
      this.initVertexMarkers();
    }
    return this;
  },

  initVertexMarkers: function (latlngs) {
    if (!this.enabled()) {
      return;
    }
    latlngs = latlngs ?? this.getLatLngs();
    if (isFlat(latlngs)) {
      this.addVertexMarkers(latlngs);
    } else {
      for (let i = 0; i < latlngs.length; i++) {
        this.initVertexMarkers(latlngs[i]);
      }
    }
  },

  getLatLngs: function () {
    return this.feature.getLatLngs();
  },

  /**
   * Rebuild edit elements (Vertex, MiddleMarker, etc.).
   */
  reset: function () {
    this.editLayer.clearLayers();
    this.initVertexMarkers();
  },

  addVertexMarker: function (latlng, latlngs) {
    return new this.tools.options.vertexMarkerClass(latlng, latlngs, this);
  },

  onNewVertex: function (vertex) {
    // Fired when a new vertex is created.
    this.fireAndForward("editable:vertex:new", {latlng: vertex.latlng, vertex: vertex});
  },

  addVertexMarkers: function (latlngs) {
    for (let i = 0; i < latlngs.length; i++) {
      this.addVertexMarker(latlngs[i], latlngs);
    }
  },

  refreshVertexMarkers: function (latlngs) {
    latlngs = latlngs ?? this.getDefaultLatLngs();
    for (let i = 0; i < latlngs.length; i++) {
      latlngs[i].__vertex.update();
    }
  },

  addMiddleMarker: function (left, right, latlngs) {
    return new this.tools.options.middleMarkerClass(left, right, latlngs, this);
  },

  onVertexMarkerClick: function (e) {
    Editable.makeCancellable(e);
    // Fired when a `click` is issued on a vertex, before any internal action is being processed.
    this.fireAndForward("editable:vertex:click", e);
    if (e._cancelled) {
      return;
    }
    if (this.tools.drawing() && this.tools._drawingEditor !== this) {
      return;
    }
    const index = e.vertex.getIndex();
    let commit;
    if (e.originalEvent.ctrlKey) {
      this.onVertexMarkerCtrlClick(e);
    } else if (e.originalEvent.altKey) {
      this.onVertexMarkerAltClick(e);
    } else if (e.originalEvent.shiftKey) {
      this.onVertexMarkerShiftClick(e);
    } else if (e.originalEvent.metaKey) {
      this.onVertexMarkerMetaKeyClick(e);
    } else if (index === e.vertex.getLastIndex() && this._drawing === Editable.FORWARD) {
      if (index >= this.MIN_VERTEX - 1) {
        commit = true;
      }
    } else if (index === 0 && this._drawing === Editable.BACKWARD && this._drawnLatLngs.length >= this.MIN_VERTEX) {
      commit = true;
    } else if (index === 0 && this._drawing === Editable.FORWARD && this._drawnLatLngs.length >= this.MIN_VERTEX && this.CLOSED) {
      commit = true; // Allow to close on first point also for polygons
    } else {
      this.onVertexRawMarkerClick(e);
    }
    // Fired when a `click` is issued on a vertex, after all internal actions.
    this.fireAndForward("editable:vertex:clicked", e);
    if (commit) {
      this.commitDrawing(e);
    }
  },

  onVertexRawMarkerClick: function (e) {
    // Fired when a `click` is issued on a vertex without any special key and without being in drawing mode.
    this.fireAndForward("editable:vertex:rawclick", e);
    if (e._cancelled) {
      return;
    }
    if (!this.vertexCanBeDeleted(e.vertex)) {
      return;
    }
    e.vertex.delete();
  },

  vertexCanBeDeleted: function (vertex) {
    return vertex.latlngs.length > this.MIN_VERTEX;
  },

  onVertexDeleted: function (e) {
    // Fired after a vertex has been deleted by user.
    this.fireAndForward("editable:vertex:deleted", e);
  },

  onVertexMarkerCtrlClick: function (e) {
    // Fired when a `click` with `ctrlKey` is issued on a vertex.
    this.fireAndForward("editable:vertex:ctrlclick", e);
  },

  onVertexMarkerShiftClick: function (e) {
    // Fired when a `click` with `shiftKey` is issued on a vertex.
    this.fireAndForward("editable:vertex:shiftclick", e);
  },

  onVertexMarkerMetaKeyClick: function (e) {
    // Fired when a `click` with `metaKey` is issued on a vertex.
    this.fireAndForward("editable:vertex:metakeyclick", e);
  },

  onVertexMarkerAltClick: function (e) {
    // Fired when a `click` with `altKey` is issued on a vertex.
    this.fireAndForward("editable:vertex:altclick", e);
  },

  onVertexMarkerContextMenu: function (e) {
    // Fired when a `contextmenu` is issued on a vertex.
    this.fireAndForward("editable:vertex:contextmenu", e);
  },

  onVertexMarkerMouseDown: function (e) {
    // Fired when user `mousedown` a vertex.
    this.fireAndForward("editable:vertex:mousedown", e);
  },

  onVertexMarkerMouseOver: function (e) {
    // Fired when a user's mouse enters the vertex
    this.fireAndForward("editable:vertex:mouseover", e);
  },

  onVertexMarkerMouseOut: function (e) {
    // Fired when a user's mouse leaves the vertex
    this.fireAndForward("editable:vertex:mouseout", e);
  },

  onMiddleMarkerMouseDown: function (e) {
    // Fired when user `mousedown` a middle marker.
    this.fireAndForward("editable:middlemarker:mousedown", e);
  },

  onVertexMarkerDrag: function (e) {
    this.onMove(e);
    if (this.feature._bounds) {
      this.extendBounds(e);
    }
    // Fired when a vertex is dragged by user.
    this.fireAndForward("editable:vertex:drag", e);
  },

  onVertexMarkerDragStart: function (e) {
    // Fired before a vertex is dragged by user.
    this.fireAndForward("editable:vertex:dragstart", e);
  },

  onVertexMarkerDragEnd: function (e) {
    // Fired after a vertex is dragged by user.
    this.fireAndForward("editable:vertex:dragend", e);
  },

  setDrawnLatLngs: function (latlngs) {
    this._drawnLatLngs = latlngs ?? this.getDefaultLatLngs();
  },

  startDrawing: function () {
    if (!this._drawnLatLngs) {
      this.setDrawnLatLngs();
    }
    Editable.BaseEditor.prototype.startDrawing.call(this);
  },

  startDrawingForward: function () {
    this.startDrawing();
  },

  endDrawing: function () {
    this.tools.detachForwardLineGuide();
    this.tools.detachBackwardLineGuide();
    if (this._drawnLatLngs && this._drawnLatLngs.length < this.MIN_VERTEX) {
      this.deleteShape(this._drawnLatLngs);
    }
    Editable.BaseEditor.prototype.endDrawing.call(this);
    delete this._drawnLatLngs;
  },

  addLatLng: function (latlng) {
    if (this._drawing === Editable.FORWARD) {
      this._drawnLatLngs.push(latlng);
    } else {
      this._drawnLatLngs.unshift(latlng);
    }
    this.feature._bounds.extend(latlng);
    this.onNewVertex(this.addVertexMarker(latlng, this._drawnLatLngs));
    this.refresh();
  },

  newPointForward: function (latlng) {
    this.addLatLng(latlng);
    this.tools.attachForwardLineGuide();
    this.tools.anchorForwardLineGuide(latlng);
  },

  newPointBackward: function (latlng) {
    this.addLatLng(latlng);
    this.tools.anchorBackwardLineGuide(latlng);
  },

  /**
   * Programmatically add a point while drawing.
   * @param latlng {L.LatLng} The point to add.
   */
  push: function (latlng) {
    if (!latlng) {
      return console.error("Editable.PathEditor.push expects a valid latlng as parameter");
    }
    if (this._drawing === Editable.FORWARD) {
      this.newPointForward(latlng);
    } else {
      this.newPointBackward(latlng);
    }
  },

  removeLatLng: function (latlng) {
    latlng.__vertex.delete();
    this.refresh();
  },

  /**
   * Programmatically remove last point (if any) while drawing.
   * @return {?L.LatLng} The popped point or null if none were.
   */
  pop: function () {
    if (this._drawnLatLngs.length <= 1) {
      return null;
    }
    let latlng;
    if (this._drawing === Editable.FORWARD) {
      latlng = this._drawnLatLngs[this._drawnLatLngs.length - 1];
    } else {
      latlng = this._drawnLatLngs[0];
    }
    this.removeLatLng(latlng);
    if (this._drawing === Editable.FORWARD) {
      this.tools.anchorForwardLineGuide(this._drawnLatLngs[this._drawnLatLngs.length - 1]);
    } else {
      this.tools.anchorForwardLineGuide(this._drawnLatLngs[0]);
    }
    return latlng;
  },

  processDrawingClick: function (e) {
    if (e.vertex && e.vertex.editor === this) {
      return;
    }
    if (this._drawing === Editable.FORWARD) {
      this.newPointForward(e.latlng);
    } else {
      this.newPointBackward(e.latlng);
    }
    this.fireAndForward("editable:drawing:clicked", e);
  },

  onDrawingMouseMove: function (e) {
    Editable.BaseEditor.prototype.onDrawingMouseMove.call(this, e);
    if (this._drawing) {
      this.tools.moveForwardLineGuide(e.latlng);
      this.tools.moveBackwardLineGuide(e.latlng);
    }
  },

  refresh: function () {
    this.feature.redraw();
    this.onEditing();
  },

  /**
   * Add a new shape (Polyline, Polygon) in a multi, and setup up drawing tools to draw it;
   * @param latlng {L.LatLng} If given, point to use as start.
   */
  newShape: function (latlng) {
    const shape = this.addNewEmptyShape();
    if (!shape) {
      return;
    }
    this.setDrawnLatLngs(shape[0] ?? shape); // Polygon or polyline
    this.startDrawingForward();
    // Fired when a new shape is created in a multi (Polygon or Polyline).
    this.fireAndForward("editable:shape:new", {shape: shape});
    if (latlng) {
      this.newPointForward(latlng);
    }
  },

  /**
   * Delete a shape.
   *
   * @param shape {L.Polyline|L.Polygon}
   * @param latlngs {?(L.LatLng[])}
   * @return {L.Polyline|L.Polygon|null}
   */
  deleteShape: function (shape, latlngs = null) {
    const e = {shape: shape};
    Editable.makeCancellable(e);
    // Fired before a new shape is deleted in a multi (Polygon or Polyline).
    this.fireAndForward("editable:shape:delete", e);
    if (e._cancelled) {
      return null;
    }
    shape = this._deleteShape(shape, latlngs);
    if (this.ensureNotFlat) {
      this.ensureNotFlat();
    } // Polygon.
    this.feature.setLatLngs(this.getLatLngs()); // Force bounds reset.
    this.refresh();
    this.reset();
    // Fired after a new shape is deleted in a multi (Polygon or Polyline).
    this.fireAndForward("editable:shape:deleted", {shape: shape});
    return shape;
  },

  _deleteShape: function (shape, latlngs) {
    latlngs = latlngs ?? this.getLatLngs();
    if (!latlngs.length) {
      return;
    }
    const self = this;
    const inplaceDelete = function (latlngs, shape) {
      // Called when deleting a flat latlngs
      shape = latlngs.splice(0, Number.MAX_VALUE);
      return shape;
    };
    const spliceDelete = function (latlngs, shape) {
      // Called when removing a latlngs inside an array
      latlngs.splice(latlngs.indexOf(shape), 1);
      if (!latlngs.length) {
        self._deleteShape(latlngs);
      }
      return shape;
    };
    if (latlngs === shape) {
      return inplaceDelete(latlngs, shape);
    }
    for (let i = 0; i < latlngs.length; i++) {
      if (latlngs[i] === shape) {
        return spliceDelete(latlngs, shape);
      } else if (latlngs[i].indexOf(shape) !== -1) {
        return spliceDelete(latlngs[i], shape);
      }
    }
  },

  /**
   * Remove a path shape at the given `latlng`.
   *
   * @param latlng {L.LatLng}
   * @return {L.Polyline|L.Polygon|null}
   */
  deleteShapeAt: function (latlng) {
    const shape = this.feature.shapeAt(latlng);
    if (shape) {
      return this.deleteShape(shape);
    }
  },

  /**
   * Append a new shape to the Polygon or Polyline.
   * @param shape
   */
  appendShape: function (shape) {
    this.insertShape(shape);
  },

  /**
   * Prepend a new shape to the Polygon or Polyline.
   * @param shape
   */
  prependShape: function (shape) {
    this.insertShape(shape, 0);
  },

  // 🍂method insertShape(shape: Array, index: int)
  // Insert a new shape to the Polygon or Polyline at given index (default is to append).
  insertShape: function (shape, index) {
    this.ensureMulti();
    shape = this.formatShape(shape);
    if (typeof index === 'undefined') {
      index = this.feature._latlngs.length;
    }
    this.feature._latlngs.splice(index, 0, shape);
    this.feature.redraw();
    if (this._enabled) {
      this.reset();
    }
  },

  extendBounds: function (e) {
    this.feature._bounds.extend(e.vertex.latlng);
  },

  onDragStart: function (e) {
    this.editLayer.clearLayers();
    Editable.BaseEditor.prototype.onDragStart.call(this, e);
  },

  onDragEnd: function (e) {
    this.initVertexMarkers();
    Editable.BaseEditor.prototype.onDragEnd.call(this, e);
  }
});

/**
 * @class
 */
Editable.PolylineEditor = Editable.PathEditor.extend({
  startDrawingBackward: function () {
    this._drawing = Editable.BACKWARD;
    this.startDrawing();
  },

  /**
   * Set up drawing tools to continue the line backward.
   * @param latlngs {?(L.LatLng[])}
   */
  continueBackward: function (latlngs) {
    if (this.drawing()) {
      return;
    }
    latlngs = latlngs ?? this.getDefaultLatLngs();
    this.setDrawnLatLngs(latlngs);
    if (latlngs.length > 0) {
      this.tools.attachBackwardLineGuide();
      this.tools.anchorBackwardLineGuide(latlngs[0]);
    }
    this.startDrawingBackward();
  },

  /**
   * Set up drawing tools to continue the line forward.
   * @param latlngs {?(L.LatLng[])}
   */
  continueForward: function (latlngs) {
    if (this.drawing()) {
      return;
    }
    latlngs = latlngs ?? this.getDefaultLatLngs();
    this.setDrawnLatLngs(latlngs);
    if (latlngs.length > 0) {
      this.tools.attachForwardLineGuide();
      this.tools.anchorForwardLineGuide(latlngs[latlngs.length - 1]);
    }
    this.startDrawingForward();
  },

  getDefaultLatLngs: function (latlngs) {
    latlngs = latlngs || this.feature._latlngs;
    if (!latlngs.length || latlngs[0] instanceof L.LatLng) {
      return latlngs;
    } else {
      return this.getDefaultLatLngs(latlngs[0]);
    }
  },

  ensureMulti: function () {
    if (this.feature._latlngs.length && isFlat(this.feature._latlngs)) {
      this.feature._latlngs = [this.feature._latlngs];
    }
  },

  addNewEmptyShape: function () {
    if (this.feature._latlngs.length) {
      const shape = [];
      this.appendShape(shape);
      return shape;
    } else {
      return this.feature._latlngs;
    }
  },

  formatShape: function (shape) {
    if (isFlat(shape)) {
      return shape;
    } else if (shape[0]) {
      return this.formatShape(shape[0]);
    }
  },

  /**
   * Split the given `latlngs` shape at index `index` and integrate new shape in instance `latlngs`.
   *
   * @param shape {?(L.LatLng[])}
   * @param index {number}
   */
  splitShape: function (shape, index) {
    if (!index || index >= shape.length - 1) {
      return;
    }
    this.ensureMulti();
    const shapeIndex = this.feature._latlngs.indexOf(shape);
    if (shapeIndex === -1) {
      return;
    }
    const first = shape.slice(0, index + 1);
    const second = shape.slice(index);
    // We deal with reference, we don't want twice the same latlng around.
    // noinspection JSUnresolvedReference
    second[0] = L.latLng(second[0].lat, second[0].lng, second[0].alt);
    this.feature._latlngs.splice(shapeIndex, 1, first, second);
    this.refresh();
    this.reset();
  }

});

/**
 * @class
 */
Editable.PolygonEditor = Editable.PathEditor.extend({
  CLOSED: true,
  MIN_VERTEX: 3,

  newPointForward: function (latlng) {
    Editable.PathEditor.prototype.newPointForward.call(this, latlng);
    if (!this.tools.backwardLineGuide._latlngs.length) {
      this.tools.anchorBackwardLineGuide(latlng);
    }
    if (this._drawnLatLngs.length === 2) {
      this.tools.attachBackwardLineGuide();
    }
  },

  addNewEmptyHole: function (latlng) {
    this.ensureNotFlat();
    const latlngs = this.feature.shapeAt(latlng);
    if (!latlngs) {
      return null;
    }
    const holes = [];
    latlngs.push(holes);
    return holes;
  },

  /**
   * Set up drawing tools for creating a new hole on the Polygon.
   * If the `latlng` param is given, a first point is created.
   *
   * @param latlng {?(L.LatLng[])}
   */
  newHole: function (latlng) {
    const holes = this.addNewEmptyHole(latlng);
    if (!holes) {
      return;
    }
    this.setDrawnLatLngs(holes);
    this.startDrawingForward();
    if (latlng) {
      this.newPointForward(latlng);
    }
  },

  addNewEmptyShape: function () {
    if (this.feature._latlngs.length && this.feature._latlngs[0].length) {
      const shape = [];
      this.appendShape(shape);
      return shape;
    } else {
      return this.feature._latlngs;
    }
  },

  ensureMulti: function () {
    if (this.feature._latlngs.length && isFlat(this.feature._latlngs[0])) {
      this.feature._latlngs = [this.feature._latlngs];
    }
  },

  ensureNotFlat: function () {
    if (!this.feature._latlngs.length || isFlat(this.feature._latlngs)) {
      this.feature._latlngs = [this.feature._latlngs];
    }
  },

  vertexCanBeDeleted: function (vertex) {
    const parent = this.feature.parentShape(vertex.latlngs);
    const idx = L.Util.indexOf(parent, vertex.latlngs);
    // Holes can be totally deleted without removing the layer itself.
    return idx > 0 || Editable.PathEditor.prototype.vertexCanBeDeleted.call(this, vertex);
  },

  getDefaultLatLngs: function () {
    if (!this.feature._latlngs.length) {
      this.feature._latlngs.push([]);
    }
    return this.feature._latlngs[0];
  },

  formatShape: function (shape) {
    // [[1, 2], [3, 4]] => must be nested
    // [] => must be nested
    // [[]] => is already nested
    if (isFlat(shape) && (!shape[0] || shape[0].length !== 0)) {
      return [shape];
    } else {
      return shape;
    }
  }

});

/**
 * @class
 */
Editable.RectangleEditor = Editable.PathEditor.extend({
  CLOSED: true,
  MIN_VERTEX: 4,

  options: {
    skipMiddleMarkers: true
  },

  extendBounds: function (e) {
    const index = e.vertex.getIndex();
    const next = e.vertex.getNext();
    const previous = e.vertex.getPrevious();
    const oppositeIndex = (index + 2) % 4;
    const opposite = e.vertex.latlngs[oppositeIndex];
    const bounds = new L.LatLngBounds(e.latlng, opposite);
    // Update latlngs by hand to preserve order.
    previous.latlng.update([e.latlng.lat, opposite.lng]);
    next.latlng.update([opposite.lat, e.latlng.lng]);
    this.updateBounds(bounds);
    this.refreshVertexMarkers();
  },

  onDrawingMouseDown: function (e) {
    Editable.PathEditor.prototype.onDrawingMouseDown.call(this, e);
    this.connect();
    const latlngs = this.getDefaultLatLngs();
    // L.Polygon._convertLatLngs removes last latlng if it equals first point,
    // which is the case here as all latlngs are [0, 0]
    if (latlngs.length === 3) {
      latlngs.push(e.latlng);
    }
    const bounds = new L.LatLngBounds(e.latlng, e.latlng);
    this.updateBounds(bounds);
    this.updateLatLngs(bounds);
    this.refresh();
    this.reset();
    // Stop dragging map.
    // L.Draggable has two workflows:
    // - mousedown => mousemove => mouseup
    // - touchstart => touchmove => touchend
    // Problem: L.Map.Tap does not allow us to listen to touchstart, so we only
    // can deal with mousedown, but then when in a touch device, we are dealing with
    // simulated events (actually simulated by L.Map.Tap), which are no more taken
    // into account by L.Draggable.
    // Ref.: https://github.com/Leaflet/Leaflet.Editable/issues/103
    e.originalEvent._simulated = false;
    this.map.dragging._draggable._onUp(e.originalEvent);
    // Now transfer ongoing drag action to the bottom right corner.
    // Should we refine which corner will handle the drag according to
    // drag direction?
    latlngs[3].__vertex.dragging._draggable._onDown(e.originalEvent);
  },

  onDrawingMouseUp: function (e) {
    this.commitDrawing(e);
    e.originalEvent._simulated = false;
    Editable.PathEditor.prototype.onDrawingMouseUp.call(this, e);
  },

  onDrawingMouseMove: function (e) {
    e.originalEvent._simulated = false;
    Editable.PathEditor.prototype.onDrawingMouseMove.call(this, e);
  },

  getDefaultLatLngs: function (latlngs) {
    return latlngs || this.feature._latlngs[0];
  },

  updateBounds: function (bounds) {
    this.feature._bounds = bounds;
  },

  updateLatLngs: function (bounds) {
    const latlngs = this.getDefaultLatLngs();
    const newLatlngs = this.feature._boundsToLatLngs(bounds);
    // Keep references.
    for (let i = 0; i < latlngs.length; i++) {
      latlngs[i].update(newLatlngs[i]);
    }
  }

});

/**
 * @class
 */
Editable.CircleEditor = Editable.PathEditor.extend({
  MIN_VERTEX: 2,

  options: {
    skipMiddleMarkers: true
  },

  initialize: function (map, feature, options) {
    Editable.PathEditor.prototype.initialize.call(this, map, feature, options);
    this._resizeLatLng = this.computeResizeLatLng();
  },

  computeResizeLatLng: function () {
    // While circle is not added to the map, _radius is not set.
    const delta = (this.feature._radius || this.feature._mRadius) * Math.cos(Math.PI / 4);
    const point = this.map.project(this.feature._latlng);
    return this.map.unproject([point.x + delta, point.y - delta]);
  },

  updateResizeLatLng: function () {
    this._resizeLatLng.update(this.computeResizeLatLng());
    this._resizeLatLng.__vertex.update();
  },

  getLatLngs: function () {
    return [this.feature._latlng, this._resizeLatLng];
  },

  getDefaultLatLngs: function () {
    return this.getLatLngs();
  },

  onVertexMarkerDrag: function (e) {
    if (e.vertex.getIndex() === 1) {
      this.resize(e);
    } else {
      this.updateResizeLatLng(e);
    }
    Editable.PathEditor.prototype.onVertexMarkerDrag.call(this, e);
  },

  resize: function (e) {
    this.feature.setRadius(this.feature._latlng.distanceTo(e.latlng));
  },

  onDrawingMouseDown: function (e) {
    Editable.PathEditor.prototype.onDrawingMouseDown.call(this, e);
    this._resizeLatLng.update(e.latlng);
    this.feature._latlng.update(e.latlng);
    this.connect();
    // Stop dragging map.
    e.originalEvent._simulated = false;
    this.map.dragging._draggable._onUp(e.originalEvent);
    // Now transfer ongoing drag action to the radius handler.
    this._resizeLatLng.__vertex.dragging._draggable._onDown(e.originalEvent);
  },

  onDrawingMouseUp: function (e) {
    this.commitDrawing(e);
    e.originalEvent._simulated = false;
    Editable.PathEditor.prototype.onDrawingMouseUp.call(this, e);
  },

  onDrawingMouseMove: function (e) {
    e.originalEvent._simulated = false;
    Editable.PathEditor.prototype.onDrawingMouseMove.call(this, e);
  },

  onDrag: function (e) {
    Editable.PathEditor.prototype.onDrag.call(this, e);
    this.feature.dragging.updateLatLng(this._resizeLatLng);
  }
});

/**
 * `EditableMixin` is included to `L.Polyline`, `L.Polygon`, `L.Rectangle`, `L.Circle`
 * and `L.Marker`. It adds some methods to them.
 * When editing is enabled, the editor is accessible on the instance with the `editor` property.*
 */
const EditableMixin = {
  createEditor: function (map) {
    map = map ?? this._map;
    const tools = (this.options.editOptions ?? {}).editTools ?? map.editTools;
    if (!tools) {
      throw Error('Unable to detect Editable instance.');
    }
    // noinspection JSUnresolvedReference
    const Klass = this.options.editorClass ?? this.getEditorClass(tools);
    return new Klass(map, this, this.options.editOptions);
  },

  /**
   * Enable editing, by creating an editor if not existing, and then calling `enable` on it.
   *
   * @param map {?L.Map}
   * @return {*} This editor.
   */
  enableEdit: function (map = null) {
    if (!this.editor) {
      this.createEditor(map);
    }
    this.editor.enable();
    return this.editor;
  },

  /**
   * Return whether the current instance has an editor attached, and this editor is enabled.
   * @return {boolean} true if current instance has an editor attached, and this editor is enabled.
   */
  editEnabled: function () {
    return this.editor?.enabled();
  },

  /**
   * Disable editing, also remove the editor property reference.
   */
  disableEdit: function () {
    if (this.editor) {
      this.editor.disable();
      delete this.editor;
    }
  },

  /**
   * Enable or disable editing, according to current status.
   */
  toggleEdit: function () {
    if (this.editEnabled()) {
      this.disableEdit();
    } else {
      this.enableEdit();
    }
  },

  _onEditableAdd: function () {
    if (this.editor) {
      this.enableEdit();
    }
  }
};

const PolylineMixin = {
  getEditorClass: function (tools) {
    return tools?.options.polylineEditorClass ?? Editable.PolylineEditor;
  },

  shapeAt: function (latlng, latlngs) {
    // We can have those cases:
    // - latlngs are just a flat array of latlngs, use this
    // - latlngs is an array of arrays of latlngs, loop over
    let shape = null;
    latlngs = latlngs ?? this._latlngs;
    if (!latlngs.length) {
      return shape;
    } else if (isFlat(latlngs) && this.isInLatLngs(latlng, latlngs)) {
      shape = latlngs;
    } else {
      for (let i = 0; i < latlngs.length; i++) {
        if (this.isInLatLngs(latlng, latlngs[i])) {
          return latlngs[i];
        }
      }
    }
    return shape;
  },

  isInLatLngs: function (l, latlngs) {
    if (!latlngs) {
      return false;
    }
    let part = [];
    this._projectLatlngs(latlngs, part, this._pxBounds);
    part = part[0];
    const p = this._map.latLngToLayerPoint(l);
    const w = this._clickTolerance();

    if (!this._pxBounds.contains(p)) {
      return false;
    }
    for (let i = 1, len = part.length, k = 0; i < len; k = i++) {
      if (L.LineUtil.pointToSegmentDistance(p, part[k], part[i]) <= w) {
        return true;
      }
    }
    return false;
  }
};

const PolygonMixin = {
  getEditorClass: function (tools) {
    return tools?.options.polygonEditorClass ?? Editable.PolygonEditor;
  },

  shapeAt: function (latlng, latlngs) {
    // We can have those cases:
    // - latlngs are just a flat array of latlngs, use this
    // - latlngs is an array of arrays of latlngs, this is a simple polygon (maybe with holes), use the first
    // - latlngs is an array of arrays of arrays, this is a multi, loop over
    let shape = null;
    latlngs = latlngs ?? this._latlngs;
    if (!latlngs.length) {
      return shape;
    } else if (isFlat(latlngs) && this.isInLatLngs(latlng, latlngs)) {
      shape = latlngs;
    } else if (isFlat(latlngs[0]) && this.isInLatLngs(latlng, latlngs[0])) {
      shape = latlngs;
    } else {
      for (let i = 0; i < latlngs.length; i++) {
        if (this.isInLatLngs(latlng, latlngs[i][0])) {
          return latlngs[i];
        }
      }
    }
    return shape;
  },

  isInLatLngs: function (l, latlngs) {
    let inside = false;

    for (let j = 0, len2 = latlngs.length, k = len2 - 1; j < len2; k = j++) {
      const l1 = latlngs[j];
      const l2 = latlngs[k];

      if (((l1.lat > l.lat) !== (l2.lat > l.lat)) &&
        (l.lng < (l2.lng - l1.lng) * (l.lat - l1.lat) / (l2.lat - l1.lat) + l1.lng)) {
        inside = !inside;
      }
    }

    return inside;
  },

  parentShape: function (shape, latlngs) {
    latlngs = latlngs ?? this._latlngs;
    if (!latlngs) {
      return;
    }
    let idx = L.Util.indexOf(latlngs, shape);
    if (idx !== -1) {
      return latlngs;
    }
    for (let i = 0; i < latlngs.length; i++) {
      idx = L.Util.indexOf(latlngs[i], shape);
      if (idx !== -1) {
        return latlngs[i];
      }
    }
  }
};

const MarkerMixin = {
  getEditorClass: function (tools) {
    return tools?.options.markerEditorClass ?? Editable.MarkerEditor;
  }
};

const RectangleMixin = {
  getEditorClass: function (tools) {
    return tools?.options.rectangleEditorClass ?? Editable.RectangleEditor;
  }
};

const CircleMixin = {
  getEditorClass: function (tools) {
    return tools?.options.circleEditorClass ?? Editable.CircleEditor;
  }
};

const keepEditable = function () {
  // Make sure you can remove/readd an editable layer.
  this.on("add", this._onEditableAdd);
};

if (L.Polyline) {
  L.Polyline.include(EditableMixin);
  L.Polyline.include(PolylineMixin);
  L.Polyline.addInitHook(keepEditable);
}
if (L.Polygon) {
  L.Polygon.include(EditableMixin);
  L.Polygon.include(PolygonMixin);
}
if (L.Marker) {
  L.Marker.include(EditableMixin);
  L.Marker.include(MarkerMixin);
  L.Marker.addInitHook(keepEditable);
}
if (L.Rectangle) {
  L.Rectangle.include(EditableMixin);
  L.Rectangle.include(RectangleMixin);
}
if (L.Circle) {
  L.Circle.include(EditableMixin);
  L.Circle.include(CircleMixin);
}

L.LatLng.prototype.update = function (latlng) {
  latlng = L.latLng(latlng);
  this.lat = latlng.lat;
  this.lng = latlng.lng;
}
