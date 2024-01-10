import {LngLat, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import * as geojson from "geojson";

import {Dict} from "../../types";
import {copyLngLat} from "./utils";

export type Geometry = Point | Polyline | Polygon;

export class MapFeature<T extends Geometry = Geometry> implements geojson.Feature<T> {
  readonly type = "Feature";
  readonly geometry: T;
  readonly properties: Dict = {};
  readonly id: string;

  constructor(id: string, geometry: T) {
    this.id = id;
    this.geometry = geometry;
  }

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    this.geometry.onDrag(e);
  }
}

export abstract class GeometryObject {
  #color: string = "#ffffff";

  get color(): string {
    return this.#color;
  }

  set color(color: string) {
    if (!color) {
      throw new Error("Missing color");
    }
    this.#color = color;
  }

  abstract onDrag(e: MapMouseEvent | MapTouchEvent): void;
}

export class Point extends GeometryObject implements geojson.Point {
  readonly type = "Point";
  coordinates: geojson.Position;
  #lngLat: LngLat;
  #radius: number = 4;

  constructor(coords: LngLat) {
    super();
    this.updateCoordinates(coords);
  }

  get lngLat(): LngLat {
    return copyLngLat(this.#lngLat);
  }

  get radius(): number {
    return this.#radius;
  }

  set radius(radius: number) {
    if (radius < 1) {
      throw new Error(`Point radius is too small: ${radius}`);
    }
    this.#radius = radius;
  }

  updateCoordinates(lngLat: LngLat) {
    this.#lngLat = copyLngLat(lngLat);
    this.coordinates = lngLat.toArray();
  }

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    this.updateCoordinates(e.lngLat);
  }
}

export abstract class LinearGeometry extends GeometryObject {
  protected drawing: boolean = false;
  protected readonly vertices_: MapFeature<Point>[] = [];
  readonly #minVerticesNumber: number;
  #width: number = 4;

  protected constructor(minVerticesNumber: number) {
    super();
    this.#minVerticesNumber = minVerticesNumber;
  }

  get vertices() {
    return [...this.vertices_];
  }

  get width(): number {
    return this.#width;
  }

  set width(width: number) {
    if (width < 1) {
      throw new Error(`Line width is too small: ${width}`);
    }
    this.#width = width;
  }

  protected abstract updateCoords(): void;

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: MapFeature<Point>, atStart: boolean = false) {
    if (atStart) {
      this.vertices_.unshift(vertex);
    } else {
      this.vertices_.push(vertex);
    }
    this.updateCoords();
  }

  // TODO prevent adding the same point twice consecutively
  addVertexAt(vertex: MapFeature<Point>, index: number) {
    this.vertices_.splice(index, 0, vertex);
    this.updateCoords();
  }

  removeVertex(vertex: MapFeature<Point>) {
    if (this.vertices_.length === this.#minVerticesNumber) {
      throw new Error("Cannot remove anymore point");
    }
    this.vertices_.splice(this.vertices_.indexOf(vertex), 1);
    this.updateCoords();
  }

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    // TODO
  }
}

export enum PolylineDirection {
  FORWARD,
  BACKWARD,
}

export class Polyline extends LinearGeometry implements geojson.LineString {
  readonly type = "LineString";
  coordinates: geojson.Position[];
  protected direction_: PolylineDirection = PolylineDirection.FORWARD;

  constructor(vertices?: MapFeature<Point>[]) {
    super(2);
    vertices?.forEach(v => this.appendVertex(v));
  }

  protected updateCoords() {
    this.coordinates = this.vertices_.map(p => p.geometry.coordinates);
  }

  get direction(): PolylineDirection {
    return this.direction_;
  }

  set direction(d: PolylineDirection) {
    this.direction_ = d ?? PolylineDirection.FORWARD;
  }
}

export class Polygon extends LinearGeometry implements geojson.Polygon {
  readonly type = "Polygon";
  coordinates: geojson.Position[][];
  #bgColor: string = "#ffffff80";

  constructor(vertices?: MapFeature<Point>[]) {
    super(3);
    vertices?.forEach(v => this.appendVertex(v));
  }

  protected updateCoords() {
    this.coordinates = [this.vertices_.map(p => p.geometry.coordinates)];
  }

  appendVertex(vertex: MapFeature<Point>, atStart: boolean = false) {
    if (!this.drawing) {
      throw new Error("Cannot append points to already drawn polygon");
    }
    super.appendVertex(vertex, atStart);
  }

  get bgColor(): string {
    return this.#bgColor;
  }

  set bgColor(color: string) {
    if (!color) {
      throw new Error("Missing color");
    }
    this.#bgColor = color;
  }
}
