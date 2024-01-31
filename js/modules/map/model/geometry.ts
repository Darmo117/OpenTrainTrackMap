import * as mgl from "maplibre-gl";
import * as geojson from "geojson";
import * as turf from "@turf/turf";

import * as st from "../../streams";
import * as utils from "../utils";
import * as dtypes from "./data-types"

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
export type LineStringProperties = LinearProperties & {
  width: number;
  dash: number[] | null;
  fgColor: string;
  fgWidth: number;
  fgDash: number[] | null;
};
export type PolygonProperties = LinearProperties;

/**
 * A function that provides the given data type for a name and type string.
 */
export type DataTypeProvider =
    (typeName: string, metaType: "UnitType" | "Enum" | "ObjectType") => dtypes.UnitType | dtypes.Enum | dtypes.ObjectType;

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
  id: string = null;

  /**
   * This feature’s database ID. Null if this feature does not exist in the database yet.
   */
  readonly dbId: number | null;
  // Using # seems to mess up things
  private dataObject_: dtypes.ObjectInstance | null = null;
  private readonly dataTypesProvider: DataTypeProvider;

  /**
   * Create a new map feature.
   * @param dataTypesProvider A function that provides the given data type for a name and type string.
   * @param geometry The feature’s geometry object.
   * @param dbId The feature’s database ID.
   * @param layer The z-order layer index.
   * @param dataObject The attached object containing data. May be null.
   * @throws {TypeError} If the data object’s geometry type is incompatible with this geometry.
   */
  protected constructor(
      dataTypesProvider: DataTypeProvider,
      geometry: G,
      dbId?: number,
      layer?: number,
      dataObject?: dtypes.ObjectInstance,
  ) {
    this.dbId = dbId;
    this.geometry = geometry;
    this.properties = {
      color: "#ffffff",
      layer: 0,
      selectionMode: SelectionMode.NONE,
    } as P;
    this.dataTypesProvider = dataTypesProvider;
    if (dataObject) {
      const expectedGeomType = this.geometry.type;
      const actualGeomType = dataObject.type.getGeometryType();
      if (actualGeomType !== expectedGeomType) {
        throw new TypeError(`Invalid data object geometry type: expected "${expectedGeomType}", got "${actualGeomType}"`);
      }
      this.dataObject_ = dataObject;
    }
    this.layer = layer ?? 0;
  }

  get dataObject(): dtypes.ObjectInstance | null {
    return this.dataObject_;
  }

  /**
   * This feature’s color.
   */
  get color(): string {
    return this.properties.color;
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
   * Copy the data of the given feature.
   * If the feature does not have a data object, nothing happens.
   * @param feature The feature to copy the data of.
   */
  copyDataOf(feature: MapFeature<G, P>): void {
    if (!feature.dataObject) {
      return;
    }
    const expectedGeomType = this.geometry.type;
    const actualGeomType = feature.dataObject.type.getGeometryType();
    if (expectedGeomType !== actualGeomType) {
      throw new TypeError(`Invalid geometry type: expected "${expectedGeomType}", got "${actualGeomType}"`);
    }
    this.dataObject_ = feature.dataObject;
    this.updateProperties();
  }

  /**
   * Update this feature’s `properties` field.
   */
  abstract updateProperties(): void;

  /**
   * Get the {@link dtypes.UnitType} for the given name.
   * @param name The type’s name.
   * @returns The corresponding type.
   */
  protected getUnitType(name: string): dtypes.UnitType {
    return this.dataTypesProvider(name, "UnitType") as dtypes.UnitType;
  }

  /**
   * Get the {@link dtypes.Enum} for the given name.
   * @param name The enum’s name.
   * @returns The corresponding enum.
   */
  protected getEnum(name: string): dtypes.Enum {
    return this.dataTypesProvider(name, "Enum") as dtypes.Enum;
  }

  /**
   * Get the {@link dtypes.ObjectType} for the given name.
   * @param name The type’s name.
   * @returns The corresponding type.
   */
  protected getObjectType(name: string): dtypes.ObjectType {
    return this.dataTypesProvider(name, "ObjectType") as dtypes.ObjectType;
  }
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
   * @param dataTypesProvider A function that provides the given data type for a name and type string.
   * @param coords The point’s coordinates.
   * @param dbId The feature’s database ID.
   * @param layer The z-order layer index.
   * @param dataObject The attached object containing data.
   */
  constructor(
      dataTypesProvider: DataTypeProvider,
      coords: mgl.LngLat,
      dbId?: number,
      layer?: number,
      dataObject?: dtypes.ObjectInstance
  ) {
    super(dataTypesProvider, {
      type: "Point",
      coordinates: null, // Updated immediately by this.lngLat()
    }, dbId, layer, dataObject);
    this.lngLat = coords;
    this.updateProperties();
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
    this.updateGeometry();
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
    this.updateProperties();
  }

  /**
   * Unbind this point from the given feature.
   * @param feature The feature to unbind this point from.
   */
  unbindFeature(feature: LinearFeature) {
    this.#boundFeatures.delete(feature);
    this.updateProperties();
  }

  /**
   * Called when this point is dragged on the map.
   * @param mousePos The mouse location.
   * @param offset The offset between the mouse position and this point’s current position.
   */
  onDrag(mousePos: mgl.LngLat, offset: LngLatVector = LngLatVector.ZERO): void {
    this.#lngLat = offset.addTo(mousePos);
    this.updateGeometry();
  }

  /**
   * Update this point’s `geometry.coordinates` and `geometry.bbox` properties.
   * Also calls the {@link LinearFeature.onVertexDrag} method on all bound features.
   */
  protected updateGeometry(): void {
    this.geometry.coordinates = this.#lngLat.toArray();
    const {lng, lat} = this.#lngLat;
    this.geometry.bbox = [lng, lat, lng, lat];
    this.#boundFeatures.forEach(f => f.onVertexDrag(this));
  }

  updateProperties() {
    this.properties.color = this.#boundFeatures.size > 1 ? "#bbbbbb" : "#ffffff";
    if (this.dataObject) {
      this.properties.radius = 6;
    } else if (this.#boundFeatures.size === 0
        || this.#boundFeatures.size === 1
        && this.boundFeatures.allMatch(f => f instanceof LineString && f.isEndVertex(this))) {
      this.properties.radius = 5;
    } else {
      this.properties.radius = 3.5;
    }
    // TODO set icon depending on objectData’s type
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
   * Check whether this feature can accept the given vertex anywhere or at the given path.
   * @param vertex The vertex to check.
   * @param at The path where the vertex may be accepted, or null to check if the vertex may be accepted anywhere.
   * @returns True if this feature is accepted, false otherwise.
   */
  abstract canAcceptVertex(vertex: Point, at?: string): boolean

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
   * Return the path of the given vertex.
   * @param v The vertex to get the path of.
   * @returns The path for the vertex or null if it is not present in this feature.
   */
  abstract getVertexPath(v: Point): string | null;

  /**
   * Return the path to the next possible vertex position on this feature’s outer line.
   */
  abstract getNextVertexPath(): string;

  /**
   * Called when one of the vertices of this feature is being dragged.
   * @param draggedVertex The vertex being dragged.
   */
  onVertexDrag(draggedVertex: Point): void {
    this.updateGeometry(draggedVertex);
  }

  static readonly CIRCULARITY_THRESHOLD: number = 0.6;

  /**
   * Indicate whether a ring of this feature is nearly circular.
   *
   * The circularity coefficient is derived from the formula by Cox (1927).
   * @param ringIndex The index of the ring.
   * @returns True if the circularity coefficient of the ring is greater than or equal to 0.6, false otherwise.
   * @see Cox, E. P. (1927). A Method of Assigning Numerical and Percentage Values to the Degree
   *  of Roundness of Sand Grains. Journal of Paleontology, 1(3), 179–183. http://www.jstor.org/stable/1298056
   * @throws {Error} If the index is invalid.
   */
  isNearlyCircular(ringIndex: number): boolean {
    return 4 * Math.PI * this.getArea(ringIndex) / (this.getPerimeter(ringIndex) ** 2) >= LinearFeature.CIRCULARITY_THRESHOLD;
  }

  /**
   * Calculate the area of the region enclosed by the given closed ring.
   * @param ringIndex The index of the ring.
   * @returns The area of the region.
   * @throws {Error} If the index is invalid.
   */
  getArea(ringIndex: number): number {
    return getPolygonArea(this.getRing(ringIndex));
  }

  /**
   * Calculate the perimeter of the given closed ring.
   * @param ringIndex The index of the ring.
   * @returns The perimeter of the ring.
   * @throws {Error} If the index is invalid.
   */
  getPerimeter(ringIndex: number): number {
    return getPolygonPerimeter(this.getRing(ringIndex));
  }

  static readonly RIGHT_ANGLE_THRESHOLD: number = 5;

  /**
   * Indicate whether the given ring of this feature is nearly square,
   * i.e. all its angles are nearly a multiple of 90°.
   * @param ringIndex The index of the ring.
   * @returns True if all angles at each vertex is a multiple of 90° ± 5°, false otherwise.
   * @throws {Error} If the index is invalid.
   */
  isNearlySquare(ringIndex: number): boolean {
    const ring = this.getRing(ringIndex);
    for (let i = 0; i < ring.length; i++) {
      const vPrev = i == 0 ? ring[ring.length - 1] : ring[i - 1];
      const vCurr = ring[i];
      const vNext = i == ring.length - 1 ? ring[0] : ring[i + 1];
      const angle = turf.angle(vPrev, vCurr, vNext, {mercator: true}) % 90;
      const t = LinearFeature.RIGHT_ANGLE_THRESHOLD;
      if (angle > t && angle < 90 - t) {
        return false;
      }
    }
    return true;
  }

  /**
   * Return the vertices of the ring at the given index.
   * @param index The index of the ring.
   * @returns The vertices of the given ring.
   * @throws {Error} If the index is invalid.
   */
  protected abstract getRing(index: number): Point[];

  /**
   * Update this feature’s `geometry.coordinates` and `geometry.bbox` properties.
   * @param draggedVertex If specified, the dragged vertex that induced this operation.
   */
  protected abstract updateGeometry(draggedVertex?: Point): void;
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
 */
export class LineString extends LinearFeature<geojson.LineString, LineStringProperties> {
  static readonly #PATH_PATTERN = /^(\d+)$/;

  readonly #vertices: Point[] = [];
  #direction: PolylineDirection = PolylineDirection.FORWARD;

  /**
   * Create a line string.
   * @param dataTypesProvider A function that provides the given data type for a name and type string.
   * @param vertices Optional. A list of (at least 2) points. It must not contain any duplicates.
   * @param dbId The feature’s database ID.
   * @param layer The z-order layer index.
   * @param dataObject The attached object containing data.
   * @throws {Error} If a point is present multiple times in the list of points or the list contains less than 2 points.
   */
  constructor(
      dataTypesProvider: DataTypeProvider,
      vertices?: Point[],
      dbId?: number,
      layer?: number,
      dataObject?: dtypes.ObjectInstance
  ) {
    super(dataTypesProvider, {
      type: "LineString",
      coordinates: [],
    }, dbId, layer, dataObject);
    if (vertices) {
      if (vertices.length < 2) {
        throw new Error(`Expected at least 2 points, got ${vertices.length} in linestring ${dbId}`);
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
    this.updateProperties();
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

  canAcceptVertex(vertex: Point, at?: string): boolean {
    const i = this.#vertices.indexOf(vertex);
    if (i === -1) {
      return true;
    }
    if (!at || this.isLoop()) {
      return false;
    }
    const atI = this.#getVertexIndex(at);
    if (atI === null
        || Math.abs(i - atI) <= 2) { // Cannot accept if vertices have not at least two other vertices in-between
      return false;
    }
    const lastI = this.#vertices.length - 1;
    // Allow first vertex to snap to last vertex and vice-versa
    return i === 0 && atI === lastI || i === lastI && atI === 0;
  }

  replaceVertex(newVertex: Point, oldVertex: Point): void {
    if (!this.canAcceptVertex(newVertex, this.getVertexPath(oldVertex))) {
      return;
    }
    // Replace everywhere
    let i = this.#vertices.indexOf(oldVertex);
    do {
      this.#vertices[i] = newVertex;
      i = this.#vertices.indexOf(oldVertex);
    } while (i !== -1);
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
    let i = this.#vertices.indexOf(vertex);
    if (i !== -1) {
      if (this.#vertices.length <= 2 || this.isLoop() && this.#vertices.length === 3) {
        return {type: "delete_feature"};
      }
      // Vertex may be present twice if this is a loop
      do {
        this.#vertices.splice(i, 1).length
        i = this.#vertices.indexOf(vertex);
      } while (i !== -1)
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

  getVertexPath(v: Point): string | null {
    const i = this.#vertices.indexOf(v);
    return i !== null ? "" + i : null;
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
    if (this.isLoop()) {
      return false;
    }
    const i = this.#vertices.indexOf(v);
    return i === 0 || i === this.#vertices.length - 1;
  }

  /**
   * Indicate whether this line forms a loop, i.e. it has more than one vertex
   * and its first and last vertex are the same.
   */
  isLoop(): boolean {
    return this.#vertices.length > 1 && this.#vertices[0] === this.#vertices[this.#vertices.length - 1];
  }

  getArea(ringIndex: number): number {
    if (!this.isLoop()) {
      throw new Error("LineString is not a loop");
    }
    return super.getArea(ringIndex);
  }

  getPerimeter(ringIndex: number): number {
    if (!this.isLoop()) {
      throw new Error("LineString is not a loop");
    }
    return super.getPerimeter(ringIndex);
  }

  protected getRing(index: number): Point[] {
    if (index !== 0) {
      throw new Error(`Invalid ring index: ${index}`);
    }
    // Discard last vertex
    return this.#vertices.slice(0, this.#vertices.length - 1);
  }

  /**
   * Indicate whether this line is nearly straight.
   */ // TODO what does that mean?
  isNearlyStraight(): boolean {
    return false; // TODO
  }

  protected updateGeometry(draggedVertex?: Point): void {
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
    if (draggedVertex) {
      draggedVertex.updateProperties();
    } else {
      this.#vertices.forEach(v => v.updateProperties());
    }
  }

  updateProperties() {
    if (!this.dataObject) {
      this.properties.width = 2;
      this.properties.color = "#ffffff";
      this.properties.dash = null;
      this.properties.fgColor = "#ffffff";
      this.properties.fgWidth = 0;
      this.properties.fgDash = null;

    } else {
      if (this.dataObject.isInstanceOf(this.getObjectType("track_section"))) {
        this.properties.width = 6;
        if (this.dataObject.isInstanceOf(this.getObjectType("conventional_track_section"))) {
          const gauge = this.dataObject.getPropertyValue<number>("gauge");
          if (gauge !== null && gauge >= 1435) {
            this.properties.width = 8;
          }
        }
        this.properties.dash = null;
        this.properties.fgWidth = 2;
        this.properties.fgDash = [4, 4];
        let color: string;
        switch (this.dataObject.getPropertyValue("level")) {
          case "bridge":
            color = "#131313";
            break;
          case "tunnel":
            color = "#9b9b9b";
            break;
          case "surface":
          default:
            color = "#3d3d3d";
            break;
        }
        this.properties.color = color;
        this.properties.fgColor = "#ffffff";
      }
    }
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
   * @param dataTypesProvider A function that provides the given data type for a name and type string.
   * @param vertices Optional. A list of point lists that should each contain at least 3 points.
   * It must not contain any duplicates. Each sublist represents a ring.
   * @param dbId The feature’s database ID.
   * @param layer The z-order layer index.
   * @param dataObject The attached object containing data.
   * @throws {Error} If a point is present multiple times in the lists or a list contains less than 3 points.
   */
  constructor(
      dataTypesProvider: DataTypeProvider,
      vertices?: Point[][],
      dbId?: number,
      layer?: number,
      dataObject?: dtypes.ObjectInstance
  ) {
    super(dataTypesProvider, {
      type: "Polygon",
      coordinates: [[]],
    }, dbId, layer, dataObject);
    if (vertices) {
      // Separate loop to avoid binding vertices unnecessarily
      for (let i = 0; i < vertices.length; i++) {
        const ring = vertices[i];
        if (ring.length < 3) {
          throw new Error(`Expected at least 3 points, got ${ring.length} in ring ${i} of polygon ${dbId}`);
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
        ring.forEach(v => v.updateProperties()); // Refresh properties of all vertices
      }
    } else {
      // Unlock exterior ring for later drawing
      this.#lockStatus.push(false);
    }
    this.updateProperties();
  }

  /**
   * This polygon’s vertices as an ordered stream of ordered streams, each stream corresponding to a ring.
   * The first stream is always the outermost one.
   */
  get vertices(): st.Stream<st.Stream<Point>> {
    return st.stream(this.#vertices.map(vs => st.stream(vs)));
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

  getVertexPath(v: Point): string | null {
    for (let ringI = 0; ringI < this.#vertices.length; ringI++) {
      const i = this.#vertices[ringI].indexOf(v);
      if (i !== -1) {
        return `${ringI}.${i}`;
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

  protected getRing(index: number): Point[] {
    const ring = this.#vertices[index];
    if (!ring) {
      throw new Error(`Invalid ring index: ${index}`);
    }
    return [...ring];
  }

  protected updateGeometry(draggedVertex?: Point): void {
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
    if (draggedVertex) {
      draggedVertex.updateProperties();
    } else {
      this.#vertices.forEach(ring => ring.forEach(v => v.updateProperties()));
    }
  }

  updateProperties() {
    // TODO
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

/**
 * Notes are used to leave comments on geometries.
 */
export class Note {
  readonly #date: Date;
  /**
   * The username of the author that wrote this note.
   */
  readonly authorName: string;
  /**
   * This note’s text.
   */
  readonly text: string;
  readonly #geometries: MapFeature[] = [];

  /**
   * Create a new note.
   * @param date The date the note was published on.
   * @param authorName The username of the author that wrote the note.
   * @param text The note’s text.
   * @param geometries The geometries the note is linked to.
   */
  constructor(date: Date, authorName: string, text: string, geometries: MapFeature[]) {
    this.#date = date;
    this.authorName = authorName;
    this.text = text;
    this.#geometries = [...geometries];
  }

  /**
   * The date this note was published on.
   */
  get date(): Date {
    return new Date(this.#date.getTime());
  }

  /**
   * The geometries this note is linked to.
   * @returns A stream of all geometries this note is linked to.
   */
  get geometries(): st.Stream<MapFeature> {
    return st.stream(this.#geometries);
  }
}

/**
 * Calculate the area of the polygon formed by the given array of {@link Point}.
 * @param vertices The array of vertices, without repeating the first one at the end.
 * @returns The area of the polygon.
 */
export function getPolygonArea(vertices: Point[]): number {
  return turf.area(toPolygon(vertices));
}

/**
 * Calculate the perimeter of the polygon formed by the given array of {@link Point}.
 * @param vertices The array of vertices, without repeating the first one at the end.
 * @returns The perimeter of the polygon.
 */
export function getPolygonPerimeter(vertices: Point[]): number {
  return turf.lineDistance(toPolygon(vertices), {units: "meters"});
}

/**
 * Convert an array of {@link Point}s to a Turf polygon feature.
 * @param vertices The array of vertices, without repeating the first one at the end.
 * @returns A Turf polygon feature.
 */
function toPolygon(vertices: Point[]): turf.Feature<turf.Polygon> {
  return turf.polygon([[...vertices, vertices[0]].map(v => v.lngLat.toArray())]);
}
