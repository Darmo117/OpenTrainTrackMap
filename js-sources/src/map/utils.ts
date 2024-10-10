import { LngLat } from "maplibre-gl";

/**
 * Return a copy of the given LngLat object.
 * @param lngLat The object to copy.
 */
export function copyLngLat(lngLat: LngLat): LngLat {
  return LngLat.convert(lngLat.toArray());
}

/**
 * Check if the given mouse event was triggered by the mouse’s secondary button (usually the right button).
 * @param e The event to check.
 */
export function isSecondaryClick(e: MouseEvent): boolean {
  return e.button === 2;
}
