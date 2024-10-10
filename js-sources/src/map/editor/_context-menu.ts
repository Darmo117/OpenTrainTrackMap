import { LngLat, Map, Popup } from "maplibre-gl";
import $ from "jquery";

import OttmMap from "../map";
import {
  createControlButton,
  createControlContainer,
  createMdiIcon,
} from "../controls/helpers";
import "./_context-menu.css";

/**
 * Options for the {@link ContextMenu} class.
 */
export interface ContextMenuOptions {
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
}

/**
 * Options for the {@link ContextMenu.show} method.
 */
export interface ButtonStatesOptions {
  move?: boolean;
  copy?: boolean;
  paste?: boolean;
  delete?: boolean;
  continueLine?: boolean;
  disconnect?: boolean;
  extractPoint?: boolean;
  split?: boolean;
  circularize?: boolean;
  square?: boolean;
  flipLong?: boolean;
  flipShort?: boolean;
  reverseLine?: boolean;
  rotate?: boolean;
  straightenLine?: boolean;
  // TODO regularly distribute points
}

export class ContextMenu {
  readonly #map: Map;
  readonly #popup: Popup;
  readonly #container: HTMLElement;
  readonly #buttons: {
    move: HTMLButtonElement;
    copy: HTMLButtonElement;
    paste: HTMLButtonElement;
    delete: HTMLButtonElement;
    continueLine: HTMLButtonElement;
    disconnect: HTMLButtonElement;
    extractPoint: HTMLButtonElement;
    split: HTMLButtonElement;
    circularize: HTMLButtonElement;
    square: HTMLButtonElement;
    flipLong: HTMLButtonElement;
    flipShort: HTMLButtonElement;
    reverseLine: HTMLButtonElement;
    rotate: HTMLButtonElement;
    straightenLine: HTMLButtonElement;
    // TODO regularly distribute points
  };

  constructor(map: Map, options: ContextMenuOptions) {
    this.#map = map;
    this.#container = createControlContainer(
      "map-editor-context-menu-container",
    );
    this.#buttons = {
      move: createControlButton({
        title: options.moveTitle ?? "Move",
        icon: createMdiIcon("cursor-move"),
        onClick: () => {
          this.#performAction(options.onMove);
        },
        shortcut: ["M"],
      }),
      copy: createControlButton({
        title: options.copyTitle ?? "Copy",
        icon: createMdiIcon("content-copy"),
        onClick: () => {
          this.#performAction(options.onCopy);
        },
        shortcut: ["Ctrl", "C"],
      }),
      paste: createControlButton({
        title: options.pasteTitle ?? "Paste",
        icon: createMdiIcon("content-paste"),
        onClick: () => {
          this.#performAction(options.onPaste);
        },
        shortcut: ["Ctrl", "V"],
      }),
      delete: createControlButton({
        title: options.deleteTitle ?? "Delete",
        icon: createMdiIcon("trash-can-outline"),
        onClick: () => {
          this.#performAction(options.onDelete);
        },
        shortcut: ["Ctrl", "Backspace"],
      }),
      continueLine: createControlButton({
        title: options.continueLineTitle ?? "Continue Line",
        icon: createMdiIcon("ray-start-arrow"),
        onClick: () => {
          this.#performAction(options.onContinueLine);
        },
        shortcut: ["A"],
      }),
      disconnect: createControlButton({
        title: options.disconnectTitle ?? "Disconnect",
        icon: createMdiIcon("pan-horizontal"),
        onClick: () => {
          this.#performAction(options.onDisconnect);
        },
        shortcut: ["D"],
      }),
      extractPoint: createControlButton({
        title: options.extractPointTitle ?? "Extract Point",
        icon: createMdiIcon("pan-top-right"),
        onClick: () => {
          this.#performAction(options.onExtractPoint);
        },
        shortcut: ["E"],
      }),
      split: createControlButton({
        title: options.splitTitle ?? "Split",
        icon: createMdiIcon("content-cut"),
        onClick: () => {
          this.#performAction(options.onSplit);
        },
        shortcut: ["X"],
      }),
      circularize: createControlButton({
        title: options.circularizeTitle ?? "Circularize",
        icon: createMdiIcon("vector-circle"),
        onClick: () => {
          this.#performAction(options.onCircularize);
        },
        shortcut: ["O"],
      }),
      square: createControlButton({
        title: options.squareTitle ?? "Square",
        icon: createMdiIcon("vector-square"),
        onClick: () => {
          this.#performAction(options.onSquare);
        },
        shortcut: ["Q"],
      }),
      flipLong: createControlButton({
        title: options.flipLongTitle ?? "Flip Long",
        icon: createMdiIcon("dock-top"),
        onClick: () => {
          this.#performAction(options.onFlipLong);
        },
        shortcut: ["T"],
      }),
      flipShort: createControlButton({
        title: options.flipShortTitle ?? "Flip Short",
        icon: createMdiIcon("dock-left"),
        onClick: () => {
          this.#performAction(options.onFlipShort);
        },
        shortcut: ["Y"],
      }),
      reverseLine: createControlButton({
        title: options.reverseLineTitle ?? "Reverse Line",
        icon: createMdiIcon("chevron-double-left"),
        onClick: () => {
          this.#performAction(options.onReverseLine);
        },
        shortcut: ["V"],
      }),
      rotate: createControlButton({
        title: options.rotateTitle ?? "Rotate",
        icon: createMdiIcon("backup-restore"),
        onClick: () => {
          this.#performAction(options.onRotate);
        },
        shortcut: ["R"],
      }),
      straightenLine: createControlButton({
        title: options.straightenLineTitle ?? "Straighten Line",
        icon: createMdiIcon("ray-start-vertex-end"),
        onClick: () => {
          this.#performAction(options.onStraightenLine);
        },
        shortcut: ["S"],
      }),
    };
    $("body").on("keydown", (e) => {
      if (this.#map instanceof OttmMap && this.#map.textFieldHasFocus) return;
      switch (e.key) {
        case "v":
          if (e.ctrlKey) this.#performAction(options.onPaste);
          else this.#performAction(options.onReverseLine);
          break;
        case "c":
          if (e.ctrlKey) this.#performAction(options.onCopy);
          break;
        case "m":
          this.#performAction(options.onMove);
          break;
        case "Backspace":
          if (e.ctrlKey) this.#performAction(options.onDelete);
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
    this.#popup = new Popup().setDOMContent(this.#container);
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
  show(at: LngLat, buttonStates: ButtonStatesOptions = {}): void {
    this.#container.style.display = "block";
    let anyEnabled = false;
    for (const [key, button] of Object.entries(this.#buttons)) {
      const enabled = buttonStates[key as keyof ButtonStatesOptions];
      this.#setButtonState(button, !!enabled);
      if (enabled) anyEnabled = true;
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
    for (const button of Object.values(this.#buttons))
      this.#setButtonState(button, false);
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
