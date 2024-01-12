import {GeoJSONSource, LngLat, Map, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import MLPoint from "mapbox__point-geometry";
import $ from "jquery";
import Split from "split.js";

import {Dict} from "../../types";
import {LineString, MapFeature, Point, Polygon} from "./geometry";

enum EditMode {
  SELECT = "select",
  MOVE_FEATURES = "move_features",
  DRAW_POINT = "draw_point",
  DRAW_POLYLINE = "draw_polyline",
  DRAW_POLYGON = "draw_polygon",
}

class MapEditor {
  static readonly HIGHLIGHT_BASE_COLOR: string = "#00000000";
  static readonly HIGHLIGHT_SELECTED_COLOR: string = "#3bb2d0d0";
  static readonly HIGHLIGHT_HOVERED_COLOR: string = "#ff6d8bd0";

  static readonly BORDER_COLOR: string = "#101010";

  static readonly CURSORS = [
    "cursor-point",
    "cursor-linestring",
    "cursor-polygon",
    "cursor-draw",
    "cursor-grab",
    "cursor-grabbing",
  ] as const;

  readonly #map: Map;
  readonly #$canvas: JQuery;
  readonly #features: Dict<MapFeature> = {};
  readonly #selectedFeatures: Set<MapFeature> = new Set();
  #hoveredFeature: MapFeature;
  #draggedPoint: Point = null;
  #editMode: EditMode = EditMode.SELECT;

  constructor(map: Map) {
    this.#map = map;
    this.#$canvas = $(this.#map.getCanvasContainer());

    this.#map.on("click", e => this.#onMouseClick(e));
    this.#map.on("mousemove", e => this.#onMouseMouve(e));
    this.#map.on("mousedown", e => this.#onMouseDown(e));
    this.#map.on("touchstart", e => {
      if (e.points.length !== 1) {
        return;
      }
      this.#onMouseDown(e);
    });
    this.#map.on("mouseup", () => this.#onMouseUp());
    this.#map.on("touchend", e => {
      if (e.points.length !== 1) {
        return;
      }
      this.#onMouseUp();
    });
    this.#map.on("controls.styles.tiles_changed", () => {
      if (this.#map.getLayersOrder().length) {
        // Put tiles layer beneath every other feature (i.e. the lowest one)
        this.#map.moveLayer("tiles", this.#map.getLayersOrder()[0]);
      }
    });
  }

  /**
   * Return the feature currently under the mouse according to the following conditions:
   * * If there are any points, the highest one is returned.
   * * If there are no points, the lowest feature is returned.
   * * If there are no features, null is returned.
   * @param mousePos Mouse position.
   * @returns The feature or null if none are at the given mouses position.
   */
  #getFeatureUnderMouse(mousePos: MLPoint): MapFeature | null {
    const featureIds = new Set(this.#map.queryRenderedFeatures(mousePos)
        .map(f => f.source));
    const layersOrder = this.#map.getLayersOrder();
    let selectedIndex = Infinity;
    let selectedFeature: MapFeature = null;
    for (const featureId of featureIds) {
      const currentIndex = layersOrder.indexOf(featureId);
      if (currentIndex === -1) {
        continue;
      }
      const feature = this.#features[featureId];
      const currentIsPoint = feature instanceof Point;
      const selectedIsNotPoint = !(selectedFeature instanceof Point);
      if (!selectedFeature
          || currentIsPoint && (selectedIsNotPoint || currentIndex > selectedIndex)
          || !currentIsPoint && selectedIsNotPoint && currentIndex < selectedIndex) {
        selectedIndex = currentIndex;
        selectedFeature = feature;
      }
    }
    return selectedFeature;
  }

  addFeature(feature: MapFeature) {
    // TODO handle z-order
    if (this.#features[feature.id]) {
      return;
    }

    this.#features[feature.id] = feature;
    // Add all vertices
    if (feature instanceof LineString) {
      feature.vertices.forEach(v => this.addFeature(v));
    } else if (feature instanceof Polygon) {
      feature.vertices.forEach(vs => vs.forEach(v => this.addFeature(v)));
    }
    this.#map.addSource(feature.id, {
      type: "geojson",
      data: feature,
    });
    this.#addLayersForFeature(feature);
    // Put all points above all current features
    if (feature instanceof LineString) {
      feature.vertices.forEach(v => this.#moveLayer(v.id));
    } else if (feature instanceof Polygon) {
      feature.vertices.forEach(vs => vs.forEach(v => this.#moveLayer(v.id)));
    }
  }

  #moveLayer(featureId: string, beforeId?: string) {
    if (beforeId) {
      const bottomLayer = this.#getLayerIdStack(beforeId)[0];
      this.#getLayerIdStack(featureId).forEach(id => this.#map.moveLayer(id, bottomLayer));
    } else {
      this.#getLayerIdStack(featureId).forEach(id => this.#map.moveLayer(id));
    }
  }

  #getLayerIdStack(featureId: string): string[] {
    const feature = this.#features[featureId];
    if (feature instanceof Point) {
      return [feature.id + "-highlight", feature.id];
    } else if (feature instanceof LineString) {
      return [feature.id + "-highlight", feature.id + "-border", feature.id];
    } else if (feature instanceof Polygon) {
      return [feature.id, feature.id + "-highlight", feature.id + "-border"];
    } else {
      throw TypeError(`Unexpected type: ${feature}`);
    }
  }

  #addLayersForFeature(feature: MapFeature) {
    if (feature instanceof Point) {
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
    } else if (feature instanceof LineString) {
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
    } else if (feature instanceof Polygon) {
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

  removeFeature(featureId: string) {
    // TODO update bound features
    this.#map.removeLayer(featureId);
    this.#map.removeSource(featureId);
    this.#selectedFeatures.delete(this.#features[featureId]);
    delete this.#features[featureId];
    if (this.#hoveredFeature?.id === featureId) {
      this.#hoveredFeature = null;
    }
  }

  #setFeatureBorderColor(feature: MapFeature, color: string) {
    if (feature instanceof Point) {
      this.#map.setPaintProperty(feature.id + "-highlight", "circle-color", color);
    } else {
      this.#map.setPaintProperty(feature.id + "-highlight", "line-color", color);
    }
  }

  #setCanvasCursor(id: typeof MapEditor.CURSORS[number]) {
    this.#$canvas.addClass(id);
    this.#$canvas.removeClass(MapEditor.CURSORS.filter(s => s !== id));
  }

  #onMouseMouve(e: MapMouseEvent) {
    const hoveredFeature: MapFeature = this.#getFeatureUnderMouse(e.point);
    if (hoveredFeature) {
      if (this.#hoveredFeature && this.#hoveredFeature !== hoveredFeature && !this.#selectedFeatures.has(this.#hoveredFeature)) {
        this.#setFeatureBorderColor(this.#hoveredFeature, MapEditor.HIGHLIGHT_BASE_COLOR);
      }
      this.#hoveredFeature = hoveredFeature;
      if (!this.#draggedPoint && !this.#selectedFeatures.has(this.#hoveredFeature)) {
        this.#setFeatureBorderColor(hoveredFeature, MapEditor.HIGHLIGHT_HOVERED_COLOR);
      }
      this.#map.fire("editor.feature.hovered", {feature: this.#hoveredFeature});
    } else {
      if (this.#hoveredFeature && !this.#selectedFeatures.has(this.#hoveredFeature)) {
        this.#setFeatureBorderColor(this.#hoveredFeature, MapEditor.HIGHLIGHT_BASE_COLOR);
      }
      this.#hoveredFeature = null;
      this.#map.fire("editor.feature.hovered", {feature: null});
    }

    if (!this.#draggedPoint) {
      if (this.#hoveredFeature) {
        this.#setCanvasCursor(("cursor-" + this.#hoveredFeature.geometry.type.toLowerCase()) as any);
      } else {
        this.#setCanvasCursor("cursor-grab");
      }
      if (this.#editMode === EditMode.MOVE_FEATURES && this.#selectedFeatures.size) {
        this.#onMoveSelected(e);
      }
    } else {
      this.#onMovePoint(e);
    }
  }

  #onMovePoint(e: MapMouseEvent | MapTouchEvent) {
    this.#setCanvasCursor("cursor-draw");
    this.#draggedPoint.onDrag(e);
    this.#updateFeatureData(this.#draggedPoint);
    this.#draggedPoint.boundFeatures.forEach(f => this.#updateFeatureData(f));
  }

  #onMoveSelected(e: MapMouseEvent | MapTouchEvent) {
    this.#setCanvasCursor("cursor-grabbing");
    this.#selectedFeatures.forEach(feature => {
      feature.onDrag(e);
      this.#updateFeatureData(feature);
    });
  }

  #onMouseDown(e: MapMouseEvent | MapTouchEvent) {
    if (this.#hoveredFeature && this.#hoveredFeature instanceof Point) {
      e.preventDefault();
      this.#draggedPoint = this.#hoveredFeature;
    }
  }

  #onMouseClick(e: MapMouseEvent) {
    if (!e.originalEvent.ctrlKey) {
      this.#selectedFeatures.forEach(
          feature => this.#setFeatureBorderColor(feature, MapEditor.HIGHLIGHT_BASE_COLOR));
      this.#selectedFeatures.clear();
    }
    if (this.#hoveredFeature) {
      this.#selectedFeatures.add(this.#hoveredFeature);
      this.#setFeatureBorderColor(this.#hoveredFeature, MapEditor.HIGHLIGHT_SELECTED_COLOR);
    }
    this.#map.fire("editor.selection.update", {features: [...this.#selectedFeatures]});
  }

  #onMouseUp() {
    this.#draggedPoint = null;
  }

  #updateFeatureData(feature: MapFeature) {
    (this.#map.getSource(feature.id) as GeoJSONSource).setData(feature);
  }
}

