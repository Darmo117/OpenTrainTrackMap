import {LngLat} from "maplibre-gl";

/**
 * Return a copy of the given LngLat object.
 * @param lngLat The object to copy.
 */
export function copyLngLat(lngLat: LngLat): LngLat {
  return LngLat.convert(lngLat.toArray());
}
