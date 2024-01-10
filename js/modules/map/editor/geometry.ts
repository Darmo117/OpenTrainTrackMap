import {LngLat, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import * as geojson from "geojson";

import {Dict} from "../../types";
import {copyLngLat} from "./utils";

export type Geometry = geojson.Point | geojson.LineString | geojson.Polygon;

export abstract class MapFeature<T extends Geometry = Geometry> implements geojson.Feature<T> {
  // Fields required by geojson.Feature
  readonly type = "Feature";
  readonly geometry: T;
  readonly properties: Dict = {};
  readonly id: string;
  // Custom fields
  private color_: string = "#ffffff";

  protected constructor(id: string, geometry: T) {
    this.id = id;
    this.geometry = geometry;
  }

  get color(): string {
    return this.color_;
  }

  set color(color: string) {
    if (!color) {
      throw new Error("Missing color");
    }
    this.color_ = color;
  }

  abstract onDrag(e: MapMouseEvent | MapTouchEvent): void;
}

export class Point extends MapFeature<geojson.Point> {
  #lngLat: LngLat;
  #radius: number = 4;
  #boundFeatures: Set<LinearFeature> = new Set();

  constructor(id: string, coords: LngLat) {
    super(id, {
      type: "Point",
      coordinates: null,
    });
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

  get boundFeatures(): LinearFeature[] {
    return [...this.#boundFeatures];
  }

  updateCoordinates(lngLat: LngLat) {
    this.#lngLat = copyLngLat(lngLat);
    this.geometry.coordinates = lngLat.toArray();
  }

  bindFeature(feature: LinearFeature) {
    this.#boundFeatures.add(feature);
  }

  unbindFeature(feature: LinearFeature) {
    this.#boundFeatures.delete(feature);
  }

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    this.updateCoordinates(e.lngLat);
    this.#boundFeatures.forEach(f => f.onVertexDrag(this));
  }
}

export type LinearGeometry = geojson.LineString | geojson.Polygon;

export abstract class LinearFeature<T extends LinearGeometry = LinearGeometry> extends MapFeature<T> {
  protected drawing: boolean = false;
  protected readonly vertices_: Point[] = [];
  private readonly minVerticesNumber_: number;
  private width_: number = 4;

  protected constructor(id: string, geometry: T, minVerticesNumber: number) {
    super(id, geometry);
    this.minVerticesNumber_ = minVerticesNumber;
  }

  get vertices() {
    return [...this.vertices_];
  }

  get width(): number {
    return this.width_;
  }

  set width(width: number) {
    if (width < 1) {
      throw new Error(`Line width is too small: ${width}`);
    }
    this.width_ = width;
  }

  protected abstract updateCoords(): void;

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: Point, atStart: boolean = false) {
    vertex.bindFeature(this);
    if (atStart) {
      this.vertices_.unshift(vertex);
    } else {
      this.vertices_.push(vertex);
    }
    this.updateCoords();
  }

  // TODO prevent adding the same point twice consecutively
  addVertexAt(vertex: Point, index: number) {
    this.vertices_.splice(index, 0, vertex);
    this.updateCoords();
  }

  removeVertex(vertex: Point) {
    if (this.vertices_.length === this.minVerticesNumber_) {
      throw new Error("Cannot remove anymore point");
    }
    const deleted = this.vertices_.splice(this.vertices_.indexOf(vertex), 1);
    deleted.forEach(v => v.unbindFeature(this));
    this.updateCoords();
  }

  abstract onVertexDrag(vertex: Point): void;

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    // TODO drag all points (call their onDrag() method?)
  }
}

export enum PolylineDirection {
  FORWARD,
  BACKWARD,
}

export class Polyline extends LinearFeature<geojson.LineString> {
  #direction: PolylineDirection = PolylineDirection.FORWARD;

  constructor(id: string, vertices?: Point[]) {
    super(id, {
      type: "LineString",
      coordinates: [],
    }, 2);
    vertices?.forEach(v => this.appendVertex(v));
  }

  protected updateCoords() {
    this.geometry.coordinates = this.vertices_.map(p => p.geometry.coordinates);
  }

  get direction(): PolylineDirection {
    return this.#direction;
  }

  set direction(d: PolylineDirection) {
    this.#direction = d ?? PolylineDirection.FORWARD;
  }

  onVertexDrag(vertex: Point) {
    const i = this.vertices_.indexOf(vertex);
    if (i >= 0) {
      const thisCoord = this.geometry.coordinates[i];
      const vCoord = vertex.geometry.coordinates;
      thisCoord[0] = vCoord[0];
      thisCoord[1] = vCoord[1];
    }
  }
}

export class Polygon extends LinearFeature<geojson.Polygon> {
  #bgColor: string = "#ffffff80";

  constructor(id: string, vertices?: Point[]) {
    super(id, {
      type: "Polygon",
      coordinates: [[]],
    }, 3);
    this.drawing = true;
    vertices?.forEach(v => this.appendVertex(v));
    this.drawing = false;
  }

  protected updateCoords() {
    this.geometry.coordinates = [this.vertices_.map(p => p.geometry.coordinates)];
  }

  appendVertex(vertex: Point, atStart: boolean = false) {
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

  onVertexDrag(vertex: Point) {
    const i = this.vertices_.indexOf(vertex);
    if (i >= 0) {
      const thisCoord = this.geometry.coordinates[0][i];
      const vCoord = vertex.geometry.coordinates;
      thisCoord[0] = vCoord[0];
      thisCoord[1] = vCoord[1];
    }
  }
}
