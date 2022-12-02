"use strict";

/**
 * Class that manages all JS interactions.
 */
class OTTM {
  /**
   * Set referer URL to login-related links.
   */
  setReferer() {
    const path = window.location.pathname + window.location.hash;
    const linkSelectors = {
      "#nav-login-link": true,
      "#nav-logout-link": false,
    };
    for (const [linkSelector, isPath] of Object.entries(linkSelectors)) {
      const $link = $(linkSelector);
      if ($link.length) {
        OTTM.#setReturnTo($link, path, isPath ? {"is_path": 1} : null);
      }
    }
    const url = $("#nav-login-link").prop("href");
    if (url) {
      const loginURL = new URL(url);
      OTTM.#setReturnTo($("#nav-signup-link"), loginURL.pathname + loginURL.search, {"is_path": 1});
    }
  }

  /**
   * Add "return_to" argument to the given link’s href attribute.
   * @param $link Link element to modify.
   * @param path {string} Path to pass to "return_to" argument.
   * @param args {Object<string, *>?} Additional arguments to append to URL.
   */
  static #setReturnTo($link, path, args) {
    const url = new URL($link.prop("href"));
    url.search = "return_to=" + encodeURIComponent(path);
    if (args) {
      url.search += "&" + $.map(Object.entries(args), e => `${e[0]}=${e[1]}`).join("&");
    }
    $link.attr("href", url.href);
  }
}

// Expose instance to global scope
window.ottm = new OTTM();
