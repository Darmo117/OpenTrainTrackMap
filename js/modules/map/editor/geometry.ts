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

  protected constructor(id: string, geometry: G, properties: Dict) {
    super(id, geometry, {width: 4, ...properties});
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

  abstract onVertexDrag(vertex: Point): void;
}

export enum PolylineDirection {
  FORWARD,
  BACKWARD,
}

export class LineString extends LinearFeature<geojson.LineString, PolylineProperties> {
  readonly #vertices: Point[] = [];
  #direction: PolylineDirection = PolylineDirection.FORWARD;

  constructor(id: string, vertices?: Point[]) {
    super(id, {
      type: "LineString",
      coordinates: [],
    }, {});
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

  get direction(): PolylineDirection {
    return this.#direction;
  }

  set direction(d: PolylineDirection) {
    this.#direction = d ?? PolylineDirection.FORWARD;
  }

  protected updateCoords() {
    this.geometry.coordinates = this.#vertices.map(p => p.geometry.coordinates);
  }

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: Point, atStart: boolean = false) {
    vertex.bindFeature(this);
    if (atStart) {
      this.#vertices.unshift(vertex);
    } else {
      this.#vertices.push(vertex);
    }
    this.updateCoords();
  }

  // TODO prevent adding the same point twice consecutively
  addVertexAt(vertex: Point, index: number) {
    vertex.bindFeature(this);
    this.#vertices.splice(index, 0, vertex);
    this.updateCoords();
  }

  removeVertex(vertex: Point) {
    if (this.#vertices.length === 2) {
      throw new Error("Cannot remove anymore point");
    }
    // FIXME vertex may appear several times
    const deleted = this.#vertices.splice(this.#vertices.indexOf(vertex), 1);
    deleted.forEach(v => v.unbindFeature(this));
    this.updateCoords();
  }

  onVertexDrag(vertex: Point) {
    const i = this.#vertices.indexOf(vertex);
    if (i >= 0) {
      const thisCoord = this.geometry.coordinates[i];
      const vCoord = vertex.geometry.coordinates;
      thisCoord[0] = vCoord[0];
      thisCoord[1] = vCoord[1];
    }
  }

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    // TODO
  }
}

export class Polygon extends LinearFeature<geojson.Polygon, PolygonProperties> {
  readonly #vertices: Point[][] = [];
  #drawing: boolean = false;

  constructor(id: string, vertices?: Point[][]) {
    super(id, {
      type: "Polygon",
      coordinates: [[]],
    }, {
      bgColor: "#ffffff80",
    });
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

  get bgColor(): string {
    return this.properties.bgColor;
  }

  set bgColor(color: string) {
    if (!color) {
      throw new Error("Missing color");
    }
    this.properties.bgColor = color;
  }

  protected updateCoords() {
    const toArray = (vertices: Point[]) => [
      ...vertices.map(v => v.geometry.coordinates),
      vertices[0].geometry.coordinates
    ];
    this.geometry.coordinates = [...this.#vertices.map(vs => toArray(vs))];
  }

  // TODO prevent adding the same point twice consecutively
  appendVertex(vertex: Point, lineIndex: number) {
    if (!this.#drawing) {
      throw new Error("Cannot append points to already drawn polygon");
    }
    if (lineIndex > this.#vertices.length) {
      throw new Error(`Line #${lineIndex} does not exist in polygon ${this.id}`)
    }
    if (lineIndex === this.#vertices.length) {
      this.#vertices.push([]);
    }
    vertex.bindFeature(this);
    this.#vertices[lineIndex].push(vertex);
    this.updateCoords();
  }

  // TODO prevent adding the same point twice consecutively
  addVertexAt(vertex: Point, index: number, lineIndex: number) {
    vertex.bindFeature(this);
    this.#vertices[lineIndex].splice(index, 0, vertex);
    this.updateCoords();
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
    this.updateCoords();
  }

  onVertexDrag(vertex: Point) {
    for (let lineI = 0; lineI < this.#vertices.length; lineI++) {
      const vertexI = this.#vertices[lineI].indexOf(vertex);
      if (vertexI >= 0) {
        const thisCoord = this.geometry.coordinates[lineI][vertexI];
        const vCoord = vertex.geometry.coordinates;
        thisCoord[0] = vCoord[0];
        thisCoord[1] = vCoord[1];
        break;
      }
    }
  }

  onDrag(e: MapMouseEvent | MapTouchEvent) {
    // TODO
  }
}
