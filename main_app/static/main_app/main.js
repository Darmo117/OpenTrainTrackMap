"use strict";

window.ottm = {
  setReferer: function () {
    let path = window.location.pathname + window.location.hash;
    let links = [
      ["#nav-login-link", true],
      ["#nav-logout-link", false],
    ];
    for (let [link, isPath] of links) {
      let $link = $(link);
      if ($link.length) {
        this._setReturnTo($link, path, isPath ? {"is_path": 1} : null);
      }
    }
    let url = $("#nav-login-link").prop("href");
    if (url) {
      let logInUrl = new URL(url);
      this._setReturnTo($("#nav-signup-link"), logInUrl.pathname + logInUrl.search, {"is_path": 1});
    }
  },

  /**
   *
   * @param $link
   * @param path {string}
   * @param args {Object<string, *>?}
   * @private
   */
  _setReturnTo: function ($link, path, args) {
    let url = new URL($link.prop("href"));
    url.search = "return_to=" + encodeURIComponent(path);
    if (args) {
      url.search += "&" + $.map(Object.entries(args), function (e) {
        return `${e[0]}=${e[1]}`;
      }).join("&");
    }
    $link.attr("href", url.href);
  },
};
