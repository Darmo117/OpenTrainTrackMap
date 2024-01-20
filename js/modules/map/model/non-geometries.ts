import * as core from "./core";

export class Note {
  #author: string;
  #text: string;
}

export class Network extends core.TemporalObject {
  #relations: Relation[];
}

export class Operator extends core.TemporalObject {
}

export abstract class Relation extends core.TemporalObject {
  #networks: Network[];
}

export class Site extends Relation {
  #type: string[];
}

export class TrainLine extends Relation {
}

export class Infrastructure extends Relation {
}
