import {DrawCustomMode} from "@mapbox/mapbox-gl-draw";

export interface DrawCustomModeWithContext<CustomModeState = any, CustomModeOptions = any>
  extends DrawCustomMode<CustomModeState, CustomModeOptions> {
  _ctx: any; // Expose internal property
}