export default function initMapEditor(map: Map) {
  const mapEditor = new MapEditor(map);

  // TEMP
  const point1 = new Point("point1", new LngLat(0, 0));
  const point2 = new Point("point2", new LngLat(1, 0));
  const point3 = new Point("point3", new LngLat(1, 1));
  const point4 = new Point("point4", new LngLat(1.25, 2));
  const line1 = new LineString("line1", [point1, point2, point3, point4]);
  line1.color = "#ffe46d";
  const polygon1 = new Polygon("polygon1", [
    [
      point3,
      new Point("point02", new LngLat(1, 2)),
      new Point("point03", new LngLat(2, 3)),
      new Point("point04", new LngLat(3, 3)),
    ],
    [
      point4,
      new Point("point12", new LngLat(1.75, 2)),
      new Point("point13", new LngLat(1.75, 2.25)),
    ],
  ]);
  polygon1.color = "#00FFA6";
  map.on("load", () => {
    mapEditor.addFeature(point1);
    mapEditor.addFeature(point2);
    mapEditor.addFeature(line1);
    mapEditor.addFeature(polygon1);
  });

  // Setup side panel
  $("#editor-panel").css({display: "block"}).addClass("split");
  $("#map").addClass("split");
  Split(["#editor-panel", "#map"], {
    sizes: [20, 80],
    minSize: [0, 100],
    gutterSize: 5,
  });
}
