// Add .is-invalid class to form inputs with associated
// .invalid-feedback div.
$("form div.form-group").each(function () {
  let $e = $(this);
  if ($e.find("div.invalid-feedback").length) {
    $e.find("input").addClass("is-invalid");
  }
});
