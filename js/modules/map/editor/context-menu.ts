import * as mgl from "maplibre-gl";
import $ from "jquery";

import Map from "../map";
import * as helpers from "../controls/helpers";
import "./context-menu.css";

/**
 * Base type for button-related options.
 */
export type ButtonsMapping<T> = {
  move?: T;
  copy?: T;
  paste?: T;
  delete?: T;
  continueLine?: T;
  disconnect?: T;
  extractPoint?: T;
  split?: T;
  circularize?: T;
  square?: T;
  flipLong?: T;
  flipShort?: T;
  reverseLine?: T;
  rotate?: T;
  straightenLine?: T;
};

/**
 * Options for the {@link ContextMenu} class.
 */
export type ContextMenuOptions = {
  onMove: () => void;
  onCopy: () => void;
  onPaste: () => void;
  onDelete: () => void;
  onContinueLine: () => void;
  onDisconnect: () => void;
  onExtractPoint: () => void;
  onSplit: () => void;
  onCircularize: () => void;
  onSquare: () => void;
  onFlipLong: () => void;
  onFlipShort: () => void;
  onReverseLine: () => void;
  onRotate: () => void;
  onStraightenLine: () => void;
  moveTitle?: string;
  copyTitle?: string;
  pasteTitle?: string;
  deleteTitle?: string;
  continueLineTitle?: string;
  disconnectTitle?: string;
  extractPointTitle?: string;
  splitTitle?: string;
  circularizeTitle?: string;
  squareTitle?: string;
  flipLongTitle?: string;
  flipShortTitle?: string;
  reverseLineTitle?: string;
  rotateTitle?: string;
  straightenLineTitle?: string;
};

/**
 * Options for the {@link ContextMenu.show} method.
 */
export type ButtonStatesOptions = ButtonsMapping<boolean>;

export default class ContextMenu {
  readonly #map: mgl.Map;
  readonly #popup: mgl.Popup;
  readonly #container: HTMLElement;
  readonly #buttons: ButtonsMapping<HTMLButtonElement>;

