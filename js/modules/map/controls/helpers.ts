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
 * Options that can be passed to {@link createMdiIcon}.
 */
export type MdiOptions = {
  size?: 18 | 24 | 36 | 48;
  rotate?: 45 | 90 | 135 | 180 | 225 | 270 | 315;
  flip?: "h" | "v";
  spin?: boolean;
  color?: "light" | "dark";
  inactive?: boolean;
};

/**
 * Create a span element displaying a MDI icon.
 * @param name Name of the icon without the "mdi-" prefix.
 * @param options Options to apply to the icon. Size defaults to 18px.
 */
export function createMdiIcon(name: string, options: MdiOptions = {}): HTMLElement {
  const lineIcon = document.createElement("span");
  lineIcon.className = `mdi mdi-${name} mdi-${options.size ?? 18}px`;
  if (options.rotate) {
    lineIcon.classList.add(`mdi-rotate-${options.rotate}`);
  }
  if (options.flip) {
    lineIcon.classList.add(`mdi-flip-${options.flip}`);
  }
  if (options.spin) {
    lineIcon.classList.add(`mdi-spin`);
  }
  if (options.color) {
    lineIcon.classList.add(`mdi-${options.color}`);
  }
  if (options.inactive) {
    lineIcon.classList.add(`mdi-inactive`);
  }
  return lineIcon;
}

/**
 * Create SVG element from an XML string.
 * @param string SVG data.
 * @returns The SVG element.
 */
export function parseSVG(string: string): SVGElement {
  return new DOMParser().parseFromString(string, "image/svg+xml").firstChild as SVGElement;
}
