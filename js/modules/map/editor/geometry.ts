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

export type Action = DoNothingAction | DeleteFeatureAction | DeleteRingAction;
export type DoNothingAction = {
  type: "do_nothing";
};
export type DeleteFeatureAction = {
  type: "delete_feature";
};
export type DeleteRingAction = {
  type: "delete_ring";
  points: Point[];
}

export abstract class LinearFeature<G extends LinearGeometry = LinearGeometry, P extends LinearProperties = LinearProperties>
    extends MapFeature<G, P> {

  protected constructor(id: string, geometry: G, properties: types.Dict) {
    super(id, geometry, properties);
  }

  /**
   * Check whether the given vertex can be appended in this feature at the given path.
   * @param vertex The vertex to check.
   * @param path The path.
   * @returns True if the vertex can be appended at the given path, false otherwise.
   */
  abstract canAppendVertex(vertex: Point, path: string): boolean;

  /**
   * Append a vertex to this feature at the given path.
   * @param vertex The vertex to append.
   * @param path The path.
   */
  abstract appendVertex(vertex: Point, path: string): void;

  /**
   * Remove the given vertex from this feature.
   * @param vertex The vertex to remove.
   * @returns The action to perform.
   */
  abstract removeVertex(vertex: Point): Action;

  /**
   * Check whether this feature can accept the given vertex anywhere.
   * @param vertex The vertex to check.
   * @returns True if this feature is accepted, false otherwise.
   */
  abstract canAcceptVertex(vertex: Point): boolean

  /**
   * Check whether the given vertex can be inserted in this feature at the given path.
   * @param vertex The vertex to check.
   * @param path The path.
   * @returns True if the vertex can be inserted at the given path, false otherwise.
   */
  abstract canInsertVertex(vertex: Point, path: string): boolean

  // TODO copy data from oldVertex to newVertex if newVertex is just a point with no data
  /**
   * Replace a vertex of this feature by the specified one.
   * @param newVertex The vertex to put in place of the second one.
   * @param oldVertex The vertex to replace.
   * @returns True if the vertex was replaced, false if it could not.
   */
  abstract replaceVertex(newVertex: Point, oldVertex: Point): void;

  /**
   * Insert the given vertex after the specified path.
   * @param vertex The vertex to insert.
   * @param path The path to insert the vertex after.
   */
  abstract insertVertexAfter(vertex: Point, path: string): void;

  /**
   * Get the vertex at the given path.
   * @param path The path to the point.
   * @returns The vertex for the path or null if none matched.
   */
  abstract getVertex(path: string): Point | null;

  /**
   * Get the vertices of the segment at the given path.
   * @param path The path to the segment.
   * @returns The vertices for the path or null if none matched.
   */
  abstract getSegmentVertices(path: string): [Point, Point] | null;

  /**
   * Increment the point index in the given path.
   * @param path The path.
   * @returns The incremented path.
   */
  abstract incrementPath(path: string): string;

  /**
   * Called when one of the vertices of this feature is being dragged.
   */
  abstract onVertexDrag(): void;
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
      for (let i = 0; i < vertices.length; i++) {
        const vertex = vertices[i];
        const path = "" + i;
        if (!this.canAppendVertex(vertex, path)) {
          throw new Error(`Cannot append vertex ${vertex.id} at ${path}`);
        }
        this.appendVertex(vertex, path);
      }
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

  canAppendVertex(vertex: Point, path: string): boolean {
    if (!this.canAcceptVertex(vertex)) {
      return false;
    }
    const i = this.#getVertexIndex(path);
    return i !== null && (i === 0 || i === this.#vertices.length);
  }

  appendVertex(vertex: Point, path: string) {
    if (!this.canAppendVertex(vertex, path)) {
      return;
    }
    if (this.#getVertexIndex(path) === 0) {
      this.#vertices.unshift(vertex);
    } else {
      this.#vertices.push(vertex);
    }
    vertex.bindFeature(this);
    this.#updateGeometry();
  }

  removeVertex(vertex: Point): Action {
    const i = this.#vertices.indexOf(vertex);
    if (i !== -1) {
      if (this.#vertices.length === 2) {
        return {type: "delete_feature"};
      }
      this.#vertices.splice(i, 1);
      vertex.unbindFeature(this);
      this.#updateGeometry();
    }
    return {type: "do_nothing"};
  }

  canAcceptVertex(vertex: Point): boolean {
    return !this.#vertices.includes(vertex);
  }

  canInsertVertex(vertex: Point, path: string): boolean {
    if (!this.canAcceptVertex(vertex)) {
      return false;
    }
    const i = this.#getVertexIndex(path);
    // Cannot insert after last vertex
    return i !== null && i < this.#vertices.length - 1;
  }

  replaceVertex(newVertex: Point, oldVertex: Point) {
    if (!this.canAcceptVertex(newVertex)) {
      return;
    }
    this.#vertices[this.#vertices.indexOf(oldVertex)] = newVertex;
    newVertex.bindFeature(this);
    oldVertex.unbindFeature(this);
    this.#updateGeometry();
  }

  insertVertexAfter(vertex: Point, path: string) {
    if (!this.canInsertVertex(vertex, path)) {
      return;
    }
    this.#vertices.splice(this.#getVertexIndex(path) + 1, 0, vertex);
    vertex.bindFeature(this);
    this.#updateGeometry();
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

  getSegmentVertices(path: string): [Point, Point] | null {
    const index = this.#getVertexIndex(path);
    if (index !== null && index < this.#vertices.length - 1) {
      return [this.#vertices[index], this.#vertices[index + 1]];
    } else {
      return null;
    }
  }

  onVertexDrag() {
    this.#updateGeometry();
  }

  onDrag(pos: mgl.LngLat) {
    // TODO
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
      // Separate loop to avoid binding vertices unnecessarily
      for (let i = 0; i < vertices.length; i++) {
        const ring = vertices[i];
        if (ring.length < 3) {
          throw new Error(`Expected at least 3 points, got ${ring.length} in ring ${i} of polygon ${id}`);
        }
      }
      for (let ringI = 0; ringI < vertices.length; ringI++) {
        const ring = vertices[ringI];
        for (let vertexI = 0; vertexI < ring.length; vertexI++) {
          const vertex = ring[vertexI];
          const path = `${ringI}.${vertexI}`;
          if (!this.canAppendVertex(vertex, path)) {
            throw new Error(`Cannot append vertex ${vertex.id} at ${path}`);
          }
          this.appendVertex(vertex, path);
        }
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

  canAppendVertex(vertex: Point, path: string): boolean {
    if (!this.canAcceptVertex(vertex) || !this.#drawing) {
      return false;
    }
    const indices = this.#getVertexIndex(path);
    return indices !== null
        && (indices[0] < this.#vertices.length && (indices[1] === 0 || indices[1] === this.#vertices[indices[0]].length)
            || indices[0] === this.#vertices.length && indices[1] === 0);
  }

  appendVertex(vertex: Point, path: string) {
    if (!this.canAppendVertex(vertex, path)) {
      return;
    }
    const [ringI, vertexI] = this.#getVertexIndex(path);
    let ring: Point[];
    if (ringI === this.#vertices.length) {
      this.#vertices.push(ring = []);
    } else {
      ring = this.#vertices[ringI];
    }
    if (vertexI === 0) {
      ring.unshift(vertex);
    } else {
      ring.push(vertex);
    }
    vertex.bindFeature(this);
    this.#updateGeometry();
  }

  removeVertex(vertex: Point): Action {
    for (let ringI = 0; ringI < this.#vertices.length; ringI++) {
      const ring = this.#vertices[ringI];
      const i = ring.indexOf(vertex);
      if (i !== -1) {
        if (ring.length === 3) {
          if (ringI === 0) {
            return {type: "delete_feature"};
          }
          return {type: "delete_ring", points: ring};
        }
        ring.splice(i, 1);
        vertex.unbindFeature(this);
        this.#updateGeometry();
        return {type: "do_nothing"};
      }
    }
  }

  canAcceptVertex(vertex: Point): boolean {
    return !this.#vertices.some(ring => ring.includes(vertex));
  }

  canInsertVertex(vertex: Point, path: string): boolean {
    if (!this.canAcceptVertex(vertex)) {
      return false;
    }
    const indices = this.#getVertexIndex(path);
    return indices !== null
        && indices[0] < this.#vertices.length
        && indices[1] < this.#vertices[indices[0]].length;
  }

  replaceVertex(newVertex: Point, oldVertex: Point) {
    if (!this.canAcceptVertex(newVertex)) {
      return;
    }
    for (const ring of this.#vertices) {
      const i = ring.indexOf(oldVertex);
      if (i !== -1) {
        ring[i] = newVertex;
        newVertex.bindFeature(this);
        oldVertex.unbindFeature(this);
        this.#updateGeometry();
        break;
      }
    }
  }

  insertVertexAfter(vertex: Point, path: string) {
    if (!this.canInsertVertex(vertex, path)) {
      return;
    }
    const [ringI, vertexI] = this.#getVertexIndex(path);
    vertex.bindFeature(this);
    const ring = this.#vertices[ringI];
    if (vertexI === ring.length - 1) {
      ring.push(vertex);
    } else {
      ring.splice(vertexI + 1, 0, vertex);
    }
    this.#updateGeometry();
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

  getSegmentVertices(path: string): [Point, Point] | null {
    const indices = this.#getVertexIndex(path);
    if (indices !== null && indices[0] < this.#vertices.length && indices[1] < this.#vertices[indices[0]].length) {
      const ring = this.#vertices[indices[0]];
      return [ring[indices[1]], ring[(indices[1] + 1) % ring.length]];
    } else {
      return null;
    }
  }

  onVertexDrag() {
    this.#updateGeometry();
  }

  onDrag(pos: mgl.LngLat) {
    // TODO
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
