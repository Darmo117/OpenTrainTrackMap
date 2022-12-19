/**
 * Script for user settings form.
 */
"use strict";

(function () {
  // Tab/URL hash synchronization
  const hash = location.hash.substring(1) || "personal-info";
  $(`#form-tab-${hash}`).addClass("active");
  $(`#form-panel-${hash}`).addClass("show active");
  $("#page-content ul[role='tablist'] button[role='tab']").on("click", e => {
    location.hash = `#${e.target.id.substring(9)}`;
  });

  // Update example time when preferred timezone selection changes
  $("#user-settings-form-preferred-timezone").on("change", e => {
    const date = new Date();
    // Convert date to selected timezone
    const localTime = ottm.formatTime(ottm.convertDateTimezone(date, $(e.target).val()));
    const $localTime = $("#local-time time");
    $localTime.text(localTime);
    $localTime.attr("datetime", localTime);
    // Convert server time to keep coherent
    const serverTime = ottm.formatTime(ottm.convertDateTimezone(date, ottm.config.get("serverTimezone")));
    const $serverTime = $("#server-time time");
    $serverTime.text(serverTime);
    $serverTime.attr("datetime", serverTime);
  });
})();
