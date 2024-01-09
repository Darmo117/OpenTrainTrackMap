import {IControl, Map, StyleSpecification} from "maplibre-gl";

import {createControlButton, createControlContainer, parseSVG} from "../helpers";
import "./index.css";

const ICON = parseSVG(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="22" height="22" fill="currentColor">
  <path d="m24 41.5-18-14 2.5-1.85L24 37.7l15.5-12.05L42 27.5Zm0-7.6-18-14 18-14 18 14Zm0-15.05Zm0 11.25 13.1-10.2L24 9.7 10.9 19.9Z"/>
</svg>
`);

export type Style = {
  /**
   * Display-name of the style.
   */
  label: string;
  /**
   * Internal ID of the style.
   */
  styleId: string;
  /**
   * A MapLibre style specification object.
   */
  style: StyleSpecification;
};

export type StylesControlOptions = {
  /**
   * List of styles to show in the control.
   */
  styles: Style[];
  /**
   * A callback that will be invoked whenever the style changes.
   * @param style The clicked style.
   */
  onChange?: (style: Style) => void;
  /**
   * If true, the list of styles will only show when the control is clicked.
   */
  compact?: boolean;
  /**
   * Title of the control. Ignored if `compact` is `false`.
   */
  title?: string;
};

/**
 * A control that allows switching between multiple map styles.
 */
export default class StylesControl implements IControl {
  #map: Map;
  readonly #options: StylesControlOptions;
  readonly #container: HTMLDivElement;

  constructor(options: StylesControlOptions) {
    this.#options = {...options};
    this.#container = createControlContainer("maplibregl-ctrl-styles");
    this.#container.classList.add(
      options.compact
        ? "maplibregl-ctrl-styles-compact"
        : "maplibregl-ctrl-styles-expanded"
    );
  }

  #findStyleById(id: string): Style {
    const style = this.#options.styles.find(style => style.styleId === id);
    if (!style) {
      throw Error(`Can’t find style with ID ${id}`);
    }
    return style;
  }

  #setupExpandedView() {
    if (!this.#map) {
      throw Error("map is undefined");
    }
    const buttons: HTMLButtonElement[] = [];
    this.#options.styles.forEach(style => {
      const button = createControlButton({
        textContent: style.label,
        onClick: () => {
          if (!this.#map) {
            throw Error("map is undefined");
          }
          if (button.classList.contains("-active")) {
            return;
          }
          this.#map.setStyle(style.style);
          this.#options?.onChange(style);
        },
      });
      buttons.push(button);
      this.#container.appendChild(button);
    });

    this.#map.on("styledata", () => {
      if (!this.#map) {
        throw Error("map is undefined");
      }
      buttons.forEach((button) => {
        button.classList.remove("-active");
      });
      const styleNames = this.#options.styles.map(style => style.styleId);
      const styleName = this.#map.getStyle().name;
      if (!styleName) {
        throw Error("Style must have name");
      }
      const currentStyleIndex = styleNames.indexOf(styleName);
      if (currentStyleIndex !== -1) {
        const currentButton = buttons[currentStyleIndex];
        currentButton.classList.add("-active");
      }
    });
  }

  #setupCompactView() {
    if (!this.#map) {
      throw Error("map is undefined");
    }
    const button = createControlButton({
      title: this.#options.title ?? "Styles",
      icon: ICON,
    });
    this.#container.appendChild(button);
    // FIXME select extends outside of button
    const select = document.createElement("select");
    button.appendChild(select);

    this.#options.styles.forEach(style => {
      const option = document.createElement("option");
      select.appendChild(option);
      option.textContent = style.label;
      option.value = style.styleId;
    });

    select.addEventListener("change", () => {
      if (!this.#map) {
        throw Error("map is undefined");
      }
      const style = this.#findStyleById(select.value);
      this.#map.setStyle(style.style);
      this.#options?.onChange(style);
    });

    this.#map.on("styledata", () => {
      if (!this.#map) {
        throw Error("map is undefined");
      }
      const styleName = this.#map.getStyle().name;
      if (!styleName) {
        throw Error("Style must have name");
      }
      select.value = styleName;
    });
  }

  onAdd(map: Map): HTMLElement {
    this.#map = map;
    if (this.#options.compact) {
      this.#setupCompactView();
    } else {
      this.#setupExpandedView();
    }
    return this.#container;
  }

  onRemove() {
    this.#container.parentNode?.removeChild(this.#container);
  }
}
