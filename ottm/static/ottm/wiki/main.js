/**
 * Wiki script.
 */
"use strict";

(function () {
  // Apply HLJS on all tagged elements
  $(".hljs").each((_, element) => hljs.highlightElement(element));
})();
