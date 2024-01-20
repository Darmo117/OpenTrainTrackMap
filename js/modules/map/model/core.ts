import {DateInterval} from "./date-interval";

export abstract class TemporalObject {
  #existenceInterval: DateInterval;
  #label: string | null;
  #qid: string | null;
  #sources: string | null;
  #comment: string | null;
}
