import {Map} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import {
  SnapLineMode,
  SnapPointMode,
  SnapPolygonMode,
  SnapDirectSelect,
  SnapModeDrawStyles,
} from "mapbox-gl-draw-snap-mode";
import Split from "split.js";

import $ from "jquery";

/**
 * Hook a map editor to the given map.
 * @param map The map object.
 */
export default function initMapEditor(map: Map) { // TODO disable editing if zoom level is too small
  // @ts-ignore
  map.addControl(new MapboxDraw({ // TODO translate
    modes: {
      ...MapboxDraw.modes,
      draw_point: SnapPointMode,
      draw_polygon: SnapPolygonMode,
      draw_line_string: SnapLineMode,
      direct_select: SnapDirectSelect,
    },
    displayControlsDefault: false,
    controls: {
      point: true,
      line_string: true,
      polygon: true,
      trash: true
    },
    styles: SnapModeDrawStyles,
    userProperties: true,
    // @ts-ignore
    snap: true,
    snapOptions: {
      snapPx: 15, // defaults to 15
      snapToMidPoints: false, // defaults to false
      snapVertexPriorityDistance: 0.0025, // defaults to 1.25
    },
    guides: false,
  }), "top-left");

  $("#editor-panel").css({display: "block"}).addClass("split");
  $("#map").addClass("split");
  Split(["#editor-panel", "#map"], {
    sizes: [20, 80],
    minSize: [0, 100],
    gutterSize: 5,
  });
}
