window.ottm = {
  setReferer: function () {
    let path = window.location.pathname + window.location.hash;
    let $loginLink = $("#nav-login-link");
    let url = new URL($loginLink.prop("href"));
    url.search = "return_to=" + encodeURIComponent(path);
    $loginLink.attr("href", url.href);
  }
};
