"use strict";

(function () {
  const gadgetDefs = ["`<PLACEHOLDER>`"];
  for (const gadgetDef of gadgetDefs) {
    wiki.gadgetsManager.registerGadget(gadgetDef);
  }
  wiki.gadgetsManager.finishRegistration();
})();
