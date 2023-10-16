/**
 * Returns a shallow copy of the given object.
 * @param o {Object} The object to copy.
 * @return {Object} The shallow copy.
 */
function shallowCopy(o) {
  return Object.assign({}, o);
}

export {shallowCopy};
