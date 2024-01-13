/**
 * Options for the {@link createControlButton} function.
 */
export type ButtonOptions = {
  /**
   * Optional. The button’s title.
   */
  title?: string;
  /**
   * Optional. The button’s icon element.
   */
  icon?: Node;
  /**
   * Optional. The button’s text content.
   */
  textContent?: string;
  /**
   * Optional. Whether to disable the button.
   */
  disabled?: boolean;
  /**
   * Optional. Whether to hide the button.
   */
  hidden?: boolean;
  /**
   * Optional. Name of a CSS class to add to the button.
   */
  className?: string;
  /**
   * Optional. A callback to invoke whenever the button is clicked.
   */
  onClick?: ((button: HTMLButtonElement) => void);
};

/**
 * Create MapLibre control container.
 * @param className Additional class name for the container.
 * @returns A HTMLDivElement.
 */
export function createControlContainer(className: string): HTMLDivElement {
  const container = document.createElement("div");
  container.classList.add("maplibregl-ctrl", "maplibregl-ctrl-group", className);
  return container;
}

/**
 * Create a MapLibre control button.
 * @param options Button’s options.
 * @returns A HTMLButtonElement.
 */
export function createControlButton(options: ButtonOptions = {}): HTMLButtonElement {
  const button = document.createElement("button");
  if (options.title) {
    button.title = options.title;
  }
  if (options.icon) {
    button.appendChild(options.icon);
  }
  if (options.textContent) {
    button.textContent = options.textContent;
  }
  if (options.disabled) {
    button.disabled = true;
  }
  if (options.hidden) {
    button.hidden = true;
  }
  if (options.className) {
    button.classList.add(options.className);
  }
  if (options.onClick) {
    button.addEventListener("click", () => options.onClick(button));
  }
  return button;
}

/**
 * Create SVG element from an XML string.
 * @param string SVG data.
 * @returns The SVG element.
 */
export function parseSVG(string: string): SVGElement {
  return new DOMParser().parseFromString(string, "image/svg+xml").firstChild as SVGElement;
}
