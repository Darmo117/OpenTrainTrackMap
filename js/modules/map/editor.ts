import {IControl, Map} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import Split from "split.js";
import $ from "jquery";

import {SnapDirectSelect, SnapLineMode, SnapModeDrawStyles, SnapPointMode, SnapPolygonMode} from "./snap";
import {SnapOptions} from "./snap/state";

/**
 * Hook a map editor to the given map.
 * @param map The map object.
 */
export default function initMapEditor(map: Map) { // TODO disable editing if zoom level is too small
  type DrawOptions = MapboxDraw.MapboxDrawOptions & SnapOptions;
  map.addControl(new MapboxDraw({ // TODO translate
    modes: {
      ...MapboxDraw.modes,
      draw_point: SnapPointMode,
      draw_polygon: SnapPolygonMode,
      draw_line_string: SnapLineMode,
      direct_select: SnapDirectSelect,
      // TODO custom simple_select mode to enable point feature snapping
      //  cf. https://github.com/mapbox/mapbox-gl-draw/blob/main/docs/API.md#simple_select
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
    snap: true,
    snapOptions: {
      snapPx: 5,
      snapVertexPriorityDistance: 0.00125,
    },
  } as DrawOptions) as unknown as IControl, "top-left");

  $("#editor-panel").css({display: "block"}).addClass("split");
  $("#map").addClass("split");
  Split(["#editor-panel", "#map"], {
    sizes: [20, 80],
    minSize: [0, 100],
    gutterSize: 5,
  });
}
