import {LngLat, MapMouseEvent, MapTouchEvent} from "maplibre-gl";
import * as geojson from "geojson";

import {Dict} from "../../types";
import {copyLngLat} from "./utils";

export type Geometry = geojson.Point | geojson.LineString | geojson.Polygon;

export type MapFeatureProperties = {
  color: string;
  layer: number;
};
export type PointProperties = MapFeatureProperties & {
  radius: number;
};
export type LinearProperties = MapFeatureProperties & {
  width: number;
}
export type PolylineProperties = LinearProperties;
export type PolygonProperties = LinearProperties & {
  bgColor: string;
};

export abstract class MapFeature<G extends Geometry = Geometry, P extends MapFeatureProperties = MapFeatureProperties>
    implements geojson.Feature<G, P> {
  // Fields required by geojson.Feature
  readonly type = "Feature";
  readonly geometry: G;
  readonly properties: P;
  readonly id: string;

  protected constructor(id: string, geometry: G, properties: Dict = {}) {
    this.id = id;
    this.geometry = geometry;
    this.properties = Object.assign({
      color: "#ffffff",
      layer: 0,
    }, properties) as P;
    this.layer = 0;
  }

  get color(): string {
    return this.properties.color;
  }

  set color(color: string) {
    if (!color) {
      throw new Error("Missing color");
    }
    this.properties.color = color;
  }

  get layer(): number {
    return this.properties.layer;
  }

  set layer(layer: number) {
    this.properties.layer = layer;
  }

  abstract onDrag(e: MapMouseEvent | MapTouchEvent): void;
}

export class Point extends MapFeature<geojson.Point, PointProperties> {
  #lngLat: LngLat;
  #boundFeatures: Set<LinearFeature> = new Set();

  constructor(id: string, coords: LngLat) {
    super(id, {
      type: "Point",
      coordinates: null,
    }, {
      radius: 4,
    });
    this.updateCoordinates(coords);
  }

  // We need to redefined the getter as we override the setter
  // Cf. https://stackoverflow.com/questions/28950760/override-a-setter-and-the-getter-must-also-be-overridden
  get layer(): number {
    return this.properties.layer;
  }

  set layer(layer: number) {
    this.properties.layer = layer + 0.5;
  }

  get lngLat(): LngLat {
    return copyLngLat(this.#lngLat);
  }

  get radius(): number {
    return this.properties.radius;
  }

  set radius(radius: number) {
    if (radius < 1) {
      throw new Error(`Point radius is too small: ${radius}`);
    }
    this.properties.radius = radius;
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

export abstract class LinearFeature<G extends LinearGeometry = LinearGeometry, P extends LinearProperties = LinearProperties>
    extends MapFeature<G, P> {
  protected _drawing: boolean = false;
  protected readonly _vertices: Point[] = [];
  private readonly _minVerticesNumber: number;

  protected constructor(id: string, geometry: G, properties: Dict, minVerticesNumber: number) {
    super(id, geometry, {width: 4, ...properties});
    this._minVerticesNumber = minVerticesNumber;
  }

  get vertices() {
    return [...this._vertices];
  }

  get width(): number {
    return this.properties.width;
  }

  set width(width: number) {
    if (width < 1) {
      throw new Error(`Line width is too small: ${width}`);
    }
    this.properties.width = width;
  }

  protected abstract updateCoords(): void;

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: Point, atStart: boolean = false) {
    vertex.bindFeature(this);
    if (atStart) {
      this._vertices.unshift(vertex);
    } else {
      this._vertices.push(vertex);
    }
    this.updateCoords();
  }

  // TODO prevent adding the same point twice consecutively
  addVertexAt(vertex: Point, index: number) {
    this._vertices.splice(index, 0, vertex);
    this.updateCoords();
  }

  removeVertex(vertex: Point) {
    if (this._vertices.length === this._minVerticesNumber) {
      throw new Error("Cannot remove anymore point");
    }
    const deleted = this._vertices.splice(this._vertices.indexOf(vertex), 1);
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

export class Polyline extends LinearFeature<geojson.LineString, PolylineProperties> {
  #direction: PolylineDirection = PolylineDirection.FORWARD;

  constructor(id: string, vertices?: Point[]) {
    super(id, {
      type: "LineString",
      coordinates: [],
    }, {}, 2);
    vertices?.forEach(v => this.appendVertex(v));
  }

  protected updateCoords() {
    this.geometry.coordinates = this._vertices.map(p => p.geometry.coordinates);
  }

  get direction(): PolylineDirection {
    return this.#direction;
  }

  set direction(d: PolylineDirection) {
    this.#direction = d ?? PolylineDirection.FORWARD;
  }

  onVertexDrag(vertex: Point) {
    const i = this._vertices.indexOf(vertex);
    if (i >= 0) {
      const thisCoord = this.geometry.coordinates[i];
      const vCoord = vertex.geometry.coordinates;
      thisCoord[0] = vCoord[0];
      thisCoord[1] = vCoord[1];
    }
  }
}

export class Polygon extends LinearFeature<geojson.Polygon, PolygonProperties> {
  constructor(id: string, vertices?: Point[]) {
    super(id, {
      type: "Polygon",
      coordinates: [[]],
    }, {
      bgColor: "#ffffff80",
    }, 3);
    this._drawing = true;
    vertices?.forEach(v => this.appendVertex(v));
    this._drawing = false;
  }

  protected updateCoords() {
    this.geometry.coordinates = [this._vertices.map(p => p.geometry.coordinates)];
  }

  appendVertex(vertex: Point, atStart: boolean = false) {
    if (!this._drawing) {
      throw new Error("Cannot append points to already drawn polygon");
    }
    super.appendVertex(vertex, atStart);
  }

  get bgColor(): string {
    return this.properties.bgColor;
  }

  set bgColor(color: string) {
    if (!color) {
      throw new Error("Missing color");
    }
    this.properties.bgColor = color;
  }

  onVertexDrag(vertex: Point) {
    const i = this._vertices.indexOf(vertex);
    if (i >= 0) {
      const thisCoord = this.geometry.coordinates[0][i];
      const vCoord = vertex.geometry.coordinates;
      thisCoord[0] = vCoord[0];
      thisCoord[1] = vCoord[1];
    }
  }
}
