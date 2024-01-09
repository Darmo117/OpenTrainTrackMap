import {IControl, Map} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import Split from "split.js";
import $ from "jquery";

import {SnapDirectSelect, SnapLineMode, SnapModeDrawStyles, SnapPointMode, SnapPolygonMode} from "./snap";
import {SnapOptions} from "./snap/types";
import {fixMapboxDrawControls} from "./controls/mapboxgl-draw";
import {
  CreateFeaturesEvent,
  DeleteFeaturesEvent,
  FeatureUpdateEvent,
  SelectionChangedEvent,
  ModeChangedEvent
} from "./editor-types";

/**
 * Hook a map editor to the given map.
 * @param map The map object.
 */
export default function initMapEditor(map: Map) { // TODO disable editing if zoom level is too small
  type DrawOptions = MapboxDraw.MapboxDrawOptions & SnapOptions;

  let mapboxDraw;
  map.addControl((mapboxDraw = new MapboxDraw({
    modes: {
      ...MapboxDraw.modes,
      draw_point: SnapPointMode,
      draw_polygon: SnapPolygonMode,
      draw_line_string: SnapLineMode,
      direct_select: SnapDirectSelect,
      // TODO custom simple_select mode to enable point feature snapping
      //  cf. https://github.com/mapbox/mapbox-gl-draw/blob/main/docs/API.md#simple_select
    },
    keybindings: false, // Disable default key bindings
    displayControlsDefault: false,
    controls: {
      point: true,
      line_string: true,
      polygon: true,
    },
    styles: SnapModeDrawStyles,
    userProperties: true,
    snap: true,
    snapOptions: {
      snapPx: 5,
      snapVertexPriorityDistance: 0.005,
    },
  } as DrawOptions)) as unknown as IControl, "top-left");

  fixMapboxDrawControls(map, mapboxDraw);

  map.on("draw.create", (e: CreateFeaturesEvent) => {
    // console.log("draw.create", e.features);
    // TODO
  })
  // Not "draw.create" because it will never fire as we’re not using the default "trash" control
  map.on("editor.delete", (e: DeleteFeaturesEvent) => {
    // console.log("editor.delete", e.features);
    // TODO
  });
  map.on("draw.update", (e: FeatureUpdateEvent) => {
    // console.log("draw.update", e.features, e.action);
    // TODO
  })
  map.on("draw.selectionchange", (e: SelectionChangedEvent) => {
    // console.log("draw.selectionchange", e.features);
    // TODO
  })
  map.on("draw.modechange", (e: ModeChangedEvent) => {
    // console.log("draw.modechange", e.mode);
    // TODO
  })

  $("#editor-panel").css({display: "block"}).addClass("split");
  $("#map").addClass("split");
  Split(["#editor-panel", "#map"], {
    sizes: [20, 80],
    minSize: [0, 100],
    gutterSize: 5,
  });
}
