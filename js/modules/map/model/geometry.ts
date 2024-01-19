import * as mgl from "maplibre-gl";
import * as geojson from "geojson";

import * as types from "../../types";
import * as st from "../../streams";
import * as utils from "../utils";

export type Geometry = geojson.Point | geojson.LineString | geojson.Polygon;

export type MapFeatureProperties = {
  color: string;
  layer: number;
  selectionMode: SelectionMode;
};
export type PointProperties = MapFeatureProperties & {
  radius: number;
};
export type LinearProperties = MapFeatureProperties;
export type PolylineProperties = LinearProperties & {
  width: number;
};
export type PolygonProperties = LinearProperties;

/**
 * This class represents a longitude/latitude offset on the map.
 */
export class LngLatVector {
  /**
   * The zero vector.
   */
  static readonly ZERO: LngLatVector = new LngLatVector(0, 0);

  /**
   * Get the vector of the difference between the two given positions.
   * @param ll1 The first position.
   * @param ll2 The position to substract from the first one.
   * @returns The distance vector `ll1 - ll2`.
   */
  static sub(ll1: mgl.LngLat, ll2: mgl.LngLat): LngLatVector {
    return new LngLatVector(ll1.lng - ll2.lng, ll1.lat - ll2.lat);
  }

  /**
   * The longitude offset.
   */
  readonly lng: number;
  /**
   * The latitude offset.
   */
  readonly lat: number;

  /**
   * Create a new vector.
   * @param lng The longitude offset.
   * @param lat The latitude offset.
   */
  constructor(lng: number, lat: number) {
    this.lng = lng;
    this.lat = lat;
  }

  /**
   * Add this vector to the given LngLat object.
   * @param lngLat The LngLat to offset.
   * @returns A new LngLat object.
   */
  addTo(lngLat: mgl.LngLat): mgl.LngLat {
    return new mgl.LngLat(lngLat.lng + this.lng, lngLat.lat + this.lat);
  }
}

/**
 * Enumeration of all possible selection states.
 */
export enum SelectionMode {
  NONE,
  SELECTED,
  HOVERED,
}

/**
 * A map feature is a geometry object that can be shown and manipulated in a {@link mgl.Map}.
 * It implements GeoJSON’s {@link geojson.Feature} structure.
 *
 * The `geometry` field implements GeoJSON’s {@link geojson.GeoJsonObject} structure.
 *
 * All map features have the following entries in their `properties` field:
 * * `color: string`: the feature’s color.
 * * `layer: number`: the feature’s layer.
 *
 * The `geometry` and `properties` fields ***should NOT*** be modified manually.
 * Their publicly visible to respect the {@link geojson.Feature} structure.
 * Map features should always be modified through the relevant accessors and methods.
 *
 * Subclasses may define additional properties.
 *
 * @see geojson.Feature
 * @see Geometry
 * @see MapFeatureProperties
 */
export abstract class MapFeature<G extends Geometry = Geometry, P extends MapFeatureProperties = MapFeatureProperties>
    implements geojson.Feature<G, P> {
  // Fields required by geojson.Feature
  readonly type = "Feature";
  readonly geometry: G;
  readonly properties: P;
  readonly id: string;

  /**
   * Create a new map feature.
   * @param id The feature’s ID.
   * @param geometry The feature’s geometry object.
   * @param properties The feature’s additional properties.
   */
  protected constructor(id: string, geometry: G, properties: types.Dict = {}) {
    this.id = id;
    this.geometry = geometry;
    this.properties = Object.assign({
      color: "#ffffff",
      layer: 0,
      selectionMode: SelectionMode.NONE,
    }, properties) as P;
    this.layer = 0;
  }

  /**
   * This feature’s color.
   */
  get color(): string {
    return this.properties.color;
  }

  /**
   * Set this feature’s color.
   * @param color The new color.
   * @throws {Error} If the string is empty.
   */
  set color(color: string) {
    if (!color) {
      throw new Error("Missing color");
    }
    this.properties.color = color;
  }

  /**
   * This feature’s layer.
   */
  get layer(): number {
    return this.properties.layer;
  }

  /**
   * Set this feature’s layer.
   * @param layer The new layer.
   */
  set layer(layer: number) {
    this.properties.layer = layer;
  }

  /**
   * This feature’s selection mode.
   */
  get selectionMode(): SelectionMode {
    return this.properties.selectionMode;
  }

  /**
   * Set this feature’s selection mode.
   * @param mode The new mode.
   */
  set selectionMode(mode: SelectionMode) {
    this.properties.selectionMode = mode;
  }

  /**
   * Indicate whether this feature has any data bound to it.
   */
  abstract hasData(): boolean;

  /**
   * Copy the data of the given feature.
   * @param feature The feature to copy the data of.
   */
  abstract copyDataOf(feature: MapFeature<G, P>): void;
}

