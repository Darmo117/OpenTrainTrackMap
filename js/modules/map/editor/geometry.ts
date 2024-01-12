import * as mgl from "maplibre-gl";
import * as geojson from "geojson";

import * as types from "../../types";
import * as utils from "./utils";

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
export type PolygonProperties = LinearProperties;

export abstract class MapFeature<G extends Geometry = Geometry, P extends MapFeatureProperties = MapFeatureProperties>
    implements geojson.Feature<G, P> {
  // Fields required by geojson.Feature
  readonly type = "Feature";
  readonly geometry: G;
  readonly properties: P;
  readonly id: string;

  protected constructor(id: string, geometry: G, properties: types.Dict = {}) {
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

  abstract onDrag(pos: mgl.LngLat): void;
}

export class Point extends MapFeature<geojson.Point, PointProperties> {
  #lngLat: mgl.LngLat;
  #boundFeatures: Set<LinearFeature> = new Set();

  constructor(id: string, coords: mgl.LngLat) {
    super(id, {
      type: "Point",
      coordinates: null,
    }, {
      radius: 4,
    });
    this.#updateGeometry(coords);
  }

  // We need to redefined the getter as we override the setter
  // Cf. https://stackoverflow.com/questions/28950760/override-a-setter-and-the-getter-must-also-be-overridden
  get layer(): number {
    return this.properties.layer;
  }

  set layer(layer: number) {
    this.properties.layer = layer + 0.5;
  }

  get lngLat(): mgl.LngLat {
    return utils.copyLngLat(this.#lngLat);
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

  #updateGeometry(lngLat: mgl.LngLat) {
    this.#lngLat = utils.copyLngLat(lngLat);
    this.geometry.coordinates = lngLat.toArray();
    const {lng, lat} = lngLat;
    this.geometry.bbox = [lng, lat, lng, lat];
  }

  bindFeature(feature: LinearFeature) {
    this.#boundFeatures.add(feature);
  }

  unbindFeature(feature: LinearFeature) {
    this.#boundFeatures.delete(feature);
  }

  onDrag(pos: mgl.LngLat) {
    this.#updateGeometry(pos);
    this.#boundFeatures.forEach(f => f.onVertexDrag());
  }
}

export type LinearGeometry = geojson.LineString | geojson.Polygon;

export abstract class LinearFeature<G extends LinearGeometry = LinearGeometry, P extends LinearProperties = LinearProperties>
    extends MapFeature<G, P> {

  protected constructor(id: string, geometry: G, properties: types.Dict) {
    super(id, geometry, properties);
  }

  abstract removeVertex(vertex: Point): void;

  abstract onVertexDrag(): void;

  // TODO copy data from oldVertex to newVertex if newVertex is just a point with no data
  abstract replaceVertex(newVertex: Point, oldVertex: Point): void;

  abstract insertVertexAfter(vertex: Point, path: string): void;

  abstract getVertex(path: string): Point | null;

  abstract getSegmentVertices(path: string): [mgl.LngLat, mgl.LngLat];

  abstract incrementPath(path: string): string;
}

export enum PolylineDirection {
  FORWARD,
  BACKWARD,
}

export class LineString extends LinearFeature<geojson.LineString, PolylineProperties> {
  static readonly #PATH_PATTERN = /^(\d+)$/;

  readonly #vertices: Point[] = [];
  #direction: PolylineDirection = PolylineDirection.FORWARD;

  constructor(id: string, vertices?: Point[]) {
    super(id, {
      type: "LineString",
      coordinates: [],
    }, {
      width: 4,
    });
    if (vertices) {
      if (vertices.length < 2) {
        throw new Error(`Expected at least 2 points, got ${vertices.length} in linestring ${id}`);
      }
      vertices.forEach(v => this.appendVertex(v));
    }
  }

  get vertices(): Point[] {
    return [...this.#vertices];
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

  get direction(): PolylineDirection {
    return this.#direction;
  }

  set direction(d: PolylineDirection) {
    this.#direction = d ?? PolylineDirection.FORWARD;
  }

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: Point, atStart: boolean = false) {
    vertex.bindFeature(this);
    if (atStart) {
      this.#vertices.unshift(vertex);
    } else {
      this.#vertices.push(vertex);
    }
    this.#updateGeometry();
  }

  removeVertex(vertex: Point) {
    if (this.#vertices.length === 2) {
      throw new Error("Cannot remove anymore point");
    }
    // FIXME vertex may appear several times
    const deleted = this.#vertices.splice(this.#vertices.indexOf(vertex), 1);
    deleted.forEach(v => v.unbindFeature(this));
    this.#updateGeometry();
  }

  onVertexDrag() {
    this.#updateGeometry();
  }

  onDrag(pos: mgl.LngLat) {
    // TODO
  }

  // TODO prevent adding the same point twice consecutively
  replaceVertex(newVertex: Point, oldVertex: Point): void {
    const i = this.#vertices.indexOf(oldVertex);
    if (i !== -1) {
      this.#vertices[i] = newVertex;
      newVertex.bindFeature(this);
      oldVertex.unbindFeature(this);
    }
  }

  // TODO prevent adding the same point twice consecutively
  insertVertexAfter(vertex: Point, path: string) {
    const index = this.#getVertexIndex(path);
    // Cannot add after last vertex
    if (index !== null && index < this.#vertices.length - 1) {
      vertex.bindFeature(this);
      this.#vertices.splice(index + 1, 0, vertex);
      this.#updateGeometry();
    }
  }

  incrementPath(path: string): string {
    const index = this.#getVertexIndex(path);
    if (index !== null) {
      return "" + (index + 1) % this.#vertices.length;
    } else {
      return null;
    }
  }

  getVertex(path: string): Point | null {
    const index = this.#getVertexIndex(path);
    if (index !== null && index < this.#vertices.length) {
      return this.#vertices[index];
    } else {
      return null;
    }
  }

  getSegmentVertices(path: string): [mgl.LngLat, mgl.LngLat] {
    const index = this.#getVertexIndex(path);
    if (index !== null && index < this.#vertices.length) {
      return [this.#vertices[index].lngLat, this.#vertices[index + 1].lngLat];
    } else {
      return null;
    }
  }

  #getVertexIndex(path: string): number | null {
    const m = LineString.#PATH_PATTERN.exec(path);
    return m ? +m[1] : null;
  }

  #updateGeometry() {
    this.geometry.coordinates = [];
    let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
    for (const vertex of this.#vertices) {
      const {lng, lat} = vertex.lngLat;
      this.geometry.coordinates.push([lng, lat]);
      west = Math.min(lng, west);
      south = Math.min(lat, south);
      east = Math.max(lng, east);
      north = Math.max(lat, north);
    }
    this.geometry.bbox = [west, south, east, north];
  }
}

export class Polygon extends LinearFeature<geojson.Polygon, PolygonProperties> {
  static readonly #PATH_PATTERN = /^(\d+)\.(\d+)$/;

  readonly #vertices: Point[][] = [];
  #drawing: boolean = false;

  constructor(id: string, vertices?: Point[][]) {
    super(id, {
      type: "Polygon",
      coordinates: [[]],
    }, {});
    this.#drawing = true;
    if (vertices) {
      for (const vs of vertices) {
        if (vs.length < 3) {
          throw new Error(`Expected at least 3 points, got ${vs.length} in polygon ${id}`);
        }
      }
      for (let i = 0; i < vertices.length; i++) {
        vertices[i].forEach(v => this.appendVertex(v, i))
      }
    }
    this.#drawing = false;
  }

  get vertices(): Point[][] {
    return [...this.#vertices.map(vs => [...vs])];
  }

  get drawing(): boolean {
    return this.#drawing;
  }

  set drawing(drawing: boolean) {
    this.#drawing = drawing;
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

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: Point, ringIndex: number) {
    if (!this.#drawing) {
      throw new Error("Cannot append points to already drawn polygon");
    }
    if (ringIndex > this.#vertices.length) {
      throw new Error(`Ring #${ringIndex} does not exist in polygon ${this.id}`)
    }
    if (ringIndex === this.#vertices.length) {
      this.#vertices.push([]);
    }
    vertex.bindFeature(this);
    this.#vertices[ringIndex].push(vertex);
    this.#updateGeometry();
  }

  removeVertex(vertex: Point) {
    const indices: number[] = [];
    for (let i = 0; i < this.#vertices.length; i++) {
      if (this.#vertices[i].indexOf(vertex) > -1) {
        if (this.#vertices[i].length <= 3) {
          throw new Error("Cannot remove anymore point");
        }
        indices.push(i);
      }
    }
    indices.forEach(i => {
      const line = this.#vertices[i];
      // FIXME vertex may appear several times
      const deleted = line.splice(line.indexOf(vertex), 1);
      deleted.forEach(v => v.unbindFeature(this));
    });
    this.#updateGeometry();
  }

  onVertexDrag() {
    this.#updateGeometry();
  }

  onDrag(pos: mgl.LngLat) {
    // TODO
  }

  // TODO prevent adding the same point twice consecutively
  replaceVertex(newVertex: Point, oldVertex: Point): void {
    for (const ring of this.#vertices) {
      const i = ring.indexOf(oldVertex);
      if (i !== -1) {
        ring[i] = newVertex;
        newVertex.bindFeature(this);
        oldVertex.unbindFeature(this);
      }
    }
  }

  // TODO prevent adding the same point twice consecutively
  insertVertexAfter(vertex: Point, path: string) {
    const indices = this.#getVertexIndex(path);
    if (indices !== null && indices[0] < this.#vertices.length && indices[1] < this.#vertices[indices[0]].length) {
      vertex.bindFeature(this);
      if (indices[1] === this.#vertices[indices[0]].length - 1) {
        this.#vertices[indices[0]].push(vertex);
      } else {
        this.#vertices[indices[0]].splice(indices[1] + 1, 0, vertex);
      }
      this.#updateGeometry();
    }
  }

  incrementPath(path: string): string {
    const indices = this.#getVertexIndex(path);
    if (indices !== null && indices[0] < this.#vertices.length) {
      return `${indices[0]}.${(indices[1] + 1) % this.#vertices[indices[0]].length}`;
    } else {
      return null;
    }
  }

  getVertex(path: string): Point | null {
    const indices = this.#getVertexIndex(path);
    if (indices !== null && indices[0] < this.#vertices.length && indices[1] < this.#vertices[indices[0]].length) {
      return this.#vertices[indices[0]][indices[1]];
    } else {
      return null;
    }
  }

  getSegmentVertices(path: string): [mgl.LngLat, mgl.LngLat] {
    const indices = this.#getVertexIndex(path);
    if (indices !== null && indices[0] < this.#vertices.length && indices[1] < this.#vertices[indices[0]].length) {
      const ring = this.#vertices[indices[0]];
      return [ring[indices[1]].lngLat, ring[(indices[1] + 1) % ring.length].lngLat];
    } else {
      return null;
    }
  }

  #getVertexIndex(path: string): [number, number] | null {
    const m = Polygon.#PATH_PATTERN.exec(path);
    return m ? [+m[1], +m[2]] : null;
  }

  #updateGeometry() {
    this.geometry.coordinates = [];
    let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
    for (const ring of this.#vertices) {
      const points: [number, number][] = [];
      for (const vertex of ring) {
        const {lng, lat} = vertex.lngLat;
        points.push([lng, lat]);
        west = Math.min(lng, west);
        south = Math.min(lat, south);
        east = Math.max(lng, east);
        north = Math.max(lat, north);
      }
      // Add first point at the end as GeoJSON requires
      points.push(ring[0].lngLat.toArray());
      this.geometry.coordinates.push(points);
    }
    this.geometry.bbox = [west, south, east, north];
  }
}
