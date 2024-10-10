/**
 * Put the first letter to upper case and all others to lower case.
 * @param s String to capitalize.
 * @returns The capitalized string.
 */
export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}
