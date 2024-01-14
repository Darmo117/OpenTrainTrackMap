import $ from "jquery";

/**
 * Global exit counter.
 */
let confirmExitCounter = 0;

/**
 * Add a hook to the given form that shows an alert when the user quits the page without submiting that form.
 * @param form The form to add the hook to.
 */
export default function hookExitConfirm(form: JQuery<HTMLFormElement>): void {
  const formState = {
    confirmExit: false,
    savedState: form.serialize(),
  };

  /**
   * Disables the form confirmation. If the global counter is 0,
   * the onbeforeunload event is set to null.
   */
  let disable = () => {
    if (formState.confirmExit) {
      formState.confirmExit = false;
      confirmExitCounter--;
      if (confirmExitCounter === 0) {
        window.onbeforeunload = null;
      }
    }
  };

  $("input, textarea, select", form).on("change keyup", () => {
    if (form.serialize() !== formState.savedState) {
      // Do not set the event handler if not needed
      if (!formState.confirmExit) {
        formState.confirmExit = true;
        confirmExitCounter++;

        window.onbeforeunload = function (e) {
          // For old IE and Firefox
          if (e) {
            e.returnValue = true;
          }
          return true;
        }
      }
      // Disable if already set but form is back to initial state
    } else if (formState.confirmExit) {
      disable();
    }
  });

  form.on("submit", disable);
}
