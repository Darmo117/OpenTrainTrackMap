"use strict";

(function () {
  // noinspection JSMismatchedCollectionQueryUpdate
  const gadgetDefs = ["`<PLACEHOLDER>`"];
  for (const gadgetDef of gadgetDefs) {
    ottm.wiki.gadgetsManager.registerGadget(gadgetDef);
  }
  ottm.wiki.gadgetsManager.finishRegistration();
})();
