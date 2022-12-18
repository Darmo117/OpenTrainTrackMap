"use strict";

(function () {
  // noinspection JSMismatchedCollectionQueryUpdate
  const gadgetDefs = ["`<PLACEHOLDER>`"];
  for (const gadgetDef of gadgetDefs) {
    wiki.gadgetsManager.registerGadget(gadgetDef);
  }
  wiki.gadgetsManager.finishRegistration();
})();
