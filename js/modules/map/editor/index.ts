import * as mgl from "maplibre-gl";
import $ from "jquery";
import Split from "split.js";

import * as types from "../../types";
import * as events from "./events";
import * as geom from "./geometry";
import {Point} from "./geometry";
import * as snap from "./snap";
import DrawControl from "./controls";

enum EditMode {
  SELECT = "select",
  DRAW_POINT = "draw_point",
  DRAW_LINE = "draw_line",
  DRAW_POLYGON = "draw_polygon",
  MOVE_FEATURES = "move_features",
}

class EditorPanel {
  readonly #$sidePanel: JQuery;
  readonly #$featureType: JQuery;
  readonly #selectedFeatures: Set<geom.MapFeature> = new Set();

  constructor(map: mgl.Map) {
    this.#$sidePanel = $("#editor-panel").show().addClass("split");
    this.#$sidePanel.append(this.#$featureType = $('<h1 id="feature-type"></h1>'));
    map.on(events.FeatureSelectionEvent.TYPE, (e: events.FeatureSelectionEvent) => {
      this.#selectedFeatures.clear();
      e.features.forEach(f => this.#selectedFeatures.add(f));
      this.#setupForm(e.features, true);
    });
    map.on(events.FeatureHoverEvent.TYPE, (e: events.FeatureHoverEvent) => {
      if (!this.#selectedFeatures.size) {
        this.#setupForm(e.feature ? [e.feature] : [], false);
      }
    });
  }

  #setupForm(features: geom.MapFeature[], editable: boolean) {
    if (!features.length) {
      this.#$featureType.text("");
    } else {
      this.#$featureType.text(features.map(f => f.id).join(", ")); // TEMP
      // TODO setup edit form
    }
  }

  getContainer(): HTMLElement {
    return this.#$sidePanel[0];
  }
}

class MapEditor {
  static readonly HIGHLIGHT_BASE_COLOR: string = "#00000000";
  static readonly HIGHLIGHT_SELECTED_COLOR: string = "#3bb2d0d0";
  static readonly HIGHLIGHT_HOVERED_COLOR: string = "#ff6d8bd0";

  static readonly BORDER_COLOR: string = "#101010";

  /**
   * List of available map cursors.
   */
  static readonly CURSORS = [
    "point",
    "linestring",
    "polygon",
    "draw",
    "grab",
    "grabbing",
  ] as const;

  readonly #map: mgl.Map;
  readonly #$canvas: JQuery;
  readonly #sidePanel: EditorPanel;
  readonly #drawPointControl: DrawControl;
  readonly #features: types.Dict<geom.MapFeature> = {};
  readonly #selectedFeatures: Set<geom.MapFeature> = new Set();
  #hoveredFeature: geom.MapFeature = null;
  #draggedPoint: geom.Point = null;
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
  #editMode: EditMode = EditMode.SELECT;

