import {
  RasterSourceSpecificationWithId,
  TilesSource,
  TilesSourceCategory,
} from "./controls/tiles-sources";
import tileSourcesDefs from "./imagery_sources.json";

/**
 * This interface represents the bounds of a {@link TilesSourceDefinition}.
 */
export interface TilesSourceBounds {
  /**
   * The bounding box of these bounds.
   */
  bbox: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
  };
  /**
   * The list of shapes contained in these bounds.
   */
  shapes: Shape[];
}

/**
 * A shape is simply a list of points.
 */
export type Shape = Point[];

/**
 * A point represents a latitude and longitude coordinate.
 */
export interface Point {
  lat: number;
  lon: number;
}

/**
 * The available tile source categories as extracted from the JSON file.
 */
type JsonTilesSourceCategory =
  | "photo"
  | "elevation"
  | "map"
  | "historicmap"
  | "osmbasedmap"
  | "historicphoto"
  | "other";

/**
 * This interface represents a single date.
 */
export interface SingleDate {
  type: "date";
  date: string;
}

/**
 * Base interface for date intervals.
 */
export interface DateIntervalBase {
  type: "interval";
}

/**
 * A date interval with only a start date.
 */
export interface StartDateInterval extends DateIntervalBase {
  start: string;
}

/**
 * A date interval with only an end date.
 */
export interface EndDateInterval extends DateIntervalBase {
  end: string;
}

/**
 * A date interval with both a start and an end date.
 */
export type FullDateInterval = StartDateInterval & EndDateInterval;

/**
 * This type represents an interval between two dates (inclusive).
 * Either the start or end date may be absent, but not both at the same time.
 */
export type DateInterval =
  | StartDateInterval
  | EndDateInterval
  | FullDateInterval;

/**
 * This type represents the date of a tile source.
 * It is either a single date or an interval.
 */
export type TilesSourceDate = SingleDate | DateInterval;

/**
 * This interface defines the structure of a tile source definition as found in the generated JSON file.
 */
export interface TilesSourceDefinition {
  name: string;
  id: string;
  url: string;
  category: JsonTilesSourceCategory;
  eliBest?: boolean;
  description?: string;
  defaultForType?: boolean;
  minZoom?: number;
  maxZoom?: number;
  bounds?: TilesSourceBounds;
  privacyPolicyUrl?: string;
  permissionRef?: string;
  attributionText?: string;
  attributionUrl?: string;
  icon?: string;
  date?: TilesSourceDate;
  tileSize?: number;
}

export default function loadTilesSources(): TilesSource[] {
  const tilesSources: TilesSource[] = [];

  for (const sourceDef of tileSourcesDefs as TilesSourceDefinition[]) {
    const sourceSpec: RasterSourceSpecificationWithId = {
      id: sourceDef.id,
      type: "raster",
      tiles: [sourceDef.url],
      tileSize: sourceDef.tileSize ?? 256,
    };

    let attrib = "";
    if (sourceDef.icon)
      attrib = `<img style="max-height: 2em" alt="Logo" src="${sourceDef.icon}"> `;
    if (sourceDef.attributionText) {
      attrib += sourceDef.attributionText;
      if (sourceDef.attributionUrl)
        attrib = `<a href="${sourceDef.attributionUrl}" target="_blank">${attrib}</a>`;
    } else if (sourceDef.attributionUrl)
      attrib = `<a href="${sourceDef.attributionUrl}" target="_blank">${attrib}${sourceDef.attributionUrl}</a>`;
    if (attrib !== "") sourceSpec.attribution = attrib;

    if (sourceDef.minZoom) sourceSpec.minzoom = sourceDef.minZoom;
    if (sourceDef.maxZoom) sourceSpec.maxzoom = sourceDef.maxZoom;

    const source: TilesSource = {
      label: sourceDef.name,
      id: sourceDef.id,
      category: getCategory(sourceDef.category),
      source: sourceSpec,
    };

    if (sourceDef.eliBest) source.best = true;
    if (sourceDef.description) source.description = sourceDef.description;
    if (sourceDef.defaultForType)
      source.defaultForType = sourceDef.defaultForType;
    if (sourceDef.bounds) source.bounds = sourceDef.bounds;
    if (sourceDef.privacyPolicyUrl)
      source.privacyPolicyUrl = sourceDef.privacyPolicyUrl;
    if (sourceDef.permissionRef) source.permissionRef = sourceDef.permissionRef;
    if (sourceDef.icon) source.icon = sourceDef.icon;
    if (sourceDef.date) source.date = sourceDef.date;

    tilesSources.push(source);

    function getCategory(
      jsonCategory: JsonTilesSourceCategory,
    ): TilesSourceCategory {
      if (jsonCategory === "photo" || jsonCategory === "historicphoto")
        return "photo";
      if (
        jsonCategory === "map" ||
        jsonCategory === "historicmap" ||
        jsonCategory === "osmbasedmap"
      )
        return "map";
      return jsonCategory;
    }
  }

  return tilesSources;
}
