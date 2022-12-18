/**
 * Script for forms.
 */
"use strict";

(function () {
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
   * @param $input1 {jQuery} First input field.
   * @param $input2 {jQuery} Second input field.
   */
  function passwordConfirm($input1, $input2) {
    function checker() {
      if ($input1.val() !== $input2.val()) {
        $input1.addClass("is-invalid");
        $input2.addClass("is-invalid");
      } else {
        $input1.removeClass("is-invalid");
        $input2.removeClass("is-invalid");
      }
    }

    $input1.keyup(checker);
    $input2.keyup(checker);
  }

  if (location.pathname === "/sign-up") {
    passwordConfirm($("#sign-up-form-password"), $("#sign-up-form-password-confirm"));
  } else if (location.pathname === "/user/settings") {
    passwordConfirm($("#user-settings-form-password"), $("#user-settings-form-password-confirm"));
  }

  $("form input[name='warn-unsaved']").each((_, element) => $(element).closest("form").confirmExit());
})();
