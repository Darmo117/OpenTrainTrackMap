import {
  RasterSourceSpecificationWithId,
  TilesSource,
  TilesSourceType,
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
 * The available tile source categories.
 */
export type TilesSourceCategory =
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
  category: TilesSourceCategory;
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
  const tileSourcesDefinitions = tileSourcesDefs as TilesSourceDefinition[];
  tileSourcesDefinitions.sort(
    // Most source names are in English, use this locale for sorting
    (s1, s2) =>
      new Intl.Collator("en", {
        usage: "sort",
        numeric: true,
        sensitivity: "accent",
      }).compare(s1.name, s2.name),
  );

  const tilesSources: TilesSource[] = [];

  for (const sourceDef of tileSourcesDefinitions) {
    const sourceSpec: RasterSourceSpecificationWithId = {
      id: sourceDef.id,
      type: "raster",
      tiles: [sourceDef.url],
      tileSize: sourceDef.tileSize ?? 256,
    };

    if (sourceDef.attributionText) {
      let attrib = sourceDef.attributionText;
      if (sourceDef.attributionUrl)
        attrib = `<a href="${sourceDef.attributionUrl}" target="_blank">${attrib}</a>`;
      sourceSpec.attribution = attrib;
    } else if (sourceDef.attributionUrl)
      sourceSpec.attribution = `<a href="${sourceDef.attributionUrl}" target="_blank">${sourceDef.attributionUrl}</a>`;
    if (sourceDef.minZoom) sourceSpec.minzoom = sourceDef.minZoom;
    if (sourceDef.maxZoom) sourceSpec.maxzoom = sourceDef.maxZoom;

    const source: TilesSource = {
      label: sourceDef.name,
      id: sourceDef.id,
      type: getType(sourceDef.category),
      category: sourceDef.category,
      source: sourceSpec,
    };

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

    function getType(category: TilesSourceCategory): TilesSourceType {
      if (category === "photo" || category === "historicphoto") return "photo";
      return "map";
    }
  }

  return tilesSources;
}