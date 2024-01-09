export type ButtonOptions = {
  title?: string;
  icon?: Node;
  textContent?: string;
  disabled?: boolean;
  hidden?: boolean;
  className?: string;
  onClick?: (() => void);
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
    button.addEventListener("click", () => options.onClick());
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
