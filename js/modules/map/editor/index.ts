import {GeoJSONSource, LngLat, Map, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import $ from "jquery";
import Split from "split.js";

import {Dict} from "../../types";
import {LinearGeometry, MapFeature, Point, Polyline} from "./geometry";

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
  #draggedPoint: MapFeature<Point> = null;
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
      (feature.geometry as LinearGeometry).vertices.forEach(v => this.addFeature(v));
    }
    this.#map.addSource(feature.id, {
      type: "geojson",
      data: feature,
    });
    this.#addLayerForFeature(feature);
    this.#makeFeatureSelectable(feature);
    this.#makeFeatureHighlightable(feature);
    if (feature.geometry.type === "Point") {
      this.#makePointDraggableWithoutSelection(feature as MapFeature<Point>);
    }
  }

  #addLayerForFeature(feature: MapFeature) {
    switch (feature.geometry.type) {
      case "Point":
        this.#map.addLayer({
          id: feature.id,
          type: "circle",
          source: feature.id,
          paint: {
            "circle-radius": (feature.geometry as Point).radius,
            "circle-color": feature.geometry.color,
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
          },
          paint: {
            "line-width": (feature.geometry as Polyline).width,
            "line-color": feature.geometry.color,
            // TODO find how to display a border
            // "circle-stroke-width": 3,
            // "circle-stroke-color": MapEditor.BASE_COLOR,
          },
        });
        break;
      case "Polygon":
        // TODO
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

  #makePointDraggableWithoutSelection(feature: MapFeature<Point>) {
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
    (this.#map.getSource(feature.id) as GeoJSONSource).setData(feature);
  }

  #onMoveSelected(e: MapMouseEvent | MapTouchEvent) {
    this.#map.getCanvasContainer().style.cursor = "crosshair";
    this.#selectedFeatureIds.forEach(id => {
      const feature = this.#features[id];
      feature.onDrag(e);
      (this.#map.getSource(feature.id) as GeoJSONSource).setData(feature);
    });
  }

  #onUp() {
    this.#draggedPoint = null;
  }
}

export default function initMapEditor(map: Map) {
  // TODO
  const mapEditor = new MapEditor(map);

  // TEMP
  const point1 = new MapFeature("point1", new Point(new LngLat(0, 0)));
  const point2 = new MapFeature("point2", new Point(new LngLat(1, 0)));
  const line1 = new MapFeature("line1", new Polyline([point1, point2, new MapFeature("point3", new Point(new LngLat(1, 1)))]));
  line1.geometry.color = "red";
  map.on("load", () => {
    mapEditor.addFeature(point1);
    mapEditor.addFeature(point2);
    mapEditor.addFeature(line1);
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
