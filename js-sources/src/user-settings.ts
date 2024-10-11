import $ from "jquery";

// language=jquery-css
export const USER_SETTINGS_FORM_SELECTOR = "#user-settings";

/**
 * Sets up events on the user settings form.
 */
export default function setupUserSettings() {
  // Tab/URL hash synchronization
  const hash = location.hash.substring(1) || "personal-info";
  $(`#form-tab-${hash}`).addClass("active");
  $(`#form-panel-${hash}`).addClass("show active");
  $("#page-content ul[role='tablist'] button[role='tab']").on("click", (e) => {
    location.hash = "#" + e.target.id.substring(9);
  });

  // Update example time when preferred timezone selection changes
  $("#user-settings-form-preferred-timezone").on("change", (e) => {
    const selectedTimezone = $(e.target).val();
    if (typeof selectedTimezone !== "string") return;
    const serverTimezone = window.ottm.config.get("serverTimezone");
    if (typeof serverTimezone !== "string") return;

    const date = new Date();
    // Convert date to selected timezone
    const localTime = window.ottm.formatTime(
      window.ottm.convertDateTimezone(date, selectedTimezone),
    );
    const $localTime = $("#local-time time");
    $localTime.text(localTime);
    $localTime.attr("datetime", localTime);
    // Convert server time to stay coherent
    const serverTime = window.ottm.formatTime(
      window.ottm.convertDateTimezone(date, serverTimezone),
    );
    const $serverTime = $("#server-time time");
    $serverTime.text(serverTime);
    $serverTime.attr("datetime", serverTime);
  });
}
