import {Feature, LineString, Point, Polygon, Position} from "@turf/helpers";
import MapboxDraw from "@mapbox/mapbox-gl-draw";

/*
 * Events
 */

export type ValidGeometry = Point | LineString | Polygon;

type FeaturesEvent = {
  features: Feature<ValidGeometry>[];
};

export type CreateFeaturesEvent = FeaturesEvent;

export type DeleteFeaturesEvent = FeaturesEvent;

export type SelectionChangedEvent = FeaturesEvent;

export type FeatureUpdateEvent = FeaturesEvent & {
  action: "move" | "change_coordinates";
};

export type ModeChangedEvent = {
  mode: "simple_select" | "direct_select" | "draw_point" | "draw_line_string" | "draw_polygon";
};

/*
 * Editor
 */

type BoundVertex = {
  feature: Feature<ValidGeometry>;
  vertexIndex: number;
};

export class VertexBindingManager {
  #vertexBindings: {
    [featureId: string]: {
      feature: Feature<ValidGeometry>,
      [vertexIndex: number]: BoundVertex[]
    }
  } = {};
  #drawApi: MapboxDraw;

  constructor(drawApi: MapboxDraw) {
    this.#drawApi = drawApi;
  }

  bindVertices(
    feature: Feature<ValidGeometry>,
    vertexIndex: number,
    targetFeature: Feature<ValidGeometry>,
    targetVertexIndex: number
  ) {
    // Bind both ways so that vertices are correctly updated, regardless of which one is selected
    this.#doBindVertices(feature, vertexIndex, targetFeature, targetVertexIndex, true);
  }

  #doBindVertices(
    feature: Feature<ValidGeometry>,
    vertexIndex: number,
    targetFeature: Feature<ValidGeometry>,
    targetVertexIndex: number,
    bindReverseAlso: boolean
  ) {
    const newBind: BoundVertex = {feature: targetFeature, vertexIndex: targetVertexIndex};
    const id = feature.id;
    if (!this.#vertexBindings[id]) {
      this.#vertexBindings[id] = {feature, [vertexIndex]: [newBind]};
    } else if (!this.#vertexBindings[id][vertexIndex]) {
      this.#vertexBindings[id][vertexIndex] = [newBind];
    } else {
      this.#vertexBindings[id][vertexIndex].push(newBind);
    }
    if (bindReverseAlso) {
      this.#doBindVertices(targetFeature, targetVertexIndex, feature, vertexIndex, false);
    }
  }

  bindVertexToSegment(
    feature: Feature<ValidGeometry>,
    vertexIndex: number,
    targetFeature: Feature<ValidGeometry>,
    segmentIndex: number,
    segment: [Position, Position]
  ) {
    // TODO create a new point on the target feature at the snap location
  }

  /**
   * Unbind all vertices that are currently bound to the given one.
   * @param featuredId ID of the feature the vertex belongs to.
   * @param vertexIndex Vertex’s index in that feature.
   */
  unbindVertices(
    featuredId: string,
    vertexIndex: number
  ) {
    const boundVertices = this.#vertexBindings[featuredId]?.[vertexIndex];
    if (boundVertices) {
      for (const {feature, vertexIndex} of [...boundVertices]) {
        const boundVertices = this.#vertexBindings[featuredId][vertexIndex];
        // TODO
      }
    }
  }

  updateVertexCoordinates(featureId: string, vertexIndex: number, latLng: Position) {
    const [lng, lat] = latLng;
    const features = this.#vertexBindings[featureId]?.[vertexIndex];
    if (!features) {
      return;
    }

    // Update coordinates of bound vertices
    for (const {feature, vertexIndex} of features) {
      if (vertexIndex === null) {
        continue;
      }
      let position: Position;
      if (feature.geometry.type === "Point") {
        position = feature.geometry.coordinates;
      } else if (feature.geometry.type === "LineString") {
        position = feature.geometry.coordinates[vertexIndex];
      } else if (feature.geometry.type === "Polygon") {
        position = feature.geometry.coordinates[0][vertexIndex];
      }
      if (position) {
        position[0] = lng;
        position[1] = lat;
        this.#drawApi.add(feature); // Re-render feature
      }
    }
  }
}
