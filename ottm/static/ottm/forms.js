// Add .is-invalid class to form inputs with associated
// .invalid-feedback div.
$("form div.form-group").each((_, element) => {
  const $e = $(element);
  if ($e.find("div.invalid-feedback").length) {
    $e.find("input").addClass("is-invalid");
  }
});

$("form #form-password").each((_, element) => {

});
