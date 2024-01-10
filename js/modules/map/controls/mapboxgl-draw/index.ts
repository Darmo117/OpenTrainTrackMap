import {Map} from "maplibre-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import $ from "jquery";
import {parseSVG} from "../helpers";

const DRAW_POINT_ICON = parseSVG(`
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
  <path d="m10 2c-3.3 0-6 2.7-6 6s6 9 6 9 6-5.7 6-9-2.7-6-6-6zm0 2c2.1 0 3.8 1.7 3.8 3.8 0 1.5-1.8 3.9-2.9 5.2h-1.7c-1.1-1.4-2.9-3.8-2.9-5.2-.1-2.1 1.6-3.8 3.7-3.8z"/>
</svg>
`);

const DRAW_POLYGON_ICON = parseSVG(`
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
  <path d="m15 12.3v-4.6c.6-.3 1-1 1-1.7 0-1.1-.9-2-2-2-.7 0-1.4.4-1.7 1h-4.6c-.3-.6-1-1-1.7-1-1.1 0-2 .9-2 2 0 .7.4 1.4 1 1.7v4.6c-.6.3-1 1-1 1.7 0 1.1.9 2 2 2 .7 0 1.4-.4 1.7-1h4.6c.3.6 1 1 1.7 1 1.1 0 2-.9 2-2 0-.7-.4-1.4-1-1.7zm-8-.3v-4l1-1h4l1 1v4l-1 1h-4z"/>
</svg>
`);

const DRAW_LINE_ICON = parseSVG(`
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
  <path d="m13.5 3.5c-1.4 0-2.5 1.1-2.5 2.5 0 .3 0 .6.2.9l-3.8 3.8c-.3-.1-.6-.2-.9-.2-1.4 0-2.5 1.1-2.5 2.5s1.1 2.5 2.5 2.5 2.5-1.1 2.5-2.5c0-.3 0-.6-.2-.9l3.8-3.8c.3.1.6.2.9.2 1.4 0 2.5-1.1 2.5-2.5s-1.1-2.5-2.5-2.5z"/>
</svg>
`);

const classes: { [key: string]: { icon: SVGElement, key: string } } = {
  "draw_point": {icon: DRAW_POINT_ICON, key: "1"},
  "draw_line": {icon: DRAW_LINE_ICON, key: "2"},
  "draw_polygon": {icon: DRAW_POLYGON_ICON, key: "3"},
};

export function fixMapboxDrawControls(map: Map, mapboxDraw: MapboxDraw) {
  for (const [id, {icon, key}] of Object.entries(classes)) {
    const button = $(`.mapbox-gl-${id}`)[0];
    if (button) {
      button.title = window.ottm.translate(`map.controls.edit.${id}.tooltip`) + ` [${key}]`;
      button.appendChild(icon);
      // Add custom shortcut
      map.getCanvas().addEventListener("keydown", e => {
        if (e.key === key) {
          button.click();
        }
      });
    }
  }
  // TODO invoke MapboxDraw.trash() instead
  // Add custom shortcut to delete selected features
  map.getCanvas().addEventListener("keydown", e => {
    if (e.key === "Delete") {
      map.fire("editor.delete", {features: mapboxDraw.getSelected().features});
      mapboxDraw.getSelectedIds().forEach(id => mapboxDraw.delete(id));
    }
  });
}
