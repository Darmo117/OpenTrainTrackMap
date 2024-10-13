import $ from "jquery";
import { IControl, Map } from "maplibre-gl";

import { TilesSource, TilesSourceChangedEvent } from "../tiles-sources";
import "./_index.css";

/**
 * Options for the {@link GeocoderControl} class.
 */
export interface ImageryDateControlOptions {
  singleDateText?: string;
  onlyStartDateText?: string;
  onlyEndDateText?: string;
  twoDatesText?: string;
}

export default class ImageryDateControl implements IControl {
  readonly #options: ImageryDateControlOptions;
  readonly #$container: JQuery;
  readonly #$innerContainer: JQuery;

  constructor(options: ImageryDateControlOptions) {
    this.#options = { ...options };
    this.#$container = $('<div class="maplibregl-ctrl-imagery-date">');
    this.#$innerContainer = $("<span>");
    this.#$container.append(this.#$innerContainer);
  }

  #onTilesSourceChanged(source: TilesSource): void {
    const options = this.#options;
    const date = source.date;

    if (!date) this.#$container.hide();
    else {
      this.#$container.show();
      if (date.type === "date")
        this.#$innerContainer.text(
          (options.singleDateText ?? "Image date: {}").replace("{}", date.date),
        );
      else if ("start" in date && !("end" in date)) {
        this.#$innerContainer.text(
          (options.onlyStartDateText ?? "Image date: {} and after").replace(
            "{}",
            date.start,
          ),
        );
      } else if ("end" in date && !("start" in date)) {
        this.#$innerContainer.text(
          (options.onlyEndDateText ?? "Image date: {} and before").replace(
            "{}",
            date.end,
          ),
        );
      } else {
        this.#$innerContainer.text(
          (options.twoDatesText ?? "Image dates: {0} to {1}")
            .replace("{0}", date.start)
            .replace("{1}", date.end),
        );
      }
    }
  }

  onAdd(map: Map): HTMLElement {
    map.on("controls.styles.tiles_changed", (e: TilesSourceChangedEvent) => {
      this.#onTilesSourceChanged(e.source);
    });
    return this.#$container[0];
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  onRemove(): void {}
}
