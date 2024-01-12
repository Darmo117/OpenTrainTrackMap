import {GeoJSONSource, LngLat, Map, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
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

  readonly #map: Map;
  readonly #features: Dict<MapFeature> = {};
  readonly #selectedFeatureIds: Set<string> = new Set();
  #draggedPoint: Point = null;
  #editMode: EditMode = EditMode.SELECT;
  #lastClickTime: number = 0;

  constructor(map: Map) {
    this.#map = map;
    this.#map.on("click", e => {
      if (!e.originalEvent.ctrlKey) {
        this.#map.fire("editor.selection.remove", [...this.#selectedFeatureIds]);
        this.#selectedFeatureIds.forEach(
            id => this.#setFeatureBorderColor(this.#features[id], MapEditor.HIGHLIGHT_BASE_COLOR));
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

    this.#map.on("controls.styles.tiles_changed", () => {
      if (this.#map.getLayersOrder().length) {
        // Put tiles layer beneath every other feature (i.e. the lowest one)
        this.#map.moveLayer("tiles", this.#map.getLayersOrder()[0]);
      }
    });
  }

  addFeature(feature: MapFeature) {
    // TODO handle z-order
    if (this.#features[feature.id]) {
      return;
    }

    this.#features[feature.id] = feature;
    if (feature.geometry.type === "LineString") {
      // Add all vertices of the linestring
      (feature as LineString).vertices.forEach(v => this.addFeature(v));
    } else if (feature.geometry.type === "Polygon") {
      // Add all vertices of the polygon
      (feature as Polygon).vertices.forEach(vs => vs.forEach(v => this.addFeature(v)));
    }
    this.#map.addSource(feature.id, {
      type: "geojson",
      data: feature,
    });
    this.#addLayerForFeature(feature);
    this.#makeFeatureSelectable(feature);
    this.#makeFeatureHighlightable(feature);
    if (feature.geometry.type === "Point") {
      this.#makePointDraggableWithoutSelection(feature as Point);
    } else if (feature.geometry.type === "LineString") {
      // Put all points above all current features
      (feature as LineString).vertices.forEach(v => this.#moveLayer(v.id));
    } else if (feature.geometry.type === "Polygon") {
      // Put all points above all current features
      (feature as Polygon).vertices.forEach(vs => vs.forEach(v => this.#moveLayer(v.id)));
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
    switch (feature.geometry.type) {
      case "Point":
        return [feature.id + "-highlight", feature.id];
      case "LineString":
        return [feature.id + "-highlight", feature.id + "-border", feature.id];
      case "Polygon":
        return [feature.id, feature.id + "-contour"];
    }
  }

  #addLayerForFeature(feature: MapFeature) {
    switch (feature.geometry.type) {
      case "Point":
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
        break;
      case "LineString":
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
        break;
      case "Polygon":
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
          id: feature.id + "-contour",
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
        break;
    }
  }

  removeFeature(featureId: string) {
    // TODO update bound features
    this.#map.removeLayer(featureId);
    this.#map.removeSource(featureId);
    delete this.#features[featureId];
    this.#selectedFeatureIds.delete(featureId);
  }

  #setFeatureBorderColor(feature: MapFeature, color: string) {
    switch (feature.geometry.type) {
      case "Point":
        this.#map.setPaintProperty(feature.id + "-highlight", "circle-color", color);
        break;
      case "LineString":
      case "Polygon":
        this.#map.setPaintProperty(feature.id + "-highlight", "line-color", color);
        break;
    }
  }

  #makeFeatureSelectable(feature: MapFeature) {
    this.#map.on("click", feature.id, () => {
      const ms = new Date().getTime();
      // If several features are on top of each other, an event is fired each one of them.
      // So we add a small cooldown so that only the first one is actually clicked.
      if (ms - this.#lastClickTime < 10) {
        return;
      }
      this.#lastClickTime = ms;

      console.log(feature); // DEBUG
      this.#setFeatureBorderColor(feature, MapEditor.HIGHLIGHT_SELECTED_COLOR);
      this.#selectedFeatureIds.add(feature.id);
      this.#map.fire("editor.selection.add", feature);
    });
  }

  #makeFeatureHighlightable(feature: MapFeature) {
    const canvas = this.#map.getCanvasContainer();
    this.#map.on("mouseenter", feature.id, () => {
      if (!this.#selectedFeatureIds.has(feature.id)) {
        this.#setFeatureBorderColor(feature, MapEditor.HIGHLIGHT_HOVERED_COLOR);
      }
      if (!this.#draggedPoint) { // Avoids flicker
        canvas.style.cursor = "pointer";
      }
    });
    this.#map.on("mouseleave", feature.id, () => {
      if (!this.#selectedFeatureIds.has(feature.id)) {
        this.#setFeatureBorderColor(feature, MapEditor.HIGHLIGHT_BASE_COLOR);
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
  const line1 = new LineString("line1", [point1, point2, point3]);
  line1.color = "#ffe46d";
  const polygon1 = new Polygon("polygon1", [
    [
      point3,
      new Point("point01", new LngLat(1, 2)),
      new Point("point02", new LngLat(2, 3)),
      new Point("point03", new LngLat(3, 3)),
    ],
    [
      new Point("point11", new LngLat(1.25, 2)),
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
