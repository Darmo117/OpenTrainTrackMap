window.ottm = {
  setReferer: function () {
    let path = window.location.pathname + window.location.hash;
    let links = [
      "#nav-login-link",
      "#nav-logout-link",
    ];
    for (let link of links) {
      let $link = $(link);
      if ($link.length) {
        let url = new URL($link.prop("href"));
        url.search = "return_to=" + encodeURIComponent(path);
        $link.attr("href", url.href);
      }
    }
  }
};
