import $ from "jquery";
import { IControl, Map } from "maplibre-gl";

import { TilesSource, TilesSourceChangedEvent } from "../tiles-sources";
import "./_index.css";

/**
 * Options for the {@link ImageryDateControl} class.
 */
export interface ImageryDateControlOptions {
  /**
   * Text to show for a single date. Should contain a {} placeholder for the date.
   */
  singleDateText?: string;
  /**
   * Text to show when only the start date is available. Should contain a {} placeholder for the date.
   */
  onlyStartDateText?: string;
  /**
   * Text to show when only the end date is available. Should contain a {} placeholder for the date.
   */
  onlyEndDateText?: string;
  /**
   * Text to show when only both start and end date are available.
   * Should contain {0} and {1} placeholders for the start and end dates respectively.
   */
  twoDatesText?: string;
}

/**
 * A control that indicates the date(s) of the current imagery.
 */
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

  onRemove(): void {
    // Nothing to do
  }
}
