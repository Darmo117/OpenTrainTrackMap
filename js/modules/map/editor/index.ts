import {GeoJSONSource, LngLat, Map, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import $ from "jquery";
import Split from "split.js";

import {Dict} from "../../types";
import {LinearFeature, MapFeature, Point, Polygon, Polyline} from "./geometry";

enum EditMode {
  SELECT = "select",
  MOVE_FEATURES = "move_features",
  DRAW_POINT = "draw_point",
  DRAW_POLYLINE = "draw_polyline",
  DRAW_POLYGON = "draw_polygon",
}

class MapEditor {
  static readonly BASE_COLOR: string = "#00000000";
  static readonly SELECTED_COLOR: string = "#3bb2d0d0";
  static readonly HOVERED_COLOR: string = "#ff6d8bd0";

  readonly #map: Map;
  readonly #features: Dict<MapFeature> = {};
  readonly #selectedFeatureIds: Set<string> = new Set();
  #draggedPoint: Point = null;
  #editMode: EditMode = EditMode.SELECT;

  constructor(map: Map) {
    this.#map = map;
    this.#map.on("click", e => {
      if (!e.originalEvent.ctrlKey) {
        this.#map.fire("editor.selection.remove", [...this.#selectedFeatureIds]);
        this.#selectedFeatureIds.forEach(
            id => this.#setFeatureBorderColor(this.#features[id], MapEditor.BASE_COLOR));
        this.#selectedFeatureIds.clear();
      }
    });
    this.#map.on("mousemove", e => {
      if (this.#draggedPoint) {
        this.#onMovePoint(e);
      }
      if (this.#editMode === EditMode.MOVE_FEATURES && this.#selectedFeatureIds.size) {
        this.#onMoveSelected(e);
      }
    });
    this.#map.on("mouseup", () => this.#onUp());
  }

  addFeature(feature: MapFeature) {
    if (this.#features[feature.id]) {
      return;
    }

    this.#features[feature.id] = feature;
    if (feature.geometry.type !== "Point") {
      // Add all vertices of the polyline/polygon
      (feature as LinearFeature).vertices.forEach(v => this.addFeature(v));
    }
    this.#map.addSource(feature.id, {
      type: "geojson",
      data: feature,
    });
    if (feature.geometry.type === "Polygon") {
      // TODO add line to represent polygon’s border
    }
    this.#addLayerForFeature(feature);
    this.#makeFeatureSelectable(feature);
    this.#makeFeatureHighlightable(feature);
    if (feature.geometry.type === "Point") {
      this.#makePointDraggableWithoutSelection(feature as Point);
    }
  }

  #addLayerForFeature(feature: MapFeature) {
    switch (feature.geometry.type) {
      case "Point":
        this.#map.addLayer({
          id: feature.id,
          type: "circle",
          source: feature.id,
          layout: {
            "circle-sort-key": ["get", "priority"],
          },
          paint: {
            "circle-radius": ["get", "radius"],
            "circle-color": ["get", "color"],
            "circle-stroke-width": 3,
            "circle-stroke-color": MapEditor.BASE_COLOR,
          },
        });
        break;
      case "LineString":
        this.#map.addLayer({
          id: feature.id,
          type: "line",
          source: feature.id,
          layout: {
            "line-cap": "round",
            "line-join": "round",
            "line-sort-key": ["get", "priority"],
          },
          paint: {
            "line-width": ["get", "width"],
            "line-color": ["get", "color"],
            // TODO find how to display a border
          },
        });
        break;
      case "Polygon":
        this.#map.addLayer({
          id: feature.id,
          type: "fill",
          source: feature.id,
          layout: {
            "fill-sort-key": ["get", "priority"],
          },
          paint: {
            "fill-color": ["get", "bgColor"],
            // TODO find how to display a border
          },
        });
        break;
    }
  }

  removeFeature(featureId: string) {
    // TODO update bound features
    this.#map.removeLayer(featureId);
    this.#map.removeSource(featureId);
    delete this.#features[featureId];
  }

  #setFeatureBorderColor(feature: MapFeature, color: string) {
    switch (feature.geometry.type) {
      case "Point":
        this.#map.setPaintProperty(feature.id, "circle-stroke-color", color);
        break;
      case "LineString":
        // TODO
        break;
      case "Polygon":
        // TODO
        break;
    }
  }

  #makeFeatureSelectable(feature: MapFeature) {
    this.#map.on("click", feature.id, () => {
      this.#setFeatureBorderColor(feature, MapEditor.SELECTED_COLOR);
      this.#selectedFeatureIds.add(feature.id);
      this.#map.fire("editor.selection.add", feature);
    });
  }

  #makeFeatureHighlightable(feature: MapFeature) {
    const canvas = this.#map.getCanvasContainer();
    this.#map.on("mouseenter", feature.id, () => {
      if (!this.#selectedFeatureIds.has(feature.id)) {
        this.#setFeatureBorderColor(feature, MapEditor.HOVERED_COLOR);
      }
      if (!this.#draggedPoint) { // Avoids flicker
        canvas.style.cursor = "pointer";
      }
    });
    this.#map.on("mouseleave", feature.id, () => {
      if (!this.#selectedFeatureIds.has(feature.id)) {
        this.#setFeatureBorderColor(feature, MapEditor.BASE_COLOR);
      }
      if (!this.#draggedPoint) { // Avoids flicker
        canvas.style.cursor = "";
      }
    });
  }

  #makePointDraggableWithoutSelection(feature: Point) {
    this.#map.on("mousedown", feature.id, e => {
      // Prevent the default map drag behavior.
      e.preventDefault();
      this.#draggedPoint = feature;
    });
    this.#map.on("touchstart", feature.id, e => {
      if (e.points.length !== 1) {
        return;
      }
      // Prevent the default map drag behavior.
      e.preventDefault();
      this.#draggedPoint = feature;
    });
  }

  #onMovePoint(e: MapMouseEvent | MapTouchEvent) {
    this.#map.getCanvasContainer().style.cursor = "crosshair";
    const feature = this.#draggedPoint;
    feature.onDrag(e);
    this.#updateFeatureData(feature);
    feature.boundFeatures.forEach(
        f => this.#updateFeatureData(f))
  }

  #onMoveSelected(e: MapMouseEvent | MapTouchEvent) {
    this.#map.getCanvasContainer().style.cursor = "crosshair";
    this.#selectedFeatureIds.forEach(id => {
      const feature = this.#features[id];
      feature.onDrag(e);
      this.#updateFeatureData(feature);
    });
  }

  #onUp() {
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
  const line1 = new Polyline("line1", [point1, point2, point3]);
  line1.color = "red";
  const polygon1 = new Polygon("polygon1", [point3, new Point("point4", new LngLat(1, 2)), new Point("point5", new LngLat(2, 3)), new Point("point6", new LngLat(3, 3))])
  polygon1.color = "blue";
  polygon1.bgColor = "#000066a0";
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