  constructor(map: mgl.Map, options: ContextMenuOptions) {
    this.#map = map;
    this.#container = helpers.createControlContainer("map-editor-context-menu-container");
    this.#buttons = {
      move: helpers.createControlButton({
        title: (options.moveTitle ?? "Move") + " [M]",
        icon: helpers.createMdiIcon("cursor-move"),
        onClick: () => this.#performAction(options.onMove),
      }),
      copy: helpers.createControlButton({
        title: (options.copyTitle ?? "Copy") + " [Ctrl+C]",
        icon: helpers.createMdiIcon("content-copy"),
        onClick: () => this.#performAction(options.onCopy),
      }),
      paste: helpers.createControlButton({
        title: (options.pasteTitle ?? "Paste") + " [Ctrl+V]",
        icon: helpers.createMdiIcon("content-paste"),
        onClick: () => this.#performAction(options.onPaste),
      }),
      delete: helpers.createControlButton({
        title: (options.deleteTitle ?? "Delete") + " [Ctrl+Backspace]",
        icon: helpers.createMdiIcon("trash-can-outline"),
        onClick: () => this.#performAction(options.onDelete),
      }),
      continueLine: helpers.createControlButton({
        title: (options.continueLineTitle ?? "Continue Line") + " [A]",
        icon: helpers.createMdiIcon("ray-start-arrow"),
        onClick: () => this.#performAction(options.onContinueLine),
      }),
      disconnect: helpers.createControlButton({
        title: (options.disconnectTitle ?? "Disconnect") + " [D]",
        icon: helpers.createMdiIcon("pan-horizontal"),
        onClick: () => this.#performAction(options.onDisconnect),
      }),
      extractPoint: helpers.createControlButton({
        title: (options.extractPointTitle ?? "Extract Point") + " [E]",
        icon: helpers.createMdiIcon("pan-top-right"),
        onClick: () => this.#performAction(options.onExtractPoint),
      }),
      split: helpers.createControlButton({
        title: (options.splitTitle ?? "Split") + " [X]",
        icon: helpers.createMdiIcon("content-cut"),
        onClick: () => this.#performAction(options.onSplit),
      }),
      circularize: helpers.createControlButton({
        title: (options.circularizeTitle ?? "Circularize") + " [O]",
        icon: helpers.createMdiIcon("vector-circle"),
        onClick: () => this.#performAction(options.onCircularize),
      }),
      square: helpers.createControlButton({
        title: (options.squareTitle ?? "Square") + " [Q]",
        icon: helpers.createMdiIcon("vector-square"),
        onClick: () => this.#performAction(options.onSquare),
      }),
      flipLong: helpers.createControlButton({
        title: (options.flipLongTitle ?? "Flip Long") + " [T]",
        // icon: helpers.createMdiIcon(""), // TODO icon
        onClick: () => this.#performAction(options.onFlipLong),
      }),
      flipShort: helpers.createControlButton({
        title: (options.flipShortTitle ?? "Flip Short") + " [Y]",
        // icon: helpers.createMdiIcon(""), // TODO icon
        onClick: () => this.#performAction(options.onFlipShort),
      }),
      reverseLine: helpers.createControlButton({
        title: (options.reverseLineTitle ?? "Reverse Line") + " [V]",
        icon: helpers.createMdiIcon("chevron-double-left"),
        onClick: () => this.#performAction(options.onReverseLine),
      }),
      rotate: helpers.createControlButton({
        title: (options.rotateTitle ?? "Rotate") + " [R]",
        icon: helpers.createMdiIcon("rotate-left"),
        onClick: () => this.#performAction(options.onRotate),
      }),
      straightenLine: helpers.createControlButton({
        title: (options.straightenLineTitle ?? "Straighten Line") + " [S]",
        icon: helpers.createMdiIcon("ray-start-vertex-end"),
        onClick: () => this.#performAction(options.onStraightenLine),
      }),
    };
    $("body").on("keydown", e => {
      if (this.#map instanceof Map && this.#map.textFieldHasFocus) {
        return;
      }
      switch (e.key) {
        case "v":
          if (e.ctrlKey) {
            this.#performAction(options.onPaste);
          } else {
            this.#performAction(options.onReverseLine);
          }
          break;
        case "c":
          if (e.ctrlKey) {
            this.#performAction(options.onCopy);
          }
          break;
        case "m":
          this.#performAction(options.onMove);
          break;
        case "Backspace":
          if (e.ctrlKey) {
            this.#performAction(options.onDelete);
          }
          break;
        case "a":
          this.#performAction(options.onContinueLine);
          break;
        case "d":
          this.#performAction(options.onDisconnect);
          break;
        case "e":
          this.#performAction(options.onExtractPoint);
          break;
        case "x":
          this.#performAction(options.onSplit);
          break;
        case "o":
          this.#performAction(options.onCircularize);
          break;
        case "q":
          this.#performAction(options.onSquare);
          break;
        case "t":
          this.#performAction(options.onFlipLong);
          break;
        case "y":
          this.#performAction(options.onFlipShort);
          break;
        case "r":
          this.#performAction(options.onRotate);
          break;
        case "s":
          this.#performAction(options.onStraightenLine);
          break;
      }
    });
    this.#container.append(
        this.#buttons.move,
        this.#buttons.continueLine,
        this.#buttons.disconnect,
        this.#buttons.split,
        this.#buttons.circularize,
        this.#buttons.square,
        this.#buttons.flipLong,
        this.#buttons.flipShort,
        this.#buttons.reverseLine,
        this.#buttons.rotate,
        this.#buttons.straightenLine,
        this.#buttons.copy,
        this.#buttons.paste,
        this.#buttons.delete,
    );
    this.#popup = new mgl.Popup().setDOMContent(this.#container);
    this.#popup._closeButton.style.display = "none";
  }

  /**
   * Show this menu at the given coordinates on the map.
   * If all buttons are disabled, the menu will not be shown.
   * @param at The coordinates to show this menu at.
   * @param buttonStates The states of this menu’s buttons.
   * The states of each button may be either `true` to enable, `false` to disable.
   * Any disabled button will not be shown.
   */
  show(at: mgl.LngLat, buttonStates: ButtonStatesOptions = {}): void {
    this.#container.style.display = "block";
    let anyEnabled = false;
    for (const [key, button] of Object.entries(this.#buttons)) {
      const enabled = buttonStates[key as keyof ButtonStatesOptions];
      this.#setButtonState(button, enabled);
      if (enabled) {
        anyEnabled = true;
      }
    }
    if (anyEnabled) {
      this.#popup.setLngLat(at).addTo(this.#map);
      this.#popup.addClassName("map-editor-context-menu");
    }
  }

  /**
   * Hide this context menu.
   */
  hide(): void {
    this.#popup.remove();
    this.#container.style.display = "none";
    for (const button of Object.values(this.#buttons)) {
      this.#setButtonState(button, false);
    }
  }

  /**
   * Indicate whether this context menu is visible.
   * @returns True if it is, false otherwise.
   */
  isVisible(): boolean {
    return this.#popup.isOpen();
  }

  /**
   * Set the state of the given button.
   * @param button The button.
   * @param enable The state.
   */
  #setButtonState(button: HTMLButtonElement, enable: boolean): void {
    button.style.display = enable ? "block" : "none";
    button.disabled = !enable;
  }

  /**
   * Perform the specified action then hide this menu.
   * @param action The function to call.
   */
  #performAction(action: () => void): void {
    action();
    this.hide();
  }
}
