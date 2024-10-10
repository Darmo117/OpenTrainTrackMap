/**
 * This snippet is loaded dynamically from ./wiki.py
 *
 * The string `<PLACEHOLDER>` will be replaced by the name of all gadgets that should be loaded for the current user.
 */
"use strict";

(function () {
  const gadgetDefs = [`<PLACEHOLDER>`];
  for (const gadgetDef of gadgetDefs)
    window.wiki.gadgetsManager.registerGadget(gadgetDef);
  window.wiki.gadgetsManager.finishRegistration();
})();
