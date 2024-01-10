import {LngLat, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import * as geojson from "geojson";

import {Dict} from "../../types";
import {copyLngLat} from "./utils";

export type GeometryObject = Point | Polyline | Polygon;

export class MapFeature<T extends GeometryObject = GeometryObject> implements geojson.Feature<T> {
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

interface Draggable {
  onDrag(e: MapMouseEvent | MapTouchEvent): void;
}

export class Point implements geojson.Point, Draggable {
  readonly type = "Point";
  coordinates: geojson.Position;
  #lngLat: LngLat;

  constructor(coords: LngLat) {
    this.updateCoordinates(coords);
  }

  get lngLat(): LngLat {
    return copyLngLat(this.#lngLat);
  }

  updateCoordinates(lngLat: LngLat) {
    this.#lngLat = copyLngLat(lngLat);
    this.coordinates = lngLat.toArray();
  }

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    this.updateCoordinates(e.lngLat);
  }
}

export abstract class MultipointGeometry implements Draggable {
  protected drawing: boolean = false;
  protected vertices_: Point[];
  readonly #minVerticesNumber: number;

  protected constructor(minVerticesNumber: number) {
    this.#minVerticesNumber = minVerticesNumber;
  }

  get vertices() {
    return [...this.vertices_];
  }

  protected abstract updateCoords(): void;

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: Point, atStart: boolean = false) {
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

export class Polyline extends MultipointGeometry implements geojson.LineString {
  readonly type = "LineString";
  coordinates: geojson.Position[];
  protected direction_: PolylineDirection = PolylineDirection.FORWARD;

  constructor() {
    super(2);
  }

  protected updateCoords() {
    this.coordinates = this.vertices_.map(p => p.coordinates);
  }

  get direction(): PolylineDirection {
    return this.direction_;
  }

  set direction(d: PolylineDirection) {
    this.direction_ = d ?? PolylineDirection.FORWARD;
  }
}

export class Polygon extends MultipointGeometry implements geojson.Polygon {
  readonly type = "Polygon";
  coordinates: geojson.Position[][];

  constructor() {
    super(3);
  }

  protected updateCoords() {
    this.coordinates = [this.vertices_.map(p => p.coordinates)];
  }

  appendVertex(vertex: Point, atStart: boolean = false) {
    if (!this.drawing) {
      throw new Error("Cannot append points to already drawn polygon");
    }
    super.appendVertex(vertex, atStart);
  }
}
