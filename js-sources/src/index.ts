/**
 * Base script for each page of the site.
 */
import $ from "jquery";
import Cookies from "js-cookie";
import "bootstrap";

import "./scss/bootstrap.scss";
import "@mdi/font/css/materialdesignicons.min.css";
import "./global.css";

import { OTTM } from "./types";
import hookExitConfirm from "./confirm-form-exit.ts";
import setupUserSettings, {
  USER_SETTINGS_FORM_SELECTOR,
} from "./user-settings";
import initMap from "./map";
import initWiki from "./wiki";

declare global {
  interface Window {
    $: typeof $;
  }
}

// Expose JQuery outside of compiled bundle
window.$ = $;

window.ottm = new OTTM();

hookSettingsDropdownBehavior();
hookDarkModeCallback();
hookLanguageSelectorCallback();

initForms();
if ($(USER_SETTINGS_FORM_SELECTOR).length !== 0) setupUserSettings();
if (window.OTTM_MAP_CONFIG) initMap();
if (window.location.pathname.startsWith("/wiki/")) initWiki();

window.ottm.setReferrer();
setAccessKeys();

/*
 * Functions
 */

function hookSettingsDropdownBehavior(): void {
  const $button = $("#navbar-logged-out-settings");
  if ($button.length) {
    const $parent = $button.parent();
    const $menu = $parent.find(".dropdown-menu");
    $button.on("click", (e) => {
      $parent.toggleClass("show");
      $menu.toggleClass("show");
      e.preventDefault();
    });
    $("body").on("click", (e) => {
      if (!$.contains($parent[0], e.target)) {
        $parent.removeClass("show");
        $menu.removeClass("show");
      }
    });
  }
}

function hookDarkModeCallback(): void {
  $("#dark-mode-checkbox").on("click", (e) => {
    Cookies.set("dark_mode", $(e.target).prop("checked") as string);
    location.reload();
  });
}

function hookLanguageSelectorCallback(): void {
  $("#nav-language-select").on("change", (e) => {
    Cookies.set("language", $(e.target).val() as string);
    location.reload();
  });
}

function initForms(): void {
  // Add .is-invalid class to form inputs with associated
  // .invalid-feedback div.
  $("form div.form-group").each((_, element) => {
    const $e = $(element);
    if ($e.find("div.invalid-feedback").length) {
      $e.find("input").addClass("is-invalid");
    }
  });

  /**
   * Create a hook that checks if both input fields have the same value each time a key is pressed.
   * @param $input1 First input field.
   * @param $input2 Second input field.
   */
  function passwordConfirm(
    $input1: JQuery<HTMLInputElement>,
    $input2: JQuery<HTMLInputElement>,
  ): void {
    function checker(): void {
      if ($input1.val() !== $input2.val()) {
        $input1.addClass("is-invalid");
        $input2.addClass("is-invalid");
      } else {
        $input1.removeClass("is-invalid");
        $input2.removeClass("is-invalid");
      }
    }

    $input1.on("keyup", checker);
    $input2.on("keyup", checker);
  }

  if (location.pathname === "/sign-up") {
    passwordConfirm(
      $("#sign-up-form-password"),
      $("#sign-up-form-password-confirm"),
    );
  } else if (location.pathname === "/user/settings") {
    passwordConfirm(
      $("#user-settings-form-password"),
      $("#user-settings-form-password-confirm"),
    );
  }

  $("form input[name='warn-unsaved']").each((_, e) => {
    hookExitConfirm($(e).closest("form"));
  });
}

/**
 * Add the shortcut to the title attribute of any element that has an access key.
 */
function setAccessKeys(): void {
  $("*[accesskey]").each((_, element) => {
    const $element = $(element);
    const accessKey = $element.attr("accesskey");
    if (accessKey) {
      const title = $element.attr("title");
      const shortcut =
        "[" + window.ottm.formatShortcut("Alt", "Shift", accessKey) + "]";
      $element.attr("title", (title ? title + " " : "") + shortcut);
    }
  });
}
