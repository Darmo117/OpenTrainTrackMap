import {DateInterval} from "./date-interval";

export class Note {
  private author: string;
  private text: string;
  private geometries: Geometry[];
}

// Cannot use name Node as it would conflict with default global Node interface
export interface MapNode {
  latitude(): number;

  setLatitude(lat: number): void;

  longitude(): number;

  setLongitude(lng: number): void;
}

export abstract class TemporalObject {
  protected existenceInterval: DateInterval;
  protected label: string | null;
  protected qid: string | null;
  protected sources: string | null;
  protected comment: string | null;
}

export class Network extends TemporalObject {
  protected relations: Relation[];
}

export class Operator extends TemporalObject {
}

export abstract class Relation extends TemporalObject {
  protected networks: Network[];
}

export class Site extends Relation {
}

export class TrainRoute extends Relation {
}

export class Infrastructure extends Relation {
}

export abstract class Geometry extends TemporalObject {
  protected notes: Note[];
}

export class IsolatedNode extends Geometry implements MapNode {
  private lat: number;
  private lng: number;

  latitude(): number {
    return this.lat;
  }

  longitude(): number {
    return this.lng;
  }

  setLatitude(lat: number): void {
    this.lat = lat;
  }

  setLongitude(lng: number): void {
    this.lng = lng;
  }
}

export class SignalMast extends IsolatedNode {
}

export class OverheadLinePylon extends IsolatedNode {
}

export class PointOfInterest extends IsolatedNode {
}

export class SegmentNode implements MapNode {
  private lat: number;
  private lng: number;

  latitude(): number {
    return this.lat;
  }

  longitude(): number {
    return this.lng;
  }

  setLatitude(lat: number): void {
    this.lat = lat;
  }

  setLongitude(lng: number): void {
    this.lng = lng;
  }
}

export class Polyline extends Geometry {
  protected nodes: SegmentNode[];
}

export class Polygon extends Geometry {
  protected nodes: SegmentNode[];
}

export class PolygonHole extends Polygon {
  protected parent: Polygon;
  // TODO check that parent is not a PolygonHole
}