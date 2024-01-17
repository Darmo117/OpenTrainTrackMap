import * as gtypes from "../types";
import * as types from "./types";
import * as impl from "./_stream-impl";

export {Stream, Optional} from "./types";

/**
 * Create an empty {@link types.Stream}.
 * @returns The new {@link types.Stream}.
 */
export function emptyStream<T>(): types.Stream<T> {
  return impl.StreamImpl.for([]);
}

/**
 * Create a {@link types.Stream} for the values of the given iterable object.
 *
 * If the iterable object is ordered, the resulting stream will be ordered.
 * @param iterable The iterable object to wrap into a {@link types.Stream}.
 * @returns The new {@link types.Stream}.
 */
export function stream<T>(iterable: Iterable<T>): types.Stream<T> {
  return impl.StreamImpl.for(iterable);
}

/**
 * Create a {@link types.Stream} that iterates over the entries of the given dictionary-like object.
 * @param o The object to wrap into a {@link types.Stream}.
 * @returns The new {@link types.Stream}.
 */
export function streamOfObject<T>(o: gtypes.Dict<T>): types.Stream<[string, T]> {
  return impl.StreamImpl.for(objectIterator(o));
}

/**
 * Generator that yields the entries of the given dictionary-like object.
 * @param o The object to iterate over.
 * @returns A generator ovre the object’s entries.
 */
function* objectIterator<T>(o: gtypes.Dict<T>): Generator<[string, T]> {
  for (const e in o) {
    if (o.hasOwnProperty(e)) {
      yield [e, o[e]];
    }
  }
}
