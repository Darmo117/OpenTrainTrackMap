// noinspection JSUnusedGlobalSymbols

import {AssertionError} from ".";

/**
 * Assert that two values are equal according to the `===` operator.
 * @param expected The expected value.
 * @param actual The actual value.
 * @throws {AssertionError} If `expected !== actual`.
 */
export function equal<T>(expected: T, actual: T): void {
  if (expected !== actual) {
    throw new AssertionError(expected, actual);
  }
}

/**
 * Assert that two number values are equal to some precisionn.
 * @param expected The expected value.
 * @param actual The actual value.
 * @param delta The value under which the difference between the two values is considered 0.
 * @throws {AssertionError} If `abs(expected - actual) > delta`.
 */
export function equalDelta(expected: number, actual: number, delta: number): void {
  if (Math.abs(expected - actual) > delta) {
    throw new AssertionError(expected, actual);
  }
}

/**
 * Assert that two arrays are equal, i.e. they contain the exact same values
 * (according to the `===` operator) in the same order.
 * @param expected The expected array.
 * @param actual The actual array.
 * @throws {AssertionError} If the arrays have different lengths or there is
 * at least one index for which the values differ between the two arrays.
 */
export function arrayEqual<T>(expected: T[], actual: T[]): void {
  if (expected.length !== actual.length) {
    throw new AssertionError(`array of length ${expected.length}`, actual.length);
  }
  for (let i = 0; i < expected.length; i++) {
    const expValue = expected[i];
    const actualValue = actual[i];
    if (expValue !== actualValue) {
      throw new AssertionError(expValue, actualValue, `at index ${i}`);
    }
  }
}

/**
 * Assert that two sets are equal, i.e. they contain the exact same values
 * (according to the `===` operator).
 * @param expected The expected set.
 * @param actual The actual set.
 * @throws {AssertionError} If the sets have different size or at least one value differs between the two.
 */
export function setEqual<T>(expected: Set<T>, actual: Set<T>): void {
  if (expected.size !== actual.size) {
    throw new AssertionError(`set of size ${expected.size}`, actual.size);
  }
  if (![...expected].every(e => actual.has(e))) {
    throw new AssertionError(expected, actual);
  }
}

type Dict<T> = {
  [key: string]: T;
};

/**
 * Assert that two objects are equal, i.e. they have the exact same keys and
 * and the same key is bound to the exact same value  * (according to the `===` operator)
 * in both objects.
 * @param expected The expected object.
 * @param actual The actual object.
 * @throws {AssertionError} If the objects have different sets of keys or there is
 * at least one key for which the values differ between the two objects.
 */
export function objectEqual<T>(expected: Dict<T>, actual: Dict<T>): void {
  for (const key of Object.keys(actual)) {
    if (!expected.hasOwnProperty(key)) {
      throw new AssertionError("no key", `key "${key}"`);
    }
  }
  for (const [key, expValue] of Object.entries(expected)) {
    if (!actual.hasOwnProperty(key)) {
      throw new AssertionError(`key "${key}"`, "no key");
    }
    const actualValue = actual[key];
    if (expValue !== actualValue) {
      throw new AssertionError(expValue, actualValue, `for key "${key}"`);
    }
  }
}

/**
 * Assert that the given boolean is `true`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual !== true`.
 */
export function isTrue(actual: boolean): void {
  if (actual !== true) { // Intentional explicit value check
    throw new AssertionError(true, actual);
  }
}

/**
 * Assert that the given boolean is `false`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual !== false`.
 */
export function isFalse(actual: boolean): void {
  if (actual !== false) { // Intentional explicit value check
    throw new AssertionError(false, actual);
  }
}

/**
 * Assert that the given value is `null`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual !== null`.
 */
export function isNull(actual: any): void {
  if (actual !== null) {
    throw new AssertionError(null, actual);
  }
}

/**
 * Assert that the given value is not `null`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual === null`.
 */
export function isNotNull(actual: any): void {
  if (actual === null) {
    throw new AssertionError("not null", actual);
  }
}

/**
 * Assert that the given value is `undefined`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual !== undefined`.
 */
export function isUndefined(actual: any): void {
  if (actual !== undefined) {
    throw new AssertionError(undefined, actual);
  }
}

/**
 * Assert that the given value is not `undefined`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual === undefined`.
 */
export function isNotUndefined(actual: any): void {
  if (actual === undefined) {
    throw new AssertionError("not undefined", actual);
  }
}

/**
 * Assert that the given value is `null` or `undefined`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual !== null && actual !== undefined`.
 */
export function isNullOrUndefined(actual: any): void {
  if (actual !== null && actual !== undefined) {
    throw new AssertionError("null or undefined", actual);
  }
}

/**
 * Assert that the given value is not `null` nor `undefined`.
 * @param actual The value to check.
 * @throws {AssertionError} If `actual === null || actual === undefined`.
 */
export function isNotNullOrUndefined(actual: any): void {
  if (actual === null || actual === undefined) {
    throw new AssertionError("not null or undefined", actual);
  }
}

/**
 * Assert that the given function throws an error.
 * @param expected The expected error type.
 * @param action The function that should throw the specified error.
 * @throws {AssertionError} If the function does not throw any error or
 * throws an error whose type is different from the expected one.
 */
export function throws<E extends typeof Error>(expected: E, action: () => void): void {
  try {
    action();
  } catch (e) {
    if (e.constructor !== expected) {
      throw new AssertionError(`error of type ${expected.name}`, e.constructor.name);
    }
    return;
  }
  throw new AssertionError("error thrown", "no error");
}
