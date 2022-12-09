"use strict";

/**
 * Class that manages all JS interactions.
 */
class OTTM {
  constructor() {
    this.setReferer();
    this.setAccessKeys();
  }

  /**
   * Add the shortcut to the title attribute of any element that has an access key.
   */
  setAccessKeys() {
    $("*[accesskey]").each((_, element) => {
      const $element = $(element);
      const accessKey = $element.attr("accesskey");
      if (accessKey) {
        const title = $element.attr("title");
        const shortcut = `[Alt+Shift+${accessKey}]`;
        $element.attr("title", (title ? title + " " : "") + shortcut);
      }
    });
  }

  /**
   * Set referer URL to login-related links.
   */
  setReferer() {
    const path = window.location.pathname + window.location.hash;
    const linkSelectors = [
      "#nav-login-link",
      "#nav-logout-link",
      "#nav-signup-link",
    ];
    for (const linkSelector of linkSelectors) {
      const $link = $(linkSelector);
      if ($link.length) {
        OTTM.setReturnTo($link, path);
      }
    }
  }

  /**
   * Add "return_to" argument to the given link’s href attribute.
   * @param $link Link element to modify.
   * @param path {string} Path to pass to "return_to" argument.
   * @param args {Object<string, *>?} Additional arguments to append to URL.
   */
  static setReturnTo($link, path, args) {
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