  /**
   * Create a new editor for the given map.
   * @param map A map.
   */
  constructor(map: mgl.Map) {
    this.#map = map;
    this.#$canvas = $(this.#map.getCanvasContainer());
    this.#sidePanel = new EditorPanel(this.#map);
    this.#drawPointControl = new DrawControl({
      onDrawPoint: () => this.#enableDrawPointMode(),
      onDrawLine: () => this.#enableDrawLineMode(),
      onDrawPolygon: () => this.#enableDrawPolygonMode(),
      drawPointButtonTitle: window.ottm.translate(`map.controls.edit.draw_point.tooltip`),
      drawLineButtonTitle: window.ottm.translate(`map.controls.edit.draw_line.tooltip`),
      drawPolygonButtonTitle: window.ottm.translate(`map.controls.edit.draw_polygon.tooltip`),
    });
    this.#map.addControl(this.#drawPointControl, "top-left");

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
    $("body").on("keydown", e => this.#onKeyDown(e.originalEvent));

    // Setup splitter
    const parent = this.#$canvas.parent();
    parent.addClass("split");
    Split([this.#sidePanel.getContainer(), parent[0]], {
      sizes: [20, 80],
      minSize: [0, 100],
      gutterSize: 5,
    });
  }

  /**
   * Add the given feature to the map.
   * @param feature The feature to add.
   */
  addFeature(feature: geom.MapFeature) {
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
      feature.vertices.forEach(vs => vs.forEach(v => this.addFeature(v)));
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
      feature.vertices.forEach(vs => vs.forEach(v => this.#moveLayers(v.id)));
    }
  }

  /**
   * Delete the feature with the given ID.
   * Bound features are updated.
   * @param featureId The ID of the feature to delete.
   */
  removeFeature(featureId: string) {
    const feature = this.#features[featureId];
    if (!feature) {
      return;
    }
    // Remove now to avoid potential infinite recursions
    delete this.#features[featureId];

    if (feature instanceof geom.Point) {
      // Remove bound features
      for (const boundFeature of feature.boundFeatures) {
        feature.unbindFeature(boundFeature);
        const actionResult = boundFeature.removeVertex(feature);
        if (actionResult.type === "delete_feature") {
          this.removeFeature(boundFeature.id);
        } else if (actionResult.type === "delete_ring") {
          // Delete vertices that were only bound to the feature
          actionResult.points.forEach(p => {
            if (p.boundFeatures.length === 1 && p.boundFeatures[0] === boundFeature) {
              this.removeFeature(p.id);
            } else {
              p.unbindFeature(boundFeature);
            }
          });
        }
      }
    } else if (feature instanceof geom.LineString) {
      // Delete vertices that were only bound to the feature
      for (const vertex of feature.vertices) {
        const boundFeatures = vertex.boundFeatures;
        vertex.unbindFeature(feature);
        if (boundFeatures.length === 1 && boundFeatures[0] === feature) {
          this.removeFeature(vertex.id);
        }
      }
    } else if (feature instanceof geom.Polygon) {
      // Delete vertices that were only bound to the feature
      for (const ring of feature.vertices) {
        for (const vertex of ring) {
          const boundFeatures = vertex.boundFeatures;
          vertex.unbindFeature(feature);
          if (boundFeatures.length === 1 && boundFeatures[0] === feature) {
            this.removeFeature(vertex.id);
          }
        }
      }
    }

    this.#map.removeLayer(featureId + "-highlight");
    if (feature instanceof geom.LinearFeature) {
      this.#map.removeLayer(featureId + "-border");
    }
    this.#map.removeLayer(featureId);
    this.#map.removeSource(featureId);
    this.#selectedFeatures.delete(feature);
    if (this.#hoveredFeature?.id === featureId) {
      this.#hoveredFeature = null;
    }
  }

  /**
   * Quit the current edit mode and go to "select" mode.
   * Any ongoing drawing is interrupted.
   * @param mousePos The current mouse position. Used to refresh the cursor.
   */
  #enableSelectMode(mousePos?: mgl.PointLike) {
    const editMode = this.#editMode;
    this.#editMode = EditMode.SELECT;
    switch (editMode) {
      case EditMode.SELECT:
        this.#refreshCursor(mousePos);
        break;
      case EditMode.DRAW_POINT:
        this.#quitDrawPointMode(mousePos);
        break;
      case EditMode.DRAW_LINE:
        this.#quitDrawLineMode(mousePos);
        break;
      case EditMode.DRAW_POLYGON:
        this.#quitDrawPolygonMode(mousePos);
        break;
      case EditMode.MOVE_FEATURES:
        break; // TODO
    }
  }

  #enableDrawPointMode() {
    this.#enableSelectMode();
    this.#editMode = EditMode.DRAW_POINT;
    this.#setCanvasCursor("draw");
  }

  #disableDrawPointMode(mousePos?: mgl.PointLike) {
    this.#editMode = EditMode.SELECT;
    this.#quitDrawPointMode(mousePos);
  }

  #quitDrawPointMode(mousePos?: mgl.PointLike) {
    this.#refreshCursor(mousePos);
    this.#drawPointControl.deactivateButton(0);
  }

  #enableDrawLineMode() {
    this.#enableSelectMode();
    this.#editMode = EditMode.DRAW_LINE;
    this.#setCanvasCursor("draw");
  }

  #disableDrawLineMode(mousePos?: mgl.PointLike) {
    this.#editMode = EditMode.SELECT;
    this.#quitDrawLineMode(mousePos);
  }

  #quitDrawLineMode(mousePos?: mgl.PointLike) {
    this.#refreshCursor(mousePos);
    this.#drawPointControl.deactivateButton(1);
  }

  #enableDrawPolygonMode() {
    this.#enableSelectMode();
    this.#editMode = EditMode.DRAW_POLYGON;
    this.#setCanvasCursor("draw");
  }

  #disableDrawPolygonMode(mousePos?: mgl.PointLike) {
    this.#editMode = EditMode.SELECT;
    this.#quitDrawPolygonMode(mousePos);
  }

  #quitDrawPolygonMode(mousePos?: mgl.PointLike) {
    this.#refreshCursor(mousePos);
    this.#drawPointControl.deactivateButton(2);
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
    for (const featureId of this.#getFeatureIds(mousePos)) {
      const currentIndex = layersOrder.indexOf(featureId);
      if (currentIndex === -1) {
        continue;
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
    }
    return selectedFeature;
  }

  /**
   * Return the list of feature IDs that are currently visible.
   * @param at If specified, only the IDs of features under the given pixel position will be returned.
   * @param exclude List of feature IDs to exclude from the results.
   * @returns The set of feature IDs that correspond to the criteria.
   */
  #getFeatureIds(at?: mgl.PointLike, exclude?: Set<string>): Set<string> {
    return new Set(this.#map.queryRenderedFeatures(at)
        .filter(f => !exclude?.has(f.source))
        .map(f => f.source));
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
  #moveLayers(featureId: string, beforeId?: string) {
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
      return [feature.id + "-highlight", feature.id + "-border", feature.id];
    } else if (feature instanceof geom.Polygon) {
      return [feature.id, feature.id + "-highlight", feature.id + "-border"];
    } else {
      return null;
    }
  }

  /**
   * Create the layers for the given feature and add them to the map.
   * @param feature A feature.
   */
  #addLayersForFeature(feature: geom.MapFeature) {
    if (feature instanceof geom.Point) {
      this.#map.addLayer({
        id: feature.id + "-highlight",
        type: "circle",
        source: feature.id,
        paint: {
          "circle-radius": ["+", ["get", "radius"], 4],
          "circle-color": MapEditor.HIGHLIGHT_BASE_COLOR,
        },
      });
      this.#map.addLayer({
        id: feature.id,
        type: "circle",
        source: feature.id,
        paint: {
          "circle-radius": ["get", "radius"],
          "circle-color": ["get", "color"],
          "circle-stroke-width": 1,
          "circle-stroke-color": MapEditor.BORDER_COLOR,
        },
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
          "line-color": MapEditor.HIGHLIGHT_BASE_COLOR,
        },
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
          "line-width": ["+", ["get", "width"], 2],
          "line-color": MapEditor.BORDER_COLOR,
        },
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
          "line-color": ["get", "color"],
        },
      });
    } else if (feature instanceof geom.Polygon) {
      this.#map.addLayer({
        id: feature.id,
        type: "fill",
        source: feature.id,
        paint: {
          "fill-color": ["concat", ["get", "color"], "30"], // Add transparency
        },
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
          "line-color": MapEditor.HIGHLIGHT_BASE_COLOR,
        },
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
      });
    } else {
      throw TypeError(`Unexpected type: ${feature}`);
    }
  }

  /**
   * Set the border color of the given feature.
   * @param feature A feature.
   * @param color The border’s color.
   */
  #setFeatureBorderColor(feature: geom.MapFeature, color: string) {
    if (feature instanceof geom.Point) {
      this.#map.setPaintProperty(feature.id + "-highlight", "circle-color", color);
    } else {
      this.#map.setPaintProperty(feature.id + "-highlight", "line-color", color);
    }
  }

  /**
   * Set the cursor for the map’s canvas.
   * @param cursor The cursor type. Must be one of {@link MapEditor.CURSORS}.
   */
  #setCanvasCursor(cursor: typeof MapEditor.CURSORS[number]) {
    this.#$canvas.addClass("cursor-" + cursor);
    this.#$canvas.removeClass(
        MapEditor.CURSORS
            .filter(s => s !== cursor)
            .map(s => "cursor-" + s)
    );
  }

  /**
   * Called when the mouse moves over the map.
   */
  #onMouseMouve(e: mgl.MapMouseEvent | mgl.MapTouchEvent) {
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
      if (this.#editMode === EditMode.MOVE_FEATURES && this.#selectedFeatures.size) {
        this.#onDragSelectedFeatures(e);
      }
    }
  }

  /**
   * Called when a {@link Point} is dragged.
   */
  #onDragPoint(e: mgl.MapMouseEvent | mgl.MapTouchEvent) {
    this.#clearSelection();
    this.#setCanvasCursor("draw");

    // Prevent linear features from connecting to themselves
    // -> exclude points bound to the bound features of the dragged point
    const excludedIds: Set<string> = new Set();
    this.#draggedPoint.boundFeatures.forEach(f => {
      excludedIds.add(f.id);
      // Exclude all the feature’s points
      if (f instanceof geom.LineString) {
        f.vertices.forEach(v => excludedIds.add(v.id));
      } else if (f instanceof geom.Polygon) {
        f.vertices.forEach(ring => {
          ring.forEach(v => excludedIds.add(v.id));
        });
      }
    });
    // Exclude point itself
    excludedIds.add(this.#draggedPoint.id);
    const features = Array.from(this.#getFeatureIds(null, excludedIds))
        .map(id => this.#features[id]);
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
        const canSnap = point.boundFeatures.every(
            f => f.canAcceptVertex(this.#draggedPoint));
        if (canSnap) {
          this.#snapResult = snapResult;
          // Move dragged point to the snap position
          this.#draggedPoint.onDrag(point.lngLat);
          this.#setHover(point);
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
        }
      }
    }

    if (!this.#snapResult) {
      this.#clearHover();
      this.#draggedPoint.onDrag(e.lngLat);
    }

    this.#updateFeatureData(this.#draggedPoint);
    this.#draggedPoint.boundFeatures.forEach(f => this.#updateFeatureData(f));
  }

  /**
   * Called when a {@link MapFeature} is dragged.
   */
  #onDragSelectedFeatures(e: mgl.MapMouseEvent | mgl.MapTouchEvent) {
    this.#setCanvasCursor("grabbing");
    this.#selectedFeatures.forEach(feature => {
      feature.onDrag(e.lngLat);
      this.#updateFeatureData(feature);
    });
  }

  /**
   * Called when the mouse is pressed down on the map.
   */
  #onMouseDown(e: mgl.MapMouseEvent | mgl.MapTouchEvent) {
    if (this.#editMode === EditMode.SELECT && this.#hoveredFeature instanceof geom.Point) {
      e.preventDefault();
      this.#draggedPoint = this.#hoveredFeature;
      this.#moveLayers(this.#draggedPoint.id); // Put on top
    }
  }

  /**
   * Called when the mouse is released on the map.
   */
  #onMouseUp(e: mgl.MapMouseEvent | mgl.MapTouchEvent) {
    if (this.#snapResult) {
      if (this.#snapResult.type === "point" || this.#snapResult.type === "segment_vertex") {
        let point: geom.Point;
        if (this.#snapResult.type === "point") {
          point = this.#snapResult.point;
        } else {
          const {feature, path} = this.#snapResult;
          point = feature.getVertex(path);
        }

        this.#draggedPoint.onDrag(point.lngLat);

        // TODO copy data from "point" to "this.#draggedPoint" if "this.#draggedPoint" is just a point with no data

        point.boundFeatures.forEach(
            f => f.replaceVertex(this.#draggedPoint, point));
        this.removeFeature(point.id);

      } else { // segment
        const {feature, path, lngLat} = this.#snapResult;
        this.#draggedPoint.onDrag(lngLat);
        feature.insertVertexAfter(this.#draggedPoint, path);
        // Insert vertex to all features that share the same segment
        this.#snapResult.featuresWithSameSegment?.forEach(
            ({feature, path}) => feature.insertVertexAfter(this.#draggedPoint, path));
      }
      this.#draggedPoint.boundFeatures.forEach(f => this.#updateFeatureData(f));
      this.#updateFeatureData(this.#draggedPoint);
      this.#moveLayers(this.#draggedPoint.id); // Put point on top
      this.#snapResult = null;
    }
    if (this.#draggedPoint) {
      this.#draggedPoint = null;
      this.#refreshCursor(e.point);
    }
  }

  /**
   * Called when the mouse is clicked on the map.
   */
  #onClick(e: mgl.MapMouseEvent) {
    if (this.#hoveredFeature) {
      switch (this.#editMode) {
        case EditMode.SELECT:
          const keepSelection = e.originalEvent.ctrlKey && this.#editMode === EditMode.SELECT;
          this.#selectFeature(this.#hoveredFeature, keepSelection);
          break;
        case EditMode.DRAW_POINT:
          this.#drawPointOnFeature(e);
          break;
        case EditMode.DRAW_LINE:
          this.#drawLineVertexOnFeature(e);
          break;
        case EditMode.DRAW_POLYGON:
          this.#drawPolygonVertexOnFeature(e);
          break;
        case EditMode.MOVE_FEATURES:
          break; // TODO
      }
    } else {
      switch (this.#editMode) {
        case EditMode.SELECT:
          this.#clearSelection();
          break;
        case EditMode.DRAW_POINT:
          this.#drawPoint(e);
          break;
        case EditMode.DRAW_LINE:
          this.#drawLineVertex(e);
          break;
        case EditMode.DRAW_POLYGON:
          this.#drawPolygonVertex(e);
          break;
        case EditMode.MOVE_FEATURES:
          break; // TODO
      }
    }
  }

  #drawPoint(e: mgl.MapMouseEvent) {
    this.#selectFeature(this.#createNewPoint(e.lngLat), false);
    this.#disableDrawPointMode(e.point);
  }

  #drawLineVertex(e: mgl.MapMouseEvent) {
    // TODO
  }

  #drawPolygonVertex(e: mgl.MapMouseEvent) {
    // TODO
  }

  #drawPointOnFeature(e: mgl.MapMouseEvent) {
    let feature: geom.MapFeature;
    if (this.#hoveredFeature instanceof Point) {
      // Select existing point instead of creating a new one
      feature = this.#hoveredFeature;
    } else if (!(feature = this.#createNewPointOnHoveredSegment(e))) {
      feature = this.#createNewPoint(e.lngLat);
    }
    this.#selectFeature(feature, false);
    this.#disableDrawPointMode(e.point);
  }

  #drawLineVertexOnFeature(e: mgl.MapMouseEvent) {
    // TODO
  }

  #drawPolygonVertexOnFeature(e: mgl.MapMouseEvent) {
    // TODO
  }

  /**
   * Called when the mouse is double-clicked on the map.
   */
  #onDoubleClick(e: mgl.MapMouseEvent) {
    if (this.#hoveredFeature) {
      // Prevent default action (zoom)
      e.preventDefault();
      this.#createNewPointOnHoveredSegment(e);
      this.#refreshCursor(e.point);
    }
  }

  /**
   * Called when a key is pressed.
   */
  #onKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape" && this.#editMode !== EditMode.SELECT) {
      // Interrupt any ongoing drawings
      this.#enableSelectMode();
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
      const features: geom.LinearFeature[] = [];
      for (const id of this.#getFeatureIds(e.point)) {
        const feature = this.#features[id];
        if (feature instanceof geom.LinearFeature) {
          features.push(feature);
        }
      }

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
  #setHover(feature: geom.MapFeature) {
    if (!feature) {
      throw new Error("Missing feature");
    }
    if (this.#hoveredFeature === feature) {
      return;
    }
    if (this.#hoveredFeature && !this.#selectedFeatures.has(this.#hoveredFeature)) {
      this.#setFeatureBorderColor(this.#hoveredFeature, MapEditor.HIGHLIGHT_BASE_COLOR);
    }
    this.#hoveredFeature = feature;
    if (!this.#selectedFeatures.has(this.#hoveredFeature)) {
      this.#setFeatureBorderColor(this.#hoveredFeature, MapEditor.HIGHLIGHT_HOVERED_COLOR);
    }
    this.#map.fire(new events.FeatureHoverEvent(this.#hoveredFeature));
  }

  /**
   * Clear the currently hovered feature.
   */
  #clearHover() {
    if (this.#hoveredFeature) {
      if (this.#hoveredFeature && !this.#selectedFeatures.has(this.#hoveredFeature)) {
        this.#setFeatureBorderColor(this.#hoveredFeature, MapEditor.HIGHLIGHT_BASE_COLOR);
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
  #selectFeature(feature: geom.MapFeature, keepSelection: boolean) {
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
      this.#setFeatureBorderColor(feature, MapEditor.HIGHLIGHT_SELECTED_COLOR);
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
  #clearSelection(fire: boolean = true) {
    if (this.#selectedFeatures.size) {
      this.#selectedFeatures.forEach(feature =>
          this.#setFeatureBorderColor(feature, MapEditor.HIGHLIGHT_BASE_COLOR));
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
  #refreshCursor(mousePos?: mgl.PointLike) {
    if (this.#editMode === EditMode.SELECT) {
      let feature: geom.MapFeature;
      if (mousePos) {
        feature = this.#getFeatureUnderMouse(mousePos);
      } else {
        feature = this.#hoveredFeature;
      }
      if (feature) {
        this.#setCanvasCursor(feature.geometry.type.toLowerCase() as any);
      } else {
        this.#setCanvasCursor("grab");
      }
    }
  }

  /**
   * Create a new point at the given position.
   * @param lngLat The point’s position.
   * @returns The newly created point.
   */
  #createNewPoint(lngLat: mgl.LngLat) {
    let id: string;
    do { // TODO keep global ID counter
      id = `point-${Math.random()}`;
    } while (this.#features[id]);
    const newPoint = new geom.Point(id, lngLat);
    this.addFeature(newPoint);
    return newPoint;
  }

  /**
   * Update the given feature’s map data.
   * @param feature A feature.
   */
  #updateFeatureData(feature: geom.MapFeature) {
    (this.#map.getSource(feature.id) as mgl.GeoJSONSource).setData(feature);
  }
}

/**
 * Hook a feature editor to the given map.
 * @param map The map.
 */
export default function initMapEditor(map: mgl.Map) {
  const mapEditor = new MapEditor(map);

  // TEMP
  const point0 = new geom.Point("point0", new mgl.LngLat(1.4500, 43.6005));
  const point1 = new geom.Point("point1", new mgl.LngLat(1.4500, 43.6000));
  const point2 = new geom.Point("point2", new mgl.LngLat(1.4505, 43.6000));
  const point3 = new geom.Point("point3", new mgl.LngLat(1.4505, 43.6005));
  const point4 = new geom.Point("point4", new mgl.LngLat(1.4506, 43.6010));
  const line1 = new geom.LineString("line1", [point1, point2, point3, point4]);
  line1.color = "#ffe46d";
  const polygon1 = new geom.Polygon("polygon1", [
    [
      point3,
      new geom.Point("point02", new mgl.LngLat(1.4505, 43.6010)),
      new geom.Point("point03", new mgl.LngLat(1.4510, 43.6015)),
      new geom.Point("point04", new mgl.LngLat(1.4515, 43.6015)),
    ],
    [
      point4,
      new geom.Point("point12", new mgl.LngLat(1.4508, 43.6010)),
      new geom.Point("point13", new mgl.LngLat(1.4510, 43.6013)),
    ],
  ]);
  polygon1.color = "#00FFA6";
  map.on("load", () => {
    mapEditor.addFeature(point0);
    mapEditor.addFeature(point1);
    mapEditor.addFeature(point2);
    mapEditor.addFeature(line1);
    mapEditor.addFeature(polygon1);
  });
}
