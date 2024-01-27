import * as mgl from "maplibre-gl";
import $ from "jquery";
import Split from "split.js";

import * as types from "../../types";
import * as st from "../../streams";
import * as geom from "../model/geometry";
import {LinearFeature} from "../model/geometry";
import * as dtypes from "../model/data-types";
import Map from "../map";
import * as utils from "../utils";
import * as events from "./_events";
import * as snap from "./_snap";
import DrawControl from "./_controls";
import EditorPanel from "./_editor-panel";
import ContextMenu, * as ctxMenu from "./_context-menu";

import "./_index.css";

/**
 * Enumeration of the map editor’s modes.
 */
enum EditMode {
  VIEW_ONLY = "view_only",
  SELECT = "select",
  DRAW_POINT = "draw_point",
  DRAW_LINE = "draw_line",
  DRAW_POLYGON = "draw_polygon",
  MOVE_FEATURES = "move_features",
}

/**
 * Enumeration of available map cursors.
 */
enum Cursor {
  POINT = "point",
  LINE = "linestring",
  POLYGON = "polygon",
  DRAW = "draw",
  GRAB = "grab",
  GRABBING = "grabbing",
  CONNECT_VERTEX = "draw-connect-vertex",
  CONNECT_LINE = "draw-connect-line",
}

class MapEditor {
  static readonly #HIGHLIGHT_BASE_COLOR: string = "#00000000";
  static readonly #HIGHLIGHT_SELECTED_COLOR: string = "#3bb2d0d0";
  static readonly #HIGHLIGHT_HOVERED_COLOR: string = "#ff6d8bd0";

  static readonly #BORDER_COLOR: string = "#101010";
  static readonly #NON_EDITABLE_COLOR: string = "#e0e0e0";

  /**
   * The minimal allowed zoom to edit features.
   */
  static readonly #EDIT_MIN_ZOOM: number = 15;

