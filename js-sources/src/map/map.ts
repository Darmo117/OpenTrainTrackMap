import { Map } from "maplibre-gl";
import $ from "jquery";

/**
 * Custom subclass of {@link Map}.
 *
 * It adds a field that indicates whether a text field has the focus at any time.
 * If true, all map keyboard events should be disabled to prevent unwanted actions when the user is typing text.
 */
export default class OttmMap extends Map {
  #textFieldHasFocus = false;

  /**
   * Indicate whether a text field currently has the focus.
   */
  get textFieldHasFocus(): boolean {
    return this.#textFieldHasFocus;
  }

  /**
   * Hook events that listen to focus updates on text fields,
   * in order to update the {@link textFieldHasFocus} property.
   */
  hookTextFieldsFocusEvents(): void {
    const $textInputs = $("input[type='text'], textarea");
    $textInputs.on("focusin", () => (this.#textFieldHasFocus = true));
    $textInputs.on("focusout", () => (this.#textFieldHasFocus = false));
  }
}
