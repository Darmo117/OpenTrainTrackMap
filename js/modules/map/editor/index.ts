import {CircleLayerSpecification, GeoJSONSource, LngLat, Map, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import $ from "jquery";
import Split from "split.js";

import {Dict} from "../../types";
import {MapFeature, Point} from "./geometry";

enum EditMode {
  SELECT = "select",
  MOVE_FEATURES = "move_features",
}

class MapEditor {
  static readonly BASE_COLOR: string = "#00000000";
  static readonly SELECTED_COLOR: string = "#3bb2d0d0";
  static readonly HOVERED_COLOR: string = "#ff6d8bd0";

  readonly #map: Map;
  readonly #features: Dict<MapFeature> = {};
  readonly #selectedFeatures: Set<string> = new Set();
  #draggedPoint: MapFeature<Point> = null;
  #editMode: EditMode = EditMode.SELECT;

  constructor(map: Map) {
    this.#map = map;
    this.#map.on("click", e => {
      if (!e.originalEvent.ctrlKey) {
        this.#map.fire("editor.selection.remove", [...this.#selectedFeatures]);
        this.#selectedFeatures.forEach(
          id => this.#map.setPaintProperty(id, "circle-stroke-color", MapEditor.BASE_COLOR));
        this.#selectedFeatures.clear();
      }
    });
    this.#map.on("mousemove", e => {
      if (this.#draggedPoint) {
        this.#onMovePoint(e);
      }
      if (this.#editMode === EditMode.MOVE_FEATURES && this.#selectedFeatures.size) {
        this.#onMoveSelected(e);
      }
    });
    this.#map.on("mouseup", e => this.#onUp(e));
  }

  addFeature(feature: MapFeature) {
    if (this.#features[feature.id]) {
      return;
    }
    // Add feature
    this.#features[feature.id] = feature;
    this.#map.addSource(feature.id, {
      type: "geojson",
      data: feature,
    });
    this.#map.addLayer({
      id: feature.id,
      type: "circle",
      source: feature.id,
      paint: {
        "circle-radius": 5,
        "circle-color": "white",
        "circle-stroke-width": 3,
        "circle-stroke-color": MapEditor.BASE_COLOR,
      },
    } as CircleLayerSpecification);

    // Make feature selectable
    this.#map.on("click", feature.id, e => {
      this.#map.setPaintProperty(feature.id, "circle-stroke-color", MapEditor.SELECTED_COLOR);
      this.#selectedFeatures.add(feature.id);
      this.#map.fire("editor.selection.add", feature);
    });

    // Highlight hovered features
    const canvas = this.#map.getCanvasContainer();
    this.#map.on("mouseenter", feature.id, () => {
      if (!this.#selectedFeatures.has(feature.id)) {
        this.#map.setPaintProperty(feature.id, "circle-stroke-color", MapEditor.HOVERED_COLOR);
      }
      if (!this.#draggedPoint) { // Avoids flicker
        canvas.style.cursor = "pointer";
      }
    });
    this.#map.on("mouseleave", feature.id, e => {
      if (!this.#selectedFeatures.has(feature.id)) {
        this.#map.setPaintProperty(feature.id, "circle-stroke-color", MapEditor.BASE_COLOR);
      }
      if (!this.#draggedPoint) { // Avoids flicker
        canvas.style.cursor = "";
      }
    });

    // Only points are draggable without being selected
    if (feature.geometry.type !== "Point") {
      return;
    }

    // Make feature draggable
    this.#map.on("mousedown", feature.id, e => {
      // Prevent the default map drag behavior.
      e.preventDefault();
      this.#draggedPoint = feature as MapFeature<Point>;
    });
    this.#map.on("touchstart", feature.id, e => {
      if (e.points.length !== 1) {
        return;
      }
      // Prevent the default map drag behavior.
      e.preventDefault();
      this.#draggedPoint = feature as MapFeature<Point>;
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
    this.#selectedFeatures.forEach(id => {
      const feature = this.#features[id];
      feature.onDrag(e);
      (this.#map.getSource(feature.id) as GeoJSONSource).setData(feature);
    });
  }

  #onUp(e: MapMouseEvent | MapTouchEvent) {
    this.#draggedPoint = null;
  }
}

export default function initMapEditor(map: Map) {
  // TODO
  const mapEditor = new MapEditor(map);

  // TEMP
  const feature1 = new MapFeature("point1", new Point(new LngLat(0, 0)));
  const feature2 = new MapFeature("point2", new Point(new LngLat(1, 0)));
  map.on("load", () => {
    mapEditor.addFeature(feature1);
    mapEditor.addFeature(feature2);
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