  readonly #map: mgl.Map;
  readonly #$canvasContainer: JQuery;
  readonly #sidePanel: EditorPanel;
  readonly #contextMenu: ContextMenu;
  readonly #$editZoomNoticePanel: JQuery;
  readonly #drawPointControl: DrawControl;
  /**
   * All the features currently managed by this editor.
   */
  readonly #features: types.Dict<geom.MapFeature> = {};
  /**
   * The currently selected features.
   */
  readonly #selectedFeatures: Set<geom.MapFeature> = new Set();
  /**
   * The feature currently being hovered by the mouse cursor.
   */
  #hoveredFeature: geom.MapFeature = null;
  /**
   * The current edit mode.
   */
  #editMode: EditMode = EditMode.SELECT;
  /**
   * The point currently being dragged.
   */
  #draggedPoint: geom.Point = null;
  /**
   * If a point is being dragged and snaps to another feature,
   * this field contains relevant data to that snapped feature.
   */
  #snapResult: snap.SnapResult & {
    /**
     * The list of features that have the same segment as the snapped one.
     */
    featuresWithSameSegment?: {
      /**
       * The feature.
       */
      feature: geom.LinearFeature;
      /**
       * The path to the segment on the feature.
       */
      path: string;
    }[];
  } | null = null;
  /**
   * The points currently being moved.
   */
  #movedPoints: {
    /**
     * A point being moved.
     */
    point: geom.Point;
    /**
     * The point’s distance to the mouse cursor.
     */
    offset: geom.LngLatVector;
    /**
     * The point’s position before being moved.
     */
    startPos: mgl.LngLat;
  }[] = [];
  /**
   * The line string currently being drawn.
   */
  #drawnLineString: geom.LineString = null;
  /**
   * When drawing a line, indicates where the next point will be added on that line:
   * * `true`: at the end.
   * * `false`: at the start.
   */
  #drawnStringAppendEnd: boolean = true;
  /**
   * The polygon currently being drawn.
   */
  #drawnPolygon: geom.Polygon = null;
  /**
   * The points that were created when drawing the last linear feature.
   * This list is used for deleting all points that were drawn when the current drawing is cancelled.
   */
  readonly #drawnPoints: geom.Point[] = [];
  /**
   * The last known position of the mouse on the map.
   */
  #mousePositionCache: mgl.LngLat = null;

  /**
   * Internal cache of available data types.
   */
  readonly #dataTypes: {
    units: types.Dict<dtypes.UnitType>;
    enums: types.Dict<dtypes.Enum>;
    objects: types.Dict<dtypes.ObjectType>;
  } = {
    units: {},
    enums: {},
    objects: {},
  };

  // TODO find a way to add holes to polygons

  /**
   * Create a new editor for the given map.
   * @param map A map.
   * @param dataTypes All available data types.
   */
  constructor(map: mgl.Map, dataTypes: {
    units: types.Dict<dtypes.UnitType>;
    enums: types.Dict<dtypes.Enum>;
    objects: types.Dict<dtypes.ObjectType>;
  }) {
    this.#dataTypes.units = {...dataTypes.units};
    this.#dataTypes.enums = {...dataTypes.enums};
    this.#dataTypes.objects = {...dataTypes.objects};
    this.#map = map;
    this.#$canvasContainer = $(this.#map.getCanvasContainer());
    this.#sidePanel = new EditorPanel(this.#map);
    this.#contextMenu = new ContextMenu(this.#map, {
      onMove: () => this.#moveSelectedFeatures(),
      moveTitle: window.ottm.translate("map.context_menu.move.tooltip"),
      onCopy: () => this.#copySelectedFeatures(),
      copyTitle: window.ottm.translate("map.context_menu.copy.tooltip"),
      onPaste: () => this.#pasteFeatures(),
      pasteTitle: window.ottm.translate("map.context_menu.paste.tooltip"),
      onDelete: () => this.#deleteSelectedFeatures(),
      deleteTitle: window.ottm.translate("map.context_menu.delete.tooltip"),
      onContinueLine: () => this.#continueSelectedLine(),
      continueLineTitle: window.ottm.translate("map.context_menu.continue_line.tooltip"),
      onDisconnect: () => this.#disconnectSelectedVertices(),
      disconnectTitle: window.ottm.translate("map.context_menu.disconnect.tooltip"),
      onExtractPoint: () => this.#extractSelectedVertices(),
      extractPointTitle: window.ottm.translate("map.context_menu.extract_point.tooltip"),
      onSplit: () => this.#splitSelectedLines(),
      splitTitle: window.ottm.translate("map.context_menu.split.tooltip"),
      onCircularize: () => this.#circularizeSelectedFeatures(),
      circularizeTitle: window.ottm.translate("map.context_menu.circularize.tooltip"),
      onSquare: () => this.#squareSelectedFeatures(),
      squareTitle: window.ottm.translate("map.context_menu.square.tooltip"),
      onFlipLong: () => this.#flipLongSelectedFeatures(),
      flipLongTitle: window.ottm.translate("map.context_menu.flip_long.tooltip"),
      onFlipShort: () => this.#flipShortSelectedFeatures(),
      flipShortTitle: window.ottm.translate("map.context_menu.flip_short.tooltip"),
      onReverseLine: () => this.#reverseSelectedLines(),
      reverseLineTitle: window.ottm.translate("map.context_menu.reverse_line.tooltip"),
      onRotate: () => this.#rotateSelectedFeatures(),
      rotateTitle: window.ottm.translate("map.context_menu.rotate.tooltip"),
      onStraightenLine: () => this.#straightenSelectedLines(),
      straightenLineTitle: window.ottm.translate("map.context_menu.straighten_line.tooltip"),
    });
    this.#drawPointControl = new DrawControl({
      onDrawPoint: () => {
        if (this.#editMode === EditMode.DRAW_POINT) {
          this.#disableDrawPointMode();
        } else {
          this.#enableDrawPointMode();
        }
      },
      onDrawLine: () => {
        if (this.#editMode === EditMode.DRAW_LINE) {
          this.#disableDrawLineMode();
        } else {
          this.#enableDrawLineMode();
        }
      },
      onDrawPolygon: () => {
        if (this.#editMode === EditMode.DRAW_POLYGON) {
          this.#disableDrawPolygonMode();
        } else {
          this.#enableDrawPolygonMode();
        }
      },
      drawPointButtonTitle: window.ottm.translate("map.controls.edit.draw_point.tooltip"),
      drawLineButtonTitle: window.ottm.translate("map.controls.edit.draw_line.tooltip"),
      drawPolygonButtonTitle: window.ottm.translate("map.controls.edit.draw_polygon.tooltip"),
    });
    this.#map.addControl(this.#drawPointControl, "top-left");
    this.#map.dragRotate.disable();

    // Setup map callbacks
    this.#map.on("click", e => this.#onClick(e));
    this.#map.on("dblclick", e => this.#onDoubleClick(e));
    this.#map.on("mousemove", e => this.#onMouseMouve(e));
    this.#map.on("touchmove", e => {
      if (e.points.length !== 1) {
        return;
      }
      this.#onMouseMouve(e);
    });
    this.#map.on("mousedown", e => this.#onMouseDown(e));
    this.#map.on("touchstart", e => {
      if (e.points.length !== 1) {
        return;
      }
      this.#onMouseDown(e);
    });
    this.#map.on("mouseup", e => this.#onMouseUp(e));
    this.#map.on("touchend", e => {
      if (e.points.length !== 1) {
        return;
      }
      this.#onMouseUp(e);
    });
    this.#map.on("controls.styles.tiles_changed", () => {
      if (this.#map.getLayersOrder().length) {
        // Put tiles layer beneath every other feature (i.e. the lowest one)
        this.#map.moveLayer("tiles", this.#map.getLayersOrder()[0]);
      }
    });
    this.#map.on("zoomstart", () => this.#onZoomChangeStart());
    this.#map.on("zoomend", () => this.#onZoomChangeEnd());
    this.#map.on("load", () => this.#onZoomChangeEnd());
    $("body").on("keydown", e => {
      if (!(this.#map instanceof Map) || !this.#map.textFieldHasFocus) {
        this.#onKeyDown(e.originalEvent);
      }
    });

    // Setup splitter
    const canvasContainerParent = this.#$canvasContainer.parent();
    canvasContainerParent.addClass("split");
    const sidePanelContainer = this.#sidePanel.getContainer();
    sidePanelContainer.addClass("split");
    Split([sidePanelContainer[0], canvasContainerParent[0]], {
      sizes: [20, 80],
      minSize: [0, 100],
      gutterSize: 5,
    });

    // Setup edit zoom notice panel
    const message = window.ottm.translate("map.edit_zoom_notice");
    this.#$editZoomNoticePanel = $(`
<div id="edit-zoom-notice-panel">
  <span class="mdi mdi-plus"></span> ${message}
</div>
`);
    this.#$editZoomNoticePanel.on("click",
        () => this.#map.easeTo({zoom: MapEditor.#EDIT_MIN_ZOOM}));
    canvasContainerParent.append(this.#$editZoomNoticePanel);
  }

  /**
   * Get the data type for the given name and type string.
   * @param typeName The type’s name.
   * @param metaType A string representing the class of the type to return.
   * @returns The type for the given name or undefined if it does not exist.
   */
  getDataType(typeName: string, metaType: "UnitType" | "Enum" | "ObjectType"): dtypes.UnitType | dtypes.Enum | dtypes.ObjectType {
    switch (metaType) {
      case "UnitType":
        return this.#dataTypes.units[typeName];
      case "Enum":
        return this.#dataTypes.enums[typeName];
      case "ObjectType":
        return this.#dataTypes.objects[typeName];
    }
  }

  /**
   * Add the given feature to the map.
   * @param feature The feature to add.
   */
  addFeature(feature: geom.MapFeature): void {
    // TODO handle z-order
    // TODO put linestrings over polygons with the same z-order
    if (this.#features[feature.id]) {
      return;
    }

    this.#features[feature.id] = feature;
    // Add all vertices
    if (feature instanceof geom.LineString) {
      feature.vertices.forEach(v => this.addFeature(v));
    } else if (feature instanceof geom.Polygon) {
      feature.vertices
          .flatMap(s => s)
          .forEach(v => this.addFeature(v));
    }
    this.#map.addSource(feature.id, {
      type: "geojson",
      data: feature,
    });
    this.#addLayersForFeature(feature);
    // Put all points above all current features
    if (feature instanceof geom.LineString) {
      feature.vertices.forEach(v => this.#moveLayers(v.id));
    } else if (feature instanceof geom.Polygon) {
      feature.vertices
          .flatMap(s => s)
          .forEach(v => this.#moveLayers(v.id));
    }
  }

  /**
   * Delete the feature with the given ID.
   * Bound features are updated.
   * @param featureId The ID of the feature to delete.
   */
  removeFeature(featureId: string): void {
    const feature = this.#features[featureId];
    if (!feature) {
      return;
    }
    this.#getLayerIdStack(featureId).forEach(id => this.#map.removeLayer(id));
    // Remove now to avoid potential infinite recursions
    delete this.#features[featureId];

    if (feature instanceof geom.Point) {
      this.#updateBoundFeaturesOfDeletedPoint(feature);
    } else if (feature instanceof geom.LineString) {
      this.#deleteVerticesOfDeletedLineString(feature);
    } else if (feature instanceof geom.Polygon) {
      this.#deleteVerticesOfDeletedPolygon(feature);
    }

    this.#map.removeSource(featureId);
    this.#selectedFeatures.delete(feature);
    if (this.#hoveredFeature?.id === featureId) {
      this.#hoveredFeature = null;
    }
  }

  /**
   * Update the bound features of the specified deleted point.
   * @param point The point that is being deleted.
   */
  #updateBoundFeaturesOfDeletedPoint(point: geom.Point): void {
    point.boundFeatures.forEach(boundFeature => {
      point.unbindFeature(boundFeature);
      const action = boundFeature.removeVertex(point);
      let deletedBound = false;
      if (action.type === "delete_feature") {
        this.removeFeature(boundFeature.id);
        deletedBound = true;
      } else if (action.type === "delete_ring") {
        (boundFeature as geom.Polygon).deleteRing(action.ringIndex);
        // Delete vertices that were only bound to the feature
        action.points.forEach(p => {
          if (p.boundFeatures.count() === 0) {
            this.removeFeature(p.id);
          }
        });
      }
      if (!deletedBound) {
        this.#updateFeatureData(boundFeature);
      }
    });
  }

  /**
   * Delete the vertices that were only bound to the given deleted line.
   * @param line The line being deleted.
   */
  #deleteVerticesOfDeletedLineString(line: geom.LineString): void {
    this.#deleteVerticesOfDeletedLinearFeature(line, line.vertices);
  }

  /**
   * Delete the vertices that were only bound to the given deleted polygon.
   * @param polygon The polygon being deleted.
   */
  #deleteVerticesOfDeletedPolygon(polygon: geom.Polygon): void {
    polygon.vertices
        .forEach(ring => this.#deleteVerticesOfDeletedLinearFeature(polygon, ring));
  }

  /**
   * Delete the vertices that were only bound to the given deleted linear feature.
   * @param feature The feature being deleted.
   * @param vertices A stream of vertices to check for deletion.
   */
  #deleteVerticesOfDeletedLinearFeature(feature: geom.LinearFeature, vertices: st.Stream<geom.Point>): void {
    vertices.forEach(vertex => {
      vertex.unbindFeature(feature);
      if (vertex.boundFeatures.count() === 0) {
        this.removeFeature(vertex.id);
      } else {
        this.#updateFeatureData(vertex);
      }
    });
  }

  /**
   * Quit the current edit mode. Any ongoing drawing is interrupted.
   * @param mousePos The current mouse position. Used to refresh the cursor.
   */
  #disableCurrentEditMode(mousePos?: mgl.PointLike): void {
    switch (this.#editMode) {
      case EditMode.VIEW_ONLY:
      case EditMode.SELECT:
        this.#refreshCursor(mousePos);
        break;
      case EditMode.DRAW_POINT:
        this.#disableDrawPointMode(mousePos);
        break;
      case EditMode.DRAW_LINE:
        this.#disableDrawLineMode(mousePos);
        break;
      case EditMode.DRAW_POLYGON:
        this.#disableDrawPolygonMode(mousePos);
        break;
      case EditMode.MOVE_FEATURES:
        this.#disableMoveFeaturesMode();
        break;
    }
  }

  /**
   * Enable the "draw_point" mode.
   */
  #enableDrawPointMode(): void {
    if (this.#editMode === EditMode.VIEW_ONLY) {
      return;
    }
    this.#disableCurrentEditMode();
    this.#editMode = EditMode.DRAW_POINT;
    this.#setCanvasCursor(Cursor.DRAW);
  }

  /**
   * Disable the "draw_point" mode and go back to "select" mode.
   * Any ongoing drawing is interrupted.
   * @param mousePos The current mouse position.
   */
  #disableDrawPointMode(mousePos?: mgl.PointLike): void {
    this.#editMode = EditMode.SELECT;
    this.#refreshCursor(mousePos);
    this.#drawPointControl.deactivateButton(0);
  }

  /**
   * Enable the "draw_line" mode.
   * If one or both of the arguments are not specified,
   * or the point is not at one end of the line, a new line is created.
   * @param line Optional. The line to continue drawing.
   * @param from If "line" is specified, the point to continue drawing from.
   * Must be at one end of the specified line.
   */
  #enableDrawLineMode(line?: geom.LineString, from?: geom.Point): void {
    if (this.#editMode === EditMode.VIEW_ONLY) {
      return;
    }
    this.#disableCurrentEditMode();
    this.#editMode = EditMode.DRAW_LINE;
    if (line && from && line.isEndVertex(from)) {
      this.#drawnLineString = line;
      this.#draggedPoint = this.#createNewPoint(from.lngLat);
      this.#drawnStringAppendEnd = line.vertices.toArray().indexOf(from) !== 0;
      if (this.#drawnStringAppendEnd) {
        this.#drawnLineString.appendVertex(this.#draggedPoint, this.#drawnLineString.getNextVertexPath());
      } else {
        this.#drawnLineString.appendVertex(this.#draggedPoint, "0");
      }
      this.#updateFeatureData(this.#drawnLineString);
    } else {
      let id: string;
      do { // TODO keep global ID counter
        id = `line-${Math.random()}`;
      } while (this.#features[id]);
      this.#drawnLineString = new geom.LineString((n, t) => this.getDataType(n, t), id);
      this.addFeature(this.#drawnLineString);
    }
    this.#setCanvasCursor(Cursor.DRAW);
  }

  /**
   * Disable the "draw_line" mode and go back to "select" mode.
   * Any ongoing drawing is interrupted.
   * @param mousePos The current mouse position.
   */
  #disableDrawLineMode(mousePos?: mgl.PointLike): void {
    this.#quitLinearDrawing(this.#drawnLineString, 1, mousePos);
    this.#drawnLineString = null;
  }

  /**
   * Enable the "draw_polygon" mode.
   */
  #enableDrawPolygonMode(): void {
    if (this.#editMode === EditMode.VIEW_ONLY) {
      return;
    }
    this.#disableCurrentEditMode();
    this.#editMode = EditMode.DRAW_POLYGON;
    let id: string;
    do { // TODO keep global ID counter
      id = `polygon-${Math.random()}`;
    } while (this.#features[id]);
    this.#drawnPolygon = new geom.Polygon((n, t) => this.getDataType(n, t), id);
    this.addFeature(this.#drawnPolygon);
    this.#setCanvasCursor(Cursor.DRAW);
  }

  /**
   * Disable the "draw_polygon" mode and go back to "select" mode.
   * Any ongoing drawing is interrupted.
   * @param mousePos The current mouse position.
   */
  #disableDrawPolygonMode(mousePos?: mgl.PointLike): void {
    this.#quitLinearDrawing(this.#drawnPolygon, 2, mousePos, () => this.#drawnPolygon.lockRing(0));
    this.#drawnPolygon = null;
  }

  /**
   * Quit the current "draw_line" or "draw_polygon" mode and go back to "select" mode.
   * @param feature The feature currently being drawn.
   * @param buttonIndex The index of the draw control button to deactivate.
   * @param mousePos The current mouse position.
   * @param onValidDrawing Callback called when the current drawing finishes normally.
   */
  #quitLinearDrawing(
      feature: geom.LinearFeature,
      buttonIndex: number,
      mousePos?: mgl.PointLike,
      onValidDrawing?: (() => void)
  ): void {
    this.#editMode = EditMode.SELECT;
    if (feature) {
      let action: geom.Action = null;
      if (this.#draggedPoint) {
        action = feature.removeVertex(this.#draggedPoint);
        this.removeFeature(this.#draggedPoint.id);
        this.#draggedPoint = null;
      }
      if (action?.type === "delete_feature") {
        // FIXME prevent deletion of pre-existing isolated points
        this.removeFeature(feature.id);
        this.#drawnPoints.forEach(p => this.removeFeature(p.id));
      } else {
        if (feature.isEmpty()) {
          this.removeFeature(feature.id);
        } else {
          onValidDrawing?.();
          this.#updateFeatureData(feature);
          this.#selectFeature(feature, false);
        }
      }
      this.#drawnPoints.splice(0);
    }
    this.#refreshCursor(mousePos);
    this.#drawPointControl.deactivateButton(buttonIndex);
  }

  /**
   * Quit the current "move_features" mode and go back to "select" mode.
   * All features that were moved are put back to their position before being moved.
   */
  #disableMoveFeaturesMode() {
    this.#editMode = EditMode.SELECT;
    const features: Set<geom.LinearFeature> = new Set();
    this.#movedPoints.forEach(({point, startPos}) => {
      point.lngLat = startPos;
      this.#updateFeatureData(point);
      point.boundFeatures.forEach(f => features.add(f));
    });
    features.forEach(f => this.#updateFeatureData(f));
    this.#movedPoints.splice(0);
  }

  /**
   * Return the feature currently under the mouse according to the following conditions:
   * * If there are any points, the highest one is returned.
   * * If there are no points, the lowest feature is returned.
   * * If there are no features, null is returned.
   * @param mousePos Mouse position.
   * @returns The feature or null if none are at the given mouses position.
   */
  #getFeatureUnderMouse(mousePos: mgl.PointLike): geom.MapFeature | null {
    const layersOrder = this.#map.getLayersOrder();
    let selectedIndex = Infinity;
    let selectedFeature: geom.MapFeature = null;
    this.#getFeatureIds(mousePos).forEach(featureId => {
      const currentIndex = layersOrder.indexOf(featureId);
      if (currentIndex === -1) {
        return;
      }
      const feature = this.#features[featureId];
      const currentIsPoint = feature instanceof geom.Point;
      const selectedIsNotPoint = !(selectedFeature instanceof geom.Point);
      if (!selectedFeature
          || currentIsPoint && (selectedIsNotPoint || currentIndex > selectedIndex)
          || !currentIsPoint && selectedIsNotPoint && currentIndex < selectedIndex) {
        selectedIndex = currentIndex;
        selectedFeature = feature;
      }
    });
    return selectedFeature;
  }

  /**
   * Return the list of feature IDs that are currently visible.
   * @param at If specified, only the IDs of features under the given pixel position will be returned.
   * @param exclude List of feature IDs to exclude from the results.
   * @returns {} A {@link st.Stream} of distinct feature IDs that correspond to the criteria.
   */
  #getFeatureIds(at?: mgl.PointLike, exclude?: Set<string>): st.Stream<string> {
    return st.stream(this.#map.queryRenderedFeatures(at))
        .filter(f => !exclude?.has(f.source))
        .map(f => f.source)
        .distinct();
  }

  /**
   * Moves a feature’s layers to a different z-position.
   * @param featureId The ID of the feature to move the layer’s of.
   * @param beforeId The ID of an existing feature to insert the layers before.
   * When viewing the map, the `featureId`’s layers will appear beneath the `beforeId`’s layers.
   * If `beforeId` is omitted, the layers will be appended to the end of the layers
   * array and appear above all other layers on the map.
   * @see Map.moveLayer
   */
  #moveLayers(featureId: string, beforeId?: string): void {
    if (beforeId) {
      const bottomLayer = this.#getLayerIdStack(beforeId)[0];
      this.#getLayerIdStack(featureId).forEach(id => this.#map.moveLayer(id, bottomLayer));
    } else {
      this.#getLayerIdStack(featureId).forEach(id => this.#map.moveLayer(id));
    }
  }

  /**
   * Return the stack of layer IDs for the given feature ID.
   * @param featureId A feature’s ID.
   * @returns The IDs stack as a string array or null if the feature was not found.
   */
  #getLayerIdStack(featureId: string): string[] | null {
    const feature = this.#features[featureId];
    if (feature instanceof geom.Point) {
      return [feature.id + "-highlight", feature.id];
    } else if (feature instanceof geom.LineString) {
      return [feature.id + "-highlight", feature.id, feature.id + "-foreground"];
    } else if (feature instanceof geom.Polygon) {
      return [feature.id, feature.id + "-highlight", feature.id + "-border"];
    } else {
      return null;
    }
  }

  /**
   * Hide associated layers for zoom < MapEditor.EDIT_MIN_ZOOM.
   */
  static readonly #FILTER_TOGGLE_VISIBILITY_FOR_ZOOM: mgl.FilterSpecification = [
    "step", ["zoom"],
    false, // If 0 <= zoom < MapEditor.EDIT_MIN_ZOOM
    MapEditor.#EDIT_MIN_ZOOM, true // If MapEditor.EDIT_MIN_ZOOM <= zoom
  ];
  /**
   * Select a color depending on the feature’s "selectionMode" property.
   */
  static readonly #CHOOSE_COLOR_FOR_SELECTION_MODE: mgl.DataDrivenPropertyValueSpecification<mgl.ColorSpecification> = [
    "match", ["get", "selectionMode"],
    geom.SelectionMode.SELECTED, MapEditor.#HIGHLIGHT_SELECTED_COLOR, // Case 1
    geom.SelectionMode.HOVERED, MapEditor.#HIGHLIGHT_HOVERED_COLOR, // Case 2
    MapEditor.#HIGHLIGHT_BASE_COLOR, // Default
  ];

  /**
   * Create the layers for the given feature and add them to the map.
   * @param feature A feature.
   * @see https://maplibre.org/maplibre-style-spec/expressions/
   */
  #addLayersForFeature(feature: geom.MapFeature): void {
    if (feature instanceof geom.Point) {
      this.#map.addLayer({
        id: feature.id + "-highlight",
        type: "circle",
        source: feature.id,
        paint: {
          "circle-radius": ["+", ["get", "radius"], 4],
          "circle-color": MapEditor.#CHOOSE_COLOR_FOR_SELECTION_MODE,
        },
        filter: MapEditor.#FILTER_TOGGLE_VISIBILITY_FOR_ZOOM,
      });
      this.#map.addLayer({
        id: feature.id,
        type: "circle",
        source: feature.id,
        paint: {
          "circle-radius": ["get", "radius"],
          "circle-color": ["get", "color"],
          "circle-stroke-width": 1,
          "circle-stroke-color": MapEditor.#BORDER_COLOR,
        },
        filter: MapEditor.#FILTER_TOGGLE_VISIBILITY_FOR_ZOOM,
      });

    } else if (feature instanceof geom.LineString) {
      this.#map.addLayer({
        id: feature.id + "-highlight",
        type: "line",
        source: feature.id,
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
        paint: {
          "line-width": ["+", ["get", "width"], 8],
          "line-color": MapEditor.#CHOOSE_COLOR_FOR_SELECTION_MODE,
        },
        filter: MapEditor.#FILTER_TOGGLE_VISIBILITY_FOR_ZOOM,
      });
      this.#map.addLayer({
        id: feature.id,
        type: "line",
        source: feature.id,
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
        paint: {
          "line-width": ["get", "width"],
          "line-color": ["step", ["zoom"],
            MapEditor.#NON_EDITABLE_COLOR, // If 0 < zoom < MapEditor.EDIT_MIN_ZOOM
            MapEditor.#EDIT_MIN_ZOOM, ["get", "color"], // If zoom >= MapEditor.EDIT_MIN_ZOOM
          ],
        },
      });
      this.#map.addLayer({
        id: feature.id + "-foreground",
        type: "line",
        source: feature.id,
        layout: {
          "line-cap": "butt",
          "line-join": "round",
        },
        paint: {
          "line-width": ["get", "fgWidth"],
          "line-color": ["get", "fgColor"],
        },
        filter: MapEditor.#FILTER_TOGGLE_VISIBILITY_FOR_ZOOM,
      });

    } else if (feature instanceof geom.Polygon) {
      this.#map.addLayer({
        id: feature.id,
        type: "fill",
        source: feature.id,
        paint: {
          "fill-color": ["concat", ["get", "color"], "30"], // Add transparency
        },
        filter: MapEditor.#FILTER_TOGGLE_VISIBILITY_FOR_ZOOM,
      });
      this.#map.addLayer({
        id: feature.id + "-highlight",
        type: "line",
        source: feature.id,
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
        paint: {
          "line-width": 8,
          "line-color": MapEditor.#CHOOSE_COLOR_FOR_SELECTION_MODE,
        },
        filter: MapEditor.#FILTER_TOGGLE_VISIBILITY_FOR_ZOOM,
      });
      this.#map.addLayer({
        id: feature.id + "-border",
        type: "line",
        source: feature.id,
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
        paint: {
          "line-color": ["get", "color"],
        },
        filter: MapEditor.#FILTER_TOGGLE_VISIBILITY_FOR_ZOOM,
      });
    } else {
      throw TypeError(`Unexpected type: ${feature}`);
    }
    this.#onObjectDataUpdate(feature);
  }

  #onObjectDataUpdate(feature: geom.MapFeature): void { // TODO call when relevant
    if (feature instanceof geom.LineString) {
      this.#map.setPaintProperty(feature.id, "line-dasharray", feature.properties.dash);
      this.#map.setPaintProperty(feature.id + "-foreground", "line-dasharray", feature.properties.fgDash);
    }
  }

  /**
   * Set the cursor for the map’s canvas.
   * @param cursor The cursor type.
   */
  #setCanvasCursor(cursor: Cursor): void {
    this.#$canvasContainer.addClass(`cursor-${cursor}`);
    for (const c of Object.values(Cursor)) {
      if (c !== cursor) {
        this.#$canvasContainer.removeClass(`cursor-${c}`);
      }
    }
  }

  /**
   * Called when the mouse moves over the map.
   * @param e The mouse event.
   */
  #onMouseMouve(e: mgl.MapMouseEvent | mgl.MapTouchEvent): void {
    this.#mousePositionCache = e.lngLat;
    if (this.#editMode === EditMode.VIEW_ONLY) {
      return;
    }
    if (this.#editMode === EditMode.MOVE_FEATURES) {
      this.#onMoveFeatures(e);
      return;
    }
    const hoveredFeature: geom.MapFeature = this.#getFeatureUnderMouse(e.point);
    if (hoveredFeature) {
      if (!this.#draggedPoint) {
        this.#setHover(hoveredFeature);
      }
    } else {
      this.#clearHover();
    }

    if (this.#draggedPoint) {
      this.#onDragPoint(e);
    } else {
      this.#refreshCursor();
    }
  }

  /**
   * Called when a {@link Point} is dragged.
   * @param e The mouse event.
   */
  #onDragPoint(e: mgl.MapMouseEvent | mgl.MapTouchEvent): void {
    this.#clearSelection();
    this.#setCanvasCursor(Cursor.DRAW);

    // Prevent linear features from connecting to themselves
    // -> exclude points bound to the bound features of the dragged point
    const excludedIds: Set<string> = new Set();
    this.#draggedPoint.boundFeatures.forEach(f => {
      excludedIds.add(f.id);
      // Exclude all the feature’s points
      if (f instanceof geom.LineString) {
        f.vertices.forEach(v => excludedIds.add(v.id));
      } else if (f instanceof geom.Polygon) {
        f.vertices
            .flatMap(s => s)
            .forEach(v => excludedIds.add(v.id));
      }
    });
    // Exclude point itself
    excludedIds.add(this.#draggedPoint.id);
    const features = this.#getFeatureIds(null, excludedIds)
        .map(id => this.#features[id])
        .toArray();
    const snapResult = snap.trySnapPoint(e.lngLat, features, this.#map.getZoom());
    this.#snapResult = null;

    if (snapResult) {
      if (snapResult.type === "point" || snapResult.type === "segment_vertex") {
        let point: geom.Point;
        if (snapResult.type === "point") {
          point = snapResult.point;
        } else {
          const {feature, path} = snapResult;
          point = feature.getVertex(path);
        }
        const canSnap = point.boundFeatures.allMatch(
            f => f.canAcceptVertex(this.#draggedPoint));
        if (canSnap) {
          this.#snapResult = snapResult;
          // Move dragged point to the snap position
          this.#draggedPoint.onDrag(point.lngLat);
          this.#setHover(point);
          this.#setCanvasCursor(Cursor.CONNECT_VERTEX);
        }
      } else { // segment
        const {feature, path, lngLat} = snapResult;
        let canSnap = feature.canInsertVertex(this.#draggedPoint, path);

        let p1: geom.Point, p2: geom.Point;
        if (canSnap) {
          [p1, p2] = feature.getSegmentVertices(path);
          // Check if any excluded feature shares the same segment
          for (const id of excludedIds) {
            const f = this.#features[id];
            if (f instanceof geom.LinearFeature && f.getSegmentPath(p1, p2)) {
              // An excluded feature shares the segment, cancel snapping
              canSnap = false;
              break
            }
          }
        }

        if (canSnap) {
          const otherFeatures: { feature: geom.LinearFeature, path: string }[] = [];
          // Get all non-excluded features that share the same segment
          features.forEach(f => {
            if (f instanceof geom.LinearFeature && f !== feature) {
              const path = f.getSegmentPath(p1, p2);
              if (path) {
                otherFeatures.push({
                  feature: f,
                  path: path,
                });
              }
            }
          });

          this.#snapResult = snapResult;
          if (otherFeatures.length) {
            // Add all features that share the same segment
            this.#snapResult.featuresWithSameSegment = otherFeatures;
          }
          // Move dragged point to the snap position
          this.#draggedPoint.onDrag(lngLat);
          this.#setHover(feature);
          this.#setCanvasCursor(Cursor.CONNECT_LINE);
        }
      }
    }

    if (!this.#snapResult) {
      this.#clearHover();
      this.#draggedPoint.onDrag(e.lngLat);
      if (this.#editMode === EditMode.DRAW_LINE && this.#canFinishLineDrawing(e.point)[0]
          || this.#editMode === EditMode.DRAW_POLYGON && this.#canFinishPolygonDrawing(e.point)[0]) {
        this.#setCanvasCursor(Cursor.CONNECT_VERTEX);
      }
    }

    this.#updateFeatureData(this.#draggedPoint);
    this.#draggedPoint.boundFeatures.forEach(f => this.#updateFeatureData(f));
  }

  /**
   * Check whether the line feature currently being drawn can be finished.
   * @param p The current mouse cursor position.
   * @returns A tuple with a boolean indicating whether the drawing can be finished,
   * and the last drawn vertex of the feature.
   */
  #canFinishLineDrawing(p: mgl.PointLike): [boolean, geom.Point | null] {
    const verticesNb = this.#drawnLineString.vertices.count();
    if (verticesNb <= 2) {
      return [false, null];
    }
    const features = this.#getFeatureIds(p);
    const lastVertex = this.#drawnStringAppendEnd
        && this.#drawnLineString.getVertex("" + (verticesNb - 2))
        || this.#drawnLineString.getVertex("1");
    return [features.anyMatch(id => id === lastVertex.id), lastVertex];
  }

  /**
   * Check whether the polygon feature currently being drawn can be finished.
   * @param p The current mouse cursor position.
   * @returns A tuple with a boolean indicating whether the drawing can be finished,
   * and the last drawn vertex of the feature.
   */
  #canFinishPolygonDrawing(p: mgl.PointLike): [boolean, geom.Point | null] {
    const externalRing = this.#drawnPolygon.vertices.findFirst();
    if (externalRing.map(ring => ring.count() <= 3).orElse(true)) {
      return [false, null];
    }
    const features = this.#getFeatureIds(p);
    const lastVertex =
        this.#drawnPolygon.getVertex("0." + (externalRing.get().count() - 2));
    return [features.anyMatch(id => id === lastVertex.id), lastVertex];
  }

  /**
   * Called when a {@link MapFeature} is moved.
   * @param e The mouse event.
   */
  #onMoveFeatures(e: mgl.MapMouseEvent | mgl.MapTouchEvent): void {
    this.#setCanvasCursor(Cursor.GRABBING);
    const features: Set<geom.LinearFeature> = new Set();
    this.#movedPoints.forEach(({point, offset}) => {
      point.onDrag(e.lngLat, offset);
      this.#updateFeatureData(point);
      point.boundFeatures.forEach(f => features.add(f));
    });
    // Update each bound feature only once
    features.forEach(f => this.#updateFeatureData(f));
  }

  /**
   * Called when the mouse is pressed down on the map.
   * @param e The mouse event.
   */
  #onMouseDown(e: mgl.MapMouseEvent | mgl.MapTouchEvent): void {
    if (this.#editMode === EditMode.SELECT) {
      // Cannot use instanceof on "e" so we have to test its "type" property to narrow its type
      if (e.type === "mousedown" && utils.isSecondaryClick(e.originalEvent)) {
        // We check manually for a secondary mouse button click
        // as the "contextmenu" event seems to not fire on circle features
        this.#onContextMenu(e);
        return;
      }
      if (this.#hoveredFeature instanceof geom.Point) {
        e.preventDefault();
        this.#draggedPoint = this.#hoveredFeature;
        this.#moveLayers(this.#draggedPoint.id); // Put on top
      } else {
        this.#setCanvasCursor(Cursor.GRABBING);
      }
    }
    if (this.#contextMenu.isVisible()) {
      this.#contextMenu.hide();
    }
  }

  /**
   * Called when the mouse is released on the map.
   * @param e The mouse event.
   */
  #onMouseUp(e: mgl.MapMouseEvent | mgl.MapTouchEvent): void {
    if (this.#editMode !== EditMode.SELECT) {
      return;
    }
    if (this.#snapResult) {
      if (this.#snapResult.type === "point" || this.#snapResult.type === "segment_vertex") {
        const point = this.#getSnappedPoint();
        this.#draggedPoint.onDrag(point.lngLat);
        if (point.dataObject && !this.#draggedPoint.dataObject) {
          this.#draggedPoint.copyDataOf(point);
        }
        point.boundFeatures.forEach(
            f => f.replaceVertex(this.#draggedPoint, point));
        this.removeFeature(point.id);
      } else { // segment
        this.#addSnappedPointToSegment();
      }
      this.#draggedPoint.boundFeatures.forEach(f => this.#updateFeatureData(f));
      this.#updateFeatureData(this.#draggedPoint);
      this.#moveLayers(this.#draggedPoint.id); // Put point on top
      this.#snapResult = null;
    }
    if (this.#draggedPoint) {
      this.#setHover(this.#draggedPoint);
      this.#draggedPoint = null;
    }
    this.#refreshCursor(e.point);
  }

  /**
   * Called when the mouse is clicked on the map.
   * @param e The mouse event.
   */
  #onClick(e: mgl.MapMouseEvent): void {
    switch (this.#editMode) {
      case EditMode.DRAW_POINT:
        this.#drawPoint(e);
        break;
      case EditMode.DRAW_LINE:
        this.#drawLinearFeatureVertex(this.#drawnLineString, e);
        break;
      case EditMode.DRAW_POLYGON:
        this.#drawLinearFeatureVertex(this.#drawnPolygon, e);
        break;
      case EditMode.MOVE_FEATURES:
        this.#placeMovedFeatures(e);
        break;
      case EditMode.SELECT:
        if (this.#hoveredFeature) {
          const keepSelection = e.originalEvent.ctrlKey && this.#editMode === EditMode.SELECT;
          this.#selectFeature(this.#hoveredFeature, keepSelection);
        } else {
          this.#clearSelection();
        }
        break;
      case EditMode.VIEW_ONLY:
        this.#clearSelection();
        break;
    }
  }

  /**
   * Called when the user requests the context menu.
   * @param e The mouse event.
   */
  #onContextMenu(e: mgl.MapMouseEvent): void {
    const buttonStates: ctxMenu.ButtonStatesOptions = {};
    if (this.#hoveredFeature) {
      if (this.#hoveredFeature.selectionMode !== geom.SelectionMode.SELECTED) {
        this.#selectFeature(this.#hoveredFeature, false);
      }
      // We do not use the count() method as streams may contain filters that would
      // force them to be iterated over in full and that could be costly.
      // The findFirst() only iterates over a single element if the stream is not empty,
      // we can thus save a lot of time that way.
      buttonStates.move = this.#getMoveFeaturesActionCandidates().findFirst().isPresent();
      buttonStates.copy = this.#getCopyFeaturesActionCandidates().findFirst().isPresent();
      buttonStates.delete = this.#getDeleteFeaturesActionCandidates().findFirst().isPresent();
      buttonStates.continueLine = this.#getContinueLineActionCandidate() !== null;
      buttonStates.disconnect = this.#getDisconnectVerticesActionCandidates().findFirst().isPresent();
      buttonStates.extractPoint = this.#getExtractVerticesActionCandidates().findFirst().isPresent();
      buttonStates.split = this.#getSplitLinesActionCandidates().findFirst().isPresent();
      buttonStates.circularize = this.#getCircularizeFeaturesActionCandidates().findFirst().isPresent();
      buttonStates.square = this.#getSquareFeaturesActionCandidates().findFirst().isPresent();
      const canFlip = this.#getFlipFeaturesActionCandidates().findFirst().isPresent();
      buttonStates.flipLong = canFlip;
      buttonStates.flipShort = canFlip;
      buttonStates.reverseLine = this.#getReverseLinesActionCandidates().findFirst().isPresent();
      buttonStates.rotate = this.#getRotateFeaturesActionCandidates().findFirst().isPresent();
      buttonStates.straightenLine = this.#getStraightenLinesActionCandidates().findFirst().isPresent();
    } else {
      buttonStates.paste = this.#getPasteFeaturesActionCandidates().findFirst().isPresent();
      this.#clearSelection();
    }
    this.#contextMenu.show(e.lngLat, buttonStates);
  }

  /**
   * Draw a point feature at the mouse cursor’s position.
   * @param e The mouse event.
   */
  #drawPoint(e: mgl.MapMouseEvent): void {
    this.#selectFeature(this.#drawNewPoint(e), false);
    this.#disableDrawPointMode(e.point);
  }

  /**
   * Draw a vertex of the currently drawn feature at the mouse cursor’s position.
   * @param feature The feature to draw the point for.
   * @param e The mouse event.
   */
  #drawLinearFeatureVertex(feature: geom.LinearFeature, e: mgl.MapMouseEvent): void {
    if (this.#snapResult) {
      if (this.#snapResult.type === "point" || this.#snapResult.type === "segment_vertex") {
        const point = this.#getSnappedPoint();
        // Keep already existing point
        feature.replaceVertex(point, this.#draggedPoint);
        this.removeFeature(this.#draggedPoint.id);
        this.#moveLayers(point.id); // Put point on top
        this.#draggedPoint = null;
      } else { // segment
        this.#addSnappedPointToSegment();
        this.#drawnPoints.push(this.#draggedPoint);
      }
      this.#snapResult = null;

    } else {
      const [canFinish, lastVertex] = feature instanceof geom.LineString
          ? this.#canFinishLineDrawing(e.point)
          : this.#canFinishPolygonDrawing(e.point);
      if (canFinish) {
        this.#setHover(lastVertex);
        this.#setCanvasCursor(Cursor.POINT);
        if (feature instanceof geom.LineString) {
          this.#disableDrawLineMode(e.point);
        } else {
          this.#disableDrawPolygonMode(e.point);
        }
        return;
      }

      if (!this.#draggedPoint) {
        const point = this.#drawNewPoint(e);
        if (point !== this.#hoveredFeature) {
          this.#drawnPoints.push(point);
        }
        if (feature instanceof geom.LineString && !this.#drawnStringAppendEnd) {
          feature.appendVertex(point, "0");
        } else {
          feature.appendVertex(point, feature.getNextVertexPath());
        }
        this.#updateFeatureData(point);
      }
    }

    const prevPoint = this.#draggedPoint;
    // Create next point
    this.#draggedPoint = this.#createNewPoint(e.lngLat);
    if (feature instanceof geom.LineString && !this.#drawnStringAppendEnd) {
      feature.appendVertex(this.#draggedPoint, "0");
    } else {
      feature.appendVertex(this.#draggedPoint, feature.getNextVertexPath());
    }
    if (prevPoint) {
      this.#updateFeatureData(prevPoint);
    }
    this.#updateFeatureData(feature);
    if (feature instanceof geom.LineString && feature.vertices.count() > 2
        || feature instanceof geom.Polygon && feature.vertices.findFirst().get().count() > 3) {
      this.#setCanvasCursor(Cursor.CONNECT_VERTEX);
    }
  }

  /**
   * Draw a new point feature at the mouse cursor’s position.
   * If the point falls on a pre-existing one, the latter is returned.
   * If the point falls on a pre-existing segment, it is added to it before being returned.
   * Otherwise the point is created as is then returned.
   * @param e The mouse event.
   * @returns The newly created point or a pre-existing one.
   */
  #drawNewPoint(e: mgl.MapMouseEvent): geom.Point {
    let point: geom.Point;
    if (this.#hoveredFeature instanceof geom.Point) {
      // Select existing point instead of creating a new one
      point = this.#hoveredFeature;
    } else if (!(point = this.#createNewPointOnHoveredSegment(e))) {
      point = this.#createNewPoint(e.lngLat);
    }
    this.#moveLayers(point.id); // Put point on top
    return point;
  }

  /**
   * If the current snap result has type "point" or "segment vertex", returns the point matching the result.
   * Otherwise null is returned.
   */
  #getSnappedPoint(): geom.Point | null {
    if (this.#snapResult.type === "point") {
      return this.#snapResult.point;
    } else if (this.#snapResult.type === "segment_vertex") {
      const {feature, path} = this.#snapResult;
      return feature.getVertex(path);
    }
    return null;
  }

  /**
   * If the current snap result has type "segment", adds the dragged point to the snapped segment.
   * All features that share that same segment are updated.
   */
  #addSnappedPointToSegment(): void {
    if (this.#snapResult.type === "segment") {
      const {feature, path, lngLat} = this.#snapResult;
      this.#draggedPoint.onDrag(lngLat);
      feature.insertVertexAfter(this.#draggedPoint, path);
      // Insert vertex to all features that share the same segment
      this.#snapResult.featuresWithSameSegment?.forEach(
          ({feature, path}) => feature.insertVertexAfter(this.#draggedPoint, path));
      this.#moveLayers(this.#draggedPoint.id); // Put point on top
    }
  }

  /**
   * Place down all features that are currently being moved.
   * @param e The mouse event.
   */
  #placeMovedFeatures(e: mgl.MapMouseEvent) {
    this.#editMode = EditMode.SELECT;
    this.#movedPoints.splice(0);
    this.#refreshCursor(e.point);
  }

  /**
   * Called when the mouse is double-clicked on the map.
   * @param e The mouse event.
   */
  #onDoubleClick(e: mgl.MapMouseEvent): void {
    if (this.#hoveredFeature) {
      this.#createNewPointOnHoveredSegment(e);
      this.#refreshCursor(e.point);
    }
  }

  /**
   * Called when a key is pressed.
   * @param e The keyboard event.
   */
  #onKeyDown(e: KeyboardEvent): void {
    if (this.#editMode === EditMode.SELECT) {
      if (e.key === "Delete") {
        this.#deleteSelectedFeatures();
      }
    } else {
      if (e.key === "Escape") {
        // Interrupt any ongoing drawings
        this.#disableCurrentEditMode();
      }
    }
  }

  /**
   * Called right before the map’s zoom level changes.
   */
  #onZoomChangeStart(): void {
    if (this.#draggedPoint) {
      // Prevent unzooming past threshold if a point is being dragged
      this.#map.setMinZoom(MapEditor.#EDIT_MIN_ZOOM);
    } else {
      this.#map.setMinZoom(0);
    }
  }

  /**
   * Called right after the map’s zoom level has changed.
   */
  #onZoomChangeEnd(): void {
    const zoom = this.#map.getZoom();
    if (zoom < MapEditor.#EDIT_MIN_ZOOM && this.#editMode !== EditMode.VIEW_ONLY) {
      this.#disableCurrentEditMode(); // Interrupt any action
      this.#editMode = EditMode.VIEW_ONLY;
      this.#clearHover();
      this.#setCanvasCursor(Cursor.GRAB);
      for (let i = 0; i < 3; i++) {
        this.#drawPointControl.setButtonDisabled(i, true);
      }
      this.#$editZoomNoticePanel.show();
    } else if (zoom >= MapEditor.#EDIT_MIN_ZOOM && this.#editMode === EditMode.VIEW_ONLY) {
      this.#editMode = EditMode.SELECT;
      for (let i = 0; i < 3; i++) {
        this.#drawPointControl.setButtonDisabled(i, false);
      }
      this.#$editZoomNoticePanel.hide();
    }
  }

  /**
   * Create a point at the given position on the currently hovered segment.
   * The current selection set is not changed.
   * @param e The mouse event.
   * @returns The newly created point or null if none were.
   */
  #createNewPointOnHoveredSegment(e: mgl.MapMouseEvent): geom.Point | null {
    if (this.#hoveredFeature instanceof geom.LinearFeature) {
      // Search which linear feature was clicked
      const features = this.#getFeatureIds(e.point)
          .map(id => this.#features[id])
          .filter(f => f instanceof geom.LinearFeature)
          .toArray()

      const snapResult = snap.trySnapPoint(e.lngLat, features, this.#map.getZoom());
      // User clicked near a line, add a new point to it
      if (snapResult?.type === "segment") {
        const {feature, path, lngLat} = snapResult;

        const newPoint: geom.Point = this.#createNewPoint(lngLat);
        const [p1, p2] = feature.getSegmentVertices(path);
        const update = (feature: geom.LinearFeature, path: string) => {
          feature.insertVertexAfter(newPoint, path);
          this.#updateFeatureData(feature);
        };
        update(feature, path);
        // Update all features that share the same segment
        features.forEach(f => {
          if (f instanceof geom.LinearFeature && f !== feature) {
            const path = f.getSegmentPath(p1, p2);
            if (path) {
              update(f, path);
            }
          }
        });
        return newPoint;
      }
    }
    return null;
  }

  /**
   * Set the hovered feature. If a feature was already hovered and is not selected, its highlight is removed.
   * If the feature is selected, its highlight color is not changed.
   * @param feature The feature to set as being hovered.
   * @throws {Error} If the feature is null.
   */
  #setHover(feature: geom.MapFeature): void {
    if (!feature) {
      throw new Error("Missing feature");
    }
    if (this.#hoveredFeature === feature) {
      return;
    }
    if (this.#hoveredFeature && !this.#selectedFeatures.has(this.#hoveredFeature)) {
      this.#hoveredFeature.selectionMode = geom.SelectionMode.NONE;
      this.#updateFeatureData(this.#hoveredFeature);
    }
    this.#hoveredFeature = feature;
    if (!this.#selectedFeatures.has(this.#hoveredFeature)) {
      this.#hoveredFeature.selectionMode = geom.SelectionMode.HOVERED;
      this.#updateFeatureData(this.#hoveredFeature);
    }
    this.#map.fire(new events.FeatureHoverEvent(this.#hoveredFeature));
  }

  /**
   * Clear the currently hovered feature.
   */
  #clearHover(): void {
    if (this.#hoveredFeature) {
      if (!this.#selectedFeatures.has(this.#hoveredFeature)) {
        this.#hoveredFeature.selectionMode = geom.SelectionMode.NONE;
        this.#updateFeatureData(this.#hoveredFeature);
      }
      this.#hoveredFeature = null;
      this.#map.fire(new events.FeatureHoverEvent());
    }
  }

  /**
   * Select the given feature.
   * @param feature The feature to select.
   * @param keepSelection If true, the feature will be added to the current selection list,
   * otherwise the list is cleared beforehand.
   * @throws {Error} If the feature is null.
   */
  #selectFeature(feature: geom.MapFeature, keepSelection: boolean): void {
    if (!feature) {
      throw new Error("Missing feature");
    }
    let changed = false;
    if (this.#selectedFeatures.size && !keepSelection) {
      this.#clearSelection(false);
      changed = true;
    }
    if (!this.#selectedFeatures.has(feature)) {
      this.#selectedFeatures.add(feature);
      feature.selectionMode = geom.SelectionMode.SELECTED;
      this.#updateFeatureData(feature);
      changed = true;
    }
    if (changed) { // Only fire if the selection set changed
      this.#map.fire(new events.FeatureSelectionEvent([...this.#selectedFeatures]));
    }
  }

  /**
   * Clear the current selection.
   * @param fire If true and the selection set changed, an event is fired; otherwise an event is never fired.
   */
  #clearSelection(fire: boolean = true): void {
    if (this.#selectedFeatures.size) {
      this.#selectedFeatures.forEach(feature => {
        feature.selectionMode = geom.SelectionMode.NONE;
        this.#updateFeatureData(feature);
      });
      this.#selectedFeatures.clear();
      if (fire) {
        this.#map.fire(new events.FeatureSelectionEvent());
      }
    }
  }

  /**
   * In "select" mode, refresh the mouse cursor based on the currently hovered feature.
   * If the edit mode is something else, nothing happens.
   *
   * @param mousePos The mouse position. If specified, the feature under the mouse position will be used instead.
   */
  #refreshCursor(mousePos?: mgl.PointLike): void {
    if (this.#editMode === EditMode.SELECT) {
      let feature: geom.MapFeature;
      if (mousePos) {
        feature = this.#getFeatureUnderMouse(mousePos);
      } else {
        feature = this.#hoveredFeature;
      }
      if (feature) {
        const cursor = {
          "Point": Cursor.POINT,
          "LineString": Cursor.LINE,
          "Polygon": Cursor.POLYGON,
        }[feature.geometry.type];
        this.#setCanvasCursor(cursor);
      } else {
        this.#setCanvasCursor(Cursor.GRAB);
      }
    }
  }

  /**
   * Create a new point at the given position.
   * @param lngLat The point’s position.
   * @returns The newly created point.
   */
  #createNewPoint(lngLat: mgl.LngLat): geom.Point {
    let id: string;
    do { // TODO keep global ID counter
      id = `point-${Math.random()}`;
    } while (this.#features[id]);
    const newPoint = new geom.Point((n, t) => this.getDataType(n, t), id, lngLat);
    this.addFeature(newPoint);
    return newPoint;
  }

  /**
   * Return all values that are currently eligible for the "move features" action:
   * * all selected features.
   */
  #getMoveFeaturesActionCandidates(): st.Stream<geom.MapFeature> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    // Eliminate points that are bound to a selected linear feature
    return st.stream(this.#selectedFeatures)
        .filter(f => {
          return !(f instanceof geom.Point) || !f.boundFeatures.anyMatch(ff => {
            return this.#selectedFeatures.has(ff);
          });
        });
  }

  /**
   * Move the selected features.
   */
  #moveSelectedFeatures(): void {
    this.#movedPoints.splice(0);
    const points: Set<geom.Point> = new Set();

    this.#getMoveFeaturesActionCandidates().forEach(f => {
      if (f instanceof geom.Point) {
        points.add(f);
        this.#movedPoints.push({
          point: f,
          offset: geom.LngLatVector.sub(f.lngLat, this.#mousePositionCache),
          startPos: f.lngLat,
        });

      } else if (f instanceof geom.LineString) {
        // Add all vertices to the list
        f.vertices.forEach(v => {
          if (!points.has(v)) {
            points.add(v);
            this.#movedPoints.push({
              point: v,
              offset: geom.LngLatVector.sub(v.lngLat, this.#mousePositionCache),
              startPos: v.lngLat,
            });
          }
        });

      } else if (f instanceof geom.Polygon) {
        // Add all vertices of all rings to the list
        f.vertices
            .flatMap(s => s)
            .forEach(v => {
              if (!points.has(v)) {
                points.add(v);
                this.#movedPoints.push({
                  point: v,
                  offset: geom.LngLatVector.sub(v.lngLat, this.#mousePositionCache),
                  startPos: v.lngLat,
                });
              }
            });
      }
    });

    if (this.#movedPoints.length) {
      this.#editMode = EditMode.MOVE_FEATURES;
      this.#setCanvasCursor(Cursor.GRABBING);
    }
  }

  /**
   * Return all values that are currently eligible for the "copy features" action:
   * * all selected features.
   */
  #getCopyFeaturesActionCandidates(): st.Stream<geom.MapFeature> {
    return this.#editMode === EditMode.SELECT ? st.stream(this.#selectedFeatures) : st.emptyStream();
  }

  #copySelectedFeatures(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return all values that are currently eligible for the "paste features" action:
   * * TODO
   */
  #getPasteFeaturesActionCandidates(): st.Stream<geom.MapFeature> {
    return st.emptyStream(); // TODO
  }

  #pasteFeatures(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return all values that are currently eligible for the "delete features" action:
   * * all selected features.
   */
  #getDeleteFeaturesActionCandidates(): st.Stream<geom.MapFeature> {
    return this.#editMode === EditMode.SELECT ? st.stream(this.#selectedFeatures) : st.emptyStream();
  }

  /**
   * If in "select" mode, delete the currently selected features and clear the selection set.
   */
  #deleteSelectedFeatures(): void {
    this.#getDeleteFeaturesActionCandidates()
        .forEach(f => this.removeFeature(f.id));
    this.#selectedFeatures.clear();
  }

  /**
   * Return the point that is currently eligible for the "continue line" action along with the line that matched:
   * * only one point is selected and that point is at the end of exactly one line.
   */
  #getContinueLineActionCandidate(): [geom.Point, geom.LineString] | null {
    if (this.#editMode !== EditMode.SELECT || this.#selectedFeatures.size !== 1) {
      return null;
    }
    const v: geom.MapFeature = this.#selectedFeatures.values().next().value;
    if (!(v instanceof geom.Point)) {
      return null;
    }
    let line: geom.LineString;
    // Vertex must be the first/last vertex of exactly one line
    for (const f of v.boundFeatures.toGenerator()) {
      if (f instanceof geom.LineString && f.isEndVertex(v)) {
        if (line) {
          return null;
        }
        line = f;
      }
    }
    return line ? [v, line] : null;
  }

  /**
   * Continue drawing the line the selected vertex is at one end of.
   */
  #continueSelectedLine(): void {
    const candidate = this.#getContinueLineActionCandidate();
    if (candidate) {
      const [point, line] = candidate;
      this.#enableDrawLineMode(line, point);
    }
  }

  /**
   * Return the points that are currently eligible for the "disconnect vertices" action:
   * * all selected points that are bound to at least two features.
   */
  #getDisconnectVerticesActionCandidates(): st.Stream<geom.Point> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    return st.stream(this.#selectedFeatures)
        .filter(f => f instanceof geom.Point
            && f.boundFeatures.count() >= 2) as st.Stream<geom.Point>;
  }

  #disconnectSelectedVertices(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return the points that are currently eligible for the "extract vertices" action:
   * * all selected points with data that are bound to at least one feature.
   */
  #getExtractVerticesActionCandidates(): st.Stream<geom.Point> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    return st.stream(this.#selectedFeatures)
        .filter(f => f instanceof geom.Point
            && f.dataObject && f.boundFeatures.count() !== 0) as st.Stream<geom.Point>;
  }

  #extractSelectedVertices(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return the lines that are currently eligible for the "split lines" action,
   * along with the indices where to split them:
   * * all lines that have selected points and the latter are not at any end of the former.
   */
  #getSplitLinesActionCandidates(): st.Stream<[geom.LineString, number[]]> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    const idToIndex: { [id: string]: number } = {};
    const lines: [geom.LineString, number[]][] = [];
    for (const f of this.#selectedFeatures) {
      if (f instanceof geom.Point && f.boundFeatures.count() !== 0) {
        f.boundFeatures.forEach(ff => {
          if (ff instanceof geom.LineString && !ff.isEndVertex(f)) {
            const i = ff.vertices.toArray().indexOf(f);
            if (!idToIndex[ff.id]) {
              idToIndex[ff.id] = lines.length;
              lines.push([ff, [i]]);
            } else {
              lines[idToIndex[ff.id]][1].push(i);
            }
          }
        });
      }
    }
    return st.stream(lines);
  }

  #splitSelectedLines(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return the linear features that are currently eligible for the "circularize features" action:
   * * all selected polygons that are already nearly circular.
   * * all selected lines that form a loop that are already nearly circular.
   * @see geom.LinearFeature.isNearlyCircular
   */
  #getCircularizeFeaturesActionCandidates(): st.Stream<geom.LinearFeature> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    return st.stream(this.#selectedFeatures)
        .filter(f =>
            (f instanceof geom.Polygon || f instanceof geom.LineString && f.isLoop()) && f.isNearlyCircular()) as st.Stream<geom.LinearFeature>;
  }

  #circularizeSelectedFeatures(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return the linear features that are currently eligible for the "square features" action:
   * * all selected polygons that are already nearly square.
   * * all selected lines that form a loop that are already nearly square.
   * @see geom.LinearFeature.isNearlySquare
   */
  #getSquareFeaturesActionCandidates(): st.Stream<geom.LinearFeature> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    return st.stream(this.#selectedFeatures)
        .filter(f =>
            (f instanceof geom.Polygon || f instanceof geom.LineString && f.isLoop()) && f.isNearlySquare()) as st.Stream<geom.LinearFeature>;
  }

  #squareSelectedFeatures(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return the features that are currently eligible for the "flip long features" action:
   * * all selected features, as long as it is not a single point, two points, or a single line with only two vertices.
   */
  #getFlipFeaturesActionCandidates(): st.Stream<geom.MapFeature> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    const entries = this.#selectedFeatures.entries();
    if (this.#selectedFeatures.size === 1) {
      const {value: [feature, _]} = entries.next();
      if (feature instanceof geom.Point || feature instanceof geom.LineString && feature.vertices.count() === 2) {
        return st.emptyStream();
      }
    } else if (this.#selectedFeatures.size === 2) {
      const {value: [feature1, _1]} = entries.next();
      const {value: [feature2, _2]} = entries.next();
      if (feature1 instanceof geom.Point && feature2 instanceof geom.Point) {
        return st.emptyStream();
      }
    }
    return st.stream(this.#selectedFeatures);
  }

  #flipLongSelectedFeatures(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  #flipShortSelectedFeatures(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return the lines that are currently eligible for the "reverse lines" action:
   * * all selected lines.
   */
  #getReverseLinesActionCandidates(): st.Stream<geom.LineString> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    return st.stream(this.#selectedFeatures)
        .filter(f => f instanceof geom.LinearFeature) as st.Stream<geom.LineString>;
  }

  /**
   * Reverse the direction of all selected lines.
   */
  #reverseSelectedLines(): void {
    this.#getReverseLinesActionCandidates().forEach(line => {
      line.direction = line.direction === geom.PolylineDirection.FORWARD
          ? geom.PolylineDirection.BACKWARD
          : geom.PolylineDirection.FORWARD;
      this.#updateFeatureData(line);
    });
  }

  /**
   * Return the features that are currently eligible for the "rotate features" action:
   * * all selected features if there are more than one.
   * * the single selected feature if it is not a point.
   */
  #getRotateFeaturesActionCandidates(): st.Stream<geom.MapFeature> {
    if (this.#editMode !== EditMode.SELECT
        || (this.#selectedFeatures.size === 1
            && this.#selectedFeatures.values().next().value instanceof geom.Point)) {
      return st.emptyStream();
    }
    return st.stream(this.#selectedFeatures);
  }

  #rotateSelectedFeatures(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Return the lines that are currently eligible for the "straighten lines" action:
   * * all selected lines that are nearly straight.
   */
  #getStraightenLinesActionCandidates(): st.Stream<geom.LineString> {
    if (this.#editMode !== EditMode.SELECT) {
      return st.emptyStream();
    }
    return st.stream(this.#selectedFeatures)
        .filter(f =>
            f instanceof geom.LineString && f.isNearlyStraight()) as st.Stream<geom.LineString>;
  }

  #straightenSelectedLines(): void {
    // TODO
    console.log("Not implemented yet.");
  }

  /**
   * Update the given feature’s map data.
   * @param feature A feature.
   */
  #updateFeatureData(feature: geom.MapFeature): void {
    (this.#map.getSource(feature.id) as mgl.GeoJSONSource).setData(feature);
  }
}

/**
 * Hook a feature editor to the given map.
 * @param map The map.
 */
export default function initMapEditor(map: Map): void {
  // TEMP
  const lengthUnitType = new dtypes.UnitType("length", "Length");
  const millimeterUnit = new dtypes.Unit(lengthUnitType, "mm");
  lengthUnitType.addUnit(millimeterUnit);
  const track_level_enum = new dtypes.Enum("track_level", "Track Level", {
    on_ground: "On Ground",
    tunnel: "Underground",
    bridge: "Bridge",
  });
  const track_section = new dtypes.ObjectType("track_section", "Track Section", null, "LineString");
  track_section.addProperty(new dtypes.EnumProperty(track_section, "level", "Level", true, false, track_level_enum));
  const conv_track_section = new dtypes.ObjectType("conventional_track_section", "Railway Track Section", track_section);
  conv_track_section.addProperty(new dtypes.FloatProperty(conv_track_section, "gauge", "Gauge", true, false, 0, null, lengthUnitType));

  const mapEditor = new MapEditor(map, {
    units: {
      length: lengthUnitType,
    },
    enums: {
      track_level: track_level_enum,
    },
    objects: {
      track_section: track_section,
      conventional_track_section: conv_track_section,
    },
  });

  // TEMP
  const typeProvider: geom.DataTypeProvider = (n, t) => mapEditor.getDataType(n, t);

  const track1 = new dtypes.ObjectInstance(conv_track_section);
  track1.setPropertyValue("level", "on_ground");
  track1.setPropertyValue("gauge", 1435);

  const point0 = new geom.Point(typeProvider, "point0", new mgl.LngLat(1.4500, 43.6005));
  const point1 = new geom.Point(typeProvider, "point1", new mgl.LngLat(1.4500, 43.6000));
  const point2 = new geom.Point(typeProvider, "point2", new mgl.LngLat(1.4505, 43.6000));
  const point3 = new geom.Point(typeProvider, "point3", new mgl.LngLat(1.4505, 43.6005));
  const point4 = new geom.Point(typeProvider, "point4", new mgl.LngLat(1.4506, 43.6010));
  const line1 = new geom.LineString(typeProvider, "line1", [point1, point2, point3, point4], 0, track1);
  const polygon1 = new geom.Polygon(typeProvider, "polygon1", [
    [
      point3,
      new geom.Point(typeProvider, "point02", new mgl.LngLat(1.4505, 43.6010)),
      new geom.Point(typeProvider, "point03", new mgl.LngLat(1.4510, 43.6015)),
      new geom.Point(typeProvider, "point04", new mgl.LngLat(1.4515, 43.6015)),
    ],
    [
      point4,
      new geom.Point(typeProvider, "point12", new mgl.LngLat(1.4508, 43.6010)),
      new geom.Point(typeProvider, "point13", new mgl.LngLat(1.4510, 43.6013)),
    ],
  ]);
  map.on("load", () => {
    mapEditor.addFeature(point0);
    mapEditor.addFeature(point1);
    mapEditor.addFeature(point2);
    mapEditor.addFeature(line1);
    mapEditor.addFeature(polygon1);
  });
}
