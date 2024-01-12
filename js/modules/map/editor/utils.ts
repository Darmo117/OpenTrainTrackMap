import * as mgl from "maplibre-gl";

/**
 * Return a copy of the given LngLat object.
 * @param lngLat The object to copy.
 */
export function copyLngLat(lngLat: mgl.LngLat): mgl.LngLat {
  return mgl.LngLat.convert(lngLat.toArray());
}
