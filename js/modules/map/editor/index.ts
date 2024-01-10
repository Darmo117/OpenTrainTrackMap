import {CircleLayerSpecification, GeoJSONSource, LngLat, Map, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import $ from "jquery";
import Split from "split.js";

import {Dict} from "../../types";
import {MapFeature, Point} from "./geometry";

class MapEditor {
  static readonly BASE_COLOR: string = "#00000000";
  static readonly SELECTED_COLOR: string = "#3bb2d0d0";
  static readonly HOVERED_COLOR: string = "#fffd85d0";

  #map: Map;
  #features: Dict<MapFeature> = {};
  #selectedFeatures: Set<string> = new Set();
  #draggedPoint: MapFeature<Point> = null;
  // Needed to unbind properly in this.#onUp()
  #mousMoveCallback: (e: MapMouseEvent | MapTouchEvent) => void;
  #mouseUpCallback: (e: MapMouseEvent | MapTouchEvent) => void;

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
      canvas.style.cursor = "move";
    });
    this.#map.on("mouseleave", feature.id, () => {
      if (!this.#selectedFeatures.has(feature.id)) {
        this.#map.setPaintProperty(feature.id, "circle-stroke-color", MapEditor.BASE_COLOR);
      }
      canvas.style.cursor = "";
    });

    // Only points are draggable without being selected
    if (feature.geometry.type !== "Point") {
      return;
    }

    // Make feature draggable
    this.#mousMoveCallback = (e: MapMouseEvent) => this.#onMovePoint(e);
    this.#mouseUpCallback = (e: MapMouseEvent) => this.#onUp(e);
    this.#map.on("mousedown", feature.id, e => {
      // Prevent the default map drag behavior.
      e.preventDefault();
      canvas.style.cursor = "grab";
      this.#draggedPoint = feature as MapFeature<Point>;
      this.#map.on("mousemove", this.#mousMoveCallback);
      this.#map.once("mouseup", this.#mouseUpCallback);
    });
    this.#map.on("touchstart", feature.id, e => {
      if (e.points.length !== 1) {
        return;
      }
      // Prevent the default map drag behavior.
      e.preventDefault();
      this.#map.on("touchmove", this.#mousMoveCallback);
      this.#map.once("touchend", this.#mouseUpCallback);
    });
  }

  #onMovePoint(e: MapMouseEvent | MapTouchEvent) {
    this.#map.getCanvasContainer().style.cursor = "grabbing";
    const feature = this.#draggedPoint;
    feature.onDrag(e);
    (this.#map.getSource(feature.id) as GeoJSONSource).setData(feature);
  }

  #onMoveSelected(e: MapMouseEvent | MapTouchEvent) {
    this.#map.getCanvasContainer().style.cursor = "grabbing";
    this.#selectedFeatures.forEach(id => {
      const feature = this.#features[id];
      feature.onDrag(e);
      (this.#map.getSource(feature.id) as GeoJSONSource).setData(feature);
    });
  }

  #onUp(e: MapMouseEvent | MapTouchEvent) {
    this.#draggedPoint = null;
    // Unbind mouse/touch events
    this.#map.off("mousemove", this.#mousMoveCallback);
    this.#map.off("touchmove", this.#mouseUpCallback);
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
