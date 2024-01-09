/**
 * Put the first letter to upper case and all others to lower case.
 * @param s String to capitalize.
 * @returns The capitalized string.
 */
export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

/**
 * Return a shallow copy of the given object.
 * @param o The object to copy.
 * @return The shallow copy.
 */
export function shallowCopy<O extends object>(o: O): O {
  return Object.assign({}, o);
}