/**
 * A point feature represents a single point in space.
 *
 * Points may be isolated or bound to one or more {@link LinearFeature}s.
 * In the latter case, anytime a point is moved all its bound features are notified.
 */
export class Point extends MapFeature<geojson.Point, PointProperties> {
  #lngLat: mgl.LngLat;
  #boundFeatures: Set<LinearFeature> = new Set();

  /**
   * Create a new point.
   * @param id The feature’s ID.
   * @param coords The point’s coordinates.
   */
  constructor(id: string, coords: mgl.LngLat) {
    super(id, {
      type: "Point",
      coordinates: null, // Updated immediately by this.lngLat()
    }, {
      radius: 4,
    });
    this.lngLat = coords;
  }

  /**
   * This point’s location.
   * @returns A copy of the internal {@link mgl.LngLat} object.
   */
  get lngLat(): mgl.LngLat {
    return utils.copyLngLat(this.#lngLat);
  }

  /**
   * Set this point’s location.
   * @param lngLat This point’s new position.
   */
  set lngLat(lngLat: mgl.LngLat) {
    this.#lngLat = utils.copyLngLat(lngLat);
    this.#updateGeometry();
  }

  /**
   * This point’s radius in pixels.
   */
  get radius(): number {
    return this.properties.radius;
  }

  /**
   * Set this point’s radius in pixel.s
   * @param radius The new radius.
   * @throws {Error} If the radius is less than 1.
   */
  set radius(radius: number) {
    if (radius < 1) {
      throw new Error(`Point radius is too small: ${radius}`);
    }
    this.properties.radius = radius;
  }

  /**
   * A stream of all features this point is bound to.
   */
  get boundFeatures(): st.Stream<LinearFeature> {
    return st.stream(this.#boundFeatures);
  }

  /**
   * Bind this point to the given feature.
   * @param feature The feature to bind this point to.
   */
  bindFeature(feature: LinearFeature) {
    this.#boundFeatures.add(feature);
  }

  /**
   * Unbind this point from the given feature.
   * @param feature The feature to unbind this point from.
   */
  unbindFeature(feature: LinearFeature) {
    this.#boundFeatures.delete(feature);
  }

  /**
   * Called when this point is dragged on the map.
   * @param mousePos The mouse location.
   * @param offset The offset between the mouse position and this point’s current position.
   */
  onDrag(mousePos: mgl.LngLat, offset: LngLatVector = LngLatVector.ZERO): void {
    this.#lngLat = offset.addTo(mousePos);
    this.#updateGeometry();
  }

  hasData(): boolean {
    return false; // TODO
  }

  copyDataOf(point: Point): void {
    // TODO
  }

  /**
   * Update this point’s `geometry.coordinates` and `geometry.bbox` properties.
   * Also calls the {@link LinearFeature.onVertexDrag} method on all bound features.
   */
  #updateGeometry(): void {
    this.geometry.coordinates = this.#lngLat.toArray();
    const {lng, lat} = this.#lngLat;
    this.geometry.bbox = [lng, lat, lng, lat];
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
  ringIndex: number;
  points: Point[];
}

/**
 * A linear feature is such that it is composed of one or more lines of {@link Point}s.
 *
 * Vertices can be interacted with through what are called **paths**.
 * A path is a string that represents successive indices through this feature’s lines to a specific vertex.
 * For more details see subclasses.
 * @see LineString
 * @see Polygon
 */
export abstract class LinearFeature<G extends LinearGeometry = LinearGeometry, P extends LinearProperties = LinearProperties>
    extends MapFeature<G, P> {

  protected constructor(id: string, geometry: G, properties: types.Dict) {
    super(id, geometry, properties);
  }

  /**
   * Indicate whether this feature has any points.
   * @returns True if this feature has no points, false otherwise.
   */
  abstract isEmpty(): boolean;

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
   * Check whether this feature can accept the given vertex anywhere.
   * @param vertex The vertex to check.
   * @returns True if this feature is accepted, false otherwise.
   */
  abstract canAcceptVertex(vertex: Point): boolean

  /**
   * Replace a vertex of this feature by the specified one.
   * @param newVertex The vertex to put in place of the second one.
   * @param oldVertex The vertex to replace.
   * @returns True if the vertex was replaced, false if it could not.
   */
  abstract replaceVertex(newVertex: Point, oldVertex: Point): void;

  /**
   * Check whether the given vertex can be inserted in this feature at the given path.
   * @param vertex The vertex to check.
   * @param path The path.
   * @returns True if the vertex can be inserted at the given path, false otherwise.
   */
  abstract canInsertVertex(vertex: Point, path: string): boolean

  /**
   * Insert the given vertex after the specified path.
   * @param vertex The vertex to insert.
   * @param path The path to insert the vertex after.
   */
  abstract insertVertexAfter(vertex: Point, path: string): void;

  /**
   * Remove the given vertex from this feature.
   * @param vertex The vertex to remove.
   * @returns The action to perform.
   */
  abstract removeVertex(vertex: Point): Action;

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
   * Return the path of the segment formed by the two given points.
   * @param v1 One vertex of the segment.
   * @param v2 The other vertex of the segment.
   * @returns The segment’s path or null if there is no segment for the two points.
   */
  abstract getSegmentPath(v1: Point, v2: Point): string | null;

  /**
   * Return the path to the next possible vertex position on this feature’s outer line.
   */
  abstract getNextVertexPath(): string;

  /**
   * Called when one of the vertices of this feature is being dragged.
   */
  onVertexDrag() {
    this.updateGeometry();
  }

  /**
   * Indicate whether the outer line of this feature is nearly circular.
   */ // TODO what does that mean?
  abstract isNearlyCircular(): boolean;

  /**
   * Indicate whether the outer line of this feature is nearly square.
   */ // TODO what does that mean?
  abstract isNearlySquare(): boolean;

  /**
   * Update this feature’s `geometry.coordinates` and `geometry.bbox` properties.
   */
  protected abstract updateGeometry(): void;
}

export enum PolylineDirection {
  FORWARD,
  BACKWARD,
}

/**
 * A line string is a feature that is composed of segments represented by a list of {@link Point}s.
 *
 * A line string has a direction that is either:
 * * {@link PolylineDirection.FORWARD}: the line starts at vertex 0 towards the last one.
 * * {@link PolylineDirection.BACKWARD}: the line starts at its last vertex towards the first one.
 *
 * As a line string only contains a single vertex list, paths must respect the following format:
 * * `"<nb>"`, where `<nb>` is the index of the vertex/segment to target.
 */ // TODO allow loops (ie last point = first point)
export class LineString extends LinearFeature<geojson.LineString, PolylineProperties> {
  static readonly #PATH_PATTERN = /^(\d+)$/;

  readonly #vertices: Point[] = [];
  #direction: PolylineDirection = PolylineDirection.FORWARD;

  /**
   * Create a line string.
   * @param id The feature’s ID.
   * @param vertices Optional. A list of (at least 2) points. It must not contain any duplicates.
   * @throws {Error} If a point is present multiple times in the list of points or the list contains less than 2 points.
   */
  constructor(id: string, vertices?: Point[]) {
    super(id, {
      type: "LineString",
      coordinates: [],
    }, {
      width: 2,
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

  /**
   * An ordered stream containing this line’s vertices.
   */
  get vertices(): st.Stream<Point> {
    return st.stream(this.#vertices);
  }

  /**
   * This line’s width in pixels.
   */
  get width(): number {
    return this.properties.width;
  }

  /**
   * Set this line’s width in pixels.
   * @param width The new width.
   * @throws {Error} If the width is less than 1.
   */
  set width(width: number) {
    if (width < 1) {
      throw new Error(`Line width is too small: ${width}`);
    }
    this.properties.width = width;
  }

  /**
   * This line’s direction.
   */
  get direction(): PolylineDirection {
    return this.#direction;
  }

  /**
   * Set this line’s direction.
   * @param d The new direction.
   */
  set direction(d: PolylineDirection) {
    this.#direction = d ?? PolylineDirection.FORWARD;
  }

  isEmpty(): boolean {
    return this.#vertices.length === 0;
  }

  canAppendVertex(vertex: Point, path: string): boolean {
    if (!this.canAcceptVertex(vertex)) {
      return false;
    }
    const i = this.#getVertexIndex(path);
    return i !== null && (i === 0 || i === this.#vertices.length);
  }

  appendVertex(vertex: Point, path: string): void {
    if (!this.canAppendVertex(vertex, path)) {
      return;
    }
    if (this.#getVertexIndex(path) === 0) {
      this.#vertices.unshift(vertex);
    } else {
      this.#vertices.push(vertex);
    }
    vertex.bindFeature(this);
    this.updateGeometry();
  }

  canAcceptVertex(vertex: Point): boolean {
    return !this.#vertices.includes(vertex);
  }

  replaceVertex(newVertex: Point, oldVertex: Point): void {
    if (!this.canAcceptVertex(newVertex)) {
      return;
    }
    this.#vertices[this.#vertices.indexOf(oldVertex)] = newVertex;
    newVertex.bindFeature(this);
    oldVertex.unbindFeature(this);
    this.updateGeometry();
  }

  canInsertVertex(vertex: Point, path: string): boolean {
    if (!this.canAcceptVertex(vertex)) {
      return false;
    }
    const i = this.#getVertexIndex(path);
    // Cannot insert after last vertex
    return i !== null && i < this.#vertices.length - 1;
  }

  insertVertexAfter(vertex: Point, path: string): void {
    if (!this.canInsertVertex(vertex, path)) {
      return;
    }
    this.#vertices.splice(this.#getVertexIndex(path) + 1, 0, vertex);
    vertex.bindFeature(this);
    this.updateGeometry();
  }

  removeVertex(vertex: Point): Action {
    const i = this.#vertices.indexOf(vertex);
    if (i !== -1) {
      if (this.#vertices.length <= 2) {
        return {type: "delete_feature"};
      }
      this.#vertices.splice(i, 1);
      vertex.unbindFeature(this);
      this.updateGeometry();
    }
    return {type: "do_nothing"};
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

  incrementPath(path: string): string {
    const index = this.#getVertexIndex(path);
    if (index !== null) {
      return "" + (index + 1) % this.#vertices.length;
    } else {
      return null;
    }
  }

  getSegmentPath(v1: Point, v2: Point): string | null {
    const i1 = this.#vertices.indexOf(v1);
    const i2 = this.#vertices.indexOf(v2);
    if (i1 !== -1 && i2 !== -1) {
      if (i1 === i2 - 1) {
        return "" + i1;
      } else if (i2 === i1 - 1) {
        return "" + i2;
      }
    }
    return null;
  }

  getNextVertexPath(): string {
    return "" + this.#vertices.length;
  }

  /**
   * Check whether the given vertex is at one of the two ends of this line.
   * @param v The vertex to check.
   * @returns True if the vertex is the first or last one, false otherwise.
   */
  isEndVertex(v: Point): boolean {
    const i = this.#vertices.indexOf(v);
    return i === 0 || i === this.#vertices.length - 1;
  }

  /**
   * Indicate whether this line forms a loop, i.e. its first and last vertex are the same.
   */
  isLoop(): boolean {
    return false; // TODO
  }

  hasData(): boolean {
    return false; // TODO
  }

  copyDataOf(line: LineString): void {
    // TODO
  }

  isNearlyCircular(): boolean {
    return false; // TODO
  }

  isNearlySquare(): boolean {
    return false; // TODO
  }

  /**
   * Indicate whether this line is nearly straight.
   */ // TODO what does that mean?
  isNearlyStraight(): boolean {
    return false; // TODO
  }

  protected updateGeometry(): void {
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

  /**
   * Convert a path to a vertex index.
   * @param path The path to convert.
   * @returns The corresponding index or null if the path is malformed.
   */
  #getVertexIndex(path: string): number | null {
    const m = LineString.#PATH_PATTERN.exec(path);
    return m ? +m[1] : null;
  }
}

/**
 * A polygon is a feature that is composed of closed lines (rings), each represented by a list of {@link Point}s.
 * The ring with index 0 represents the outside perimeter of the polygon while all others represent holes.
 *
 * As such, paths must respect the following format:
 * * `"<ring>.<vertex>"`, where `<ring>` is the index of a ring
 *   and `<vertex>` is the index of the vertex/segment to target in that ring.
 *
 * Unlike {@link LineString}s, vertices cannot be added to a polygon’s rings after they have been locked.
 * A ring usually becomes locked whenever a user finished drawing it.
 */
export class Polygon extends LinearFeature<geojson.Polygon, PolygonProperties> {
  static readonly #PATH_PATTERN = /^(\d+)\.(\d+)$/;

  readonly #vertices: Point[][] = [];
  /**
   * Indicates for each ring whether it is locked (true) or not (false).
   */
  readonly #lockStatus: boolean[] = [];

  /**
   * Create a polygon.
   * @param id The feature’s ID.
   * @param vertices Optional. A list of point lists that should each contain at least 3 points.
   * It must not contain any duplicates. Each sublist represents a ring.
   * @throws {Error} If a point is present multiple times in the lists or a list contains less than 3 points.
   */
  constructor(id: string, vertices?: Point[][]) {
    super(id, {
      type: "Polygon",
      coordinates: [[]],
    }, {});
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
        this.lockRing(ringI);
      }
    } else {
      // Unlock exterior ring for later drawing
      this.#lockStatus.push(false);
    }
  }

  /**
   * This polygon’s vertices as a list of ordered streams, each stream corresponding to a ring.
   */
  get vertices(): st.Stream<Point>[] {
    return this.#vertices.map(vs => st.stream(vs));
  }

  /**
   * Indicate whether the given ring is locked.
   * @param index Index of the ring to check.
   * @returns True if the ring can no longer be modified, false if it still can or does not exist.
   */
  isRingLocked(index: number): boolean {
    return this.#lockStatus[index] ?? false;
  }

  /**
   * Lock the ring at the given index, rendering it permanently non-editable.
   * Does nothing if the ring does not exist.
   * @param index Index of the ring to lock.
   */
  lockRing(index: number): void {
    if (this.#lockStatus[index] !== undefined) {
      this.#lockStatus[index] = true;
    }
  }

  isEmpty(): boolean {
    return !this.#vertices[0] || this.#vertices[0].length === 0;
  }

  canAppendVertex(vertex: Point, path: string): boolean {
    const indices = this.#getVertexIndex(path);
    if (!this.canAcceptVertex(vertex) || indices === null || this.isRingLocked(indices[0])) {
      return false;
    }
    return indices[0] < this.#vertices.length && (indices[1] === 0 || indices[1] === this.#vertices[indices[0]].length)
        || indices[0] === this.#vertices.length && indices[1] === 0;
  }

  appendVertex(vertex: Point, path: string): void {
    if (!this.canAppendVertex(vertex, path)) {
      return;
    }
    const [ringI, vertexI] = this.#getVertexIndex(path);
    let ring: Point[];
    if (ringI === this.#vertices.length) {
      this.#vertices.push(ring = []);
      this.#lockStatus.push(false); // Make new ring drawable
    } else {
      ring = this.#vertices[ringI];
    }
    if (vertexI === 0) {
      ring.unshift(vertex);
    } else {
      ring.push(vertex);
    }
    vertex.bindFeature(this);
    this.updateGeometry();
  }

  canAcceptVertex(vertex: Point): boolean {
    return !this.#vertices.some(ring => ring.includes(vertex));
  }

  replaceVertex(newVertex: Point, oldVertex: Point): void {
    if (!this.canAcceptVertex(newVertex)) {
      return;
    }
    for (const ring of this.#vertices) {
      const i = ring.indexOf(oldVertex);
      if (i !== -1) {
        ring[i] = newVertex;
        newVertex.bindFeature(this);
        oldVertex.unbindFeature(this);
        this.updateGeometry();
        return;
      }
    }
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

  insertVertexAfter(vertex: Point, path: string): void {
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
    this.updateGeometry();
  }

  removeVertex(vertex: Point): Action {
    for (let ringI = 0; ringI < this.#vertices.length; ringI++) {
      const ring = this.#vertices[ringI];
      const i = ring.indexOf(vertex);
      if (i !== -1) {
        if (ring.length <= 3) {
          if (ringI === 0) {
            return {type: "delete_feature"};
          }
          return {type: "delete_ring", ringIndex: ringI, points: ring};
        }
        ring.splice(i, 1);
        vertex.unbindFeature(this);
        this.updateGeometry();
        return {type: "do_nothing"};
      }
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

  incrementPath(path: string): string {
    const indices = this.#getVertexIndex(path);
    if (indices !== null && indices[0] < this.#vertices.length) {
      return `${indices[0]}.${(indices[1] + 1) % this.#vertices[indices[0]].length}`;
    } else {
      return null;
    }
  }

  getSegmentPath(v1: Point, v2: Point): string | null {
    for (let ringI = 0; ringI < this.#vertices.length; ringI++) {
      const ring = this.#vertices[ringI];
      const i1 = ring.indexOf(v1);
      const i2 = ring.indexOf(v2);
      if (i1 !== -1 && i2 !== -1) {
        if (i1 === i2 - 1) {
          return "" + i1;
        } else if (i2 === i1 - 1) {
          return "" + i2;
        }
        break;
      } else if (i1 === -1 && i2 !== -1 || i1 !== -1 && i2 === -1) {
        // Vertices are not on the same ring, no need to search further
        break;
      }
    }
    return null;
  }

  getNextVertexPath(): string {
    return "0." + (this.#vertices[0]?.length ?? 0);
  }

  /**
   * Delete the ring with the given index.
   * All points of the specified rings will be unbound from this feature.
   * If the index is 0 or ≥ to the number of rings, nothing happens.
   * @param index The index of the ring to delete.
   */
  deleteRing(index: number): void {
    if (0 < index && index < this.#vertices.length) {
      this.#vertices[index].forEach(v => v.unbindFeature(this));
      this.#vertices.splice(index, 1);
      this.updateGeometry();
    }
  }

  hasData(): boolean {
    return false; // TODO
  }

  copyDataOf(polygon: Polygon): void {
    // TODO
  }

  isNearlyCircular(): boolean {
    return false; // TODO
  }

  isNearlySquare(): boolean {
    return false; // TODO
  }

  protected updateGeometry(): void {
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

  /**
   * Convert a path to ring and vertex indices.
   * @param path The path to convert.
   * @returns The corresponding ring and vertex indices or null if the path is malformed.
   */
  #getVertexIndex(path: string): [number, number] | null {
    const m = Polygon.#PATH_PATTERN.exec(path);
    return m ? [+m[1], +m[2]] : null;
  }
}
