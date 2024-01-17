/**
 * A comparator is a function that compares the values of two elements
 * and returns a number with the following meanings:
 * * `< 0`: `a` is before `b`
 * * `= 0`: `a` is equal to `b`
 * * `> 0`: `a` is after `b`
 */
export type Comparator<T> = (a: T, b: T) => number;

/**
 * A sequence of elements supporting sequential aggregate operations.
 * Elements are lazily evaluated, i.e. until a terminal operation is called
 * no element is processed.
 *
 * The methods of this interface and the doc are taken from Java 17’s Stream interface doc.
 * @see https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/stream/Stream.html
 */
export interface Stream<T> {
  /**
   * Return a stream consisting of the elements of this stream that match the given predicate.
   *
   * This is an intermediate operation.
   * @param predicate A predicate to apply to each element to determine if it should be included.
   * @returns The new stream.
   */
  filter(predicate: (e: T) => boolean): Stream<T>;

  /**
   * Return a stream consisting of the results of applying the given function to the elements of this stream.
   *
   * This is an intermediate operation.
   * @param mapper A function to apply to each element.
   * @returns The new stream.
   */
  map<R>(mapper: (e: T) => R): Stream<R>;

  /**
   * Return a stream consisting of the results of replacing each element of this stream with the contents
   * of a mapped stream produced by applying the provided mapping function to each element.
   * Each mapped stream is closed after its contents have been iterated over.
   *
   * This is an intermediate operation.
   * @param mapper A function to apply to each element which produces a stream of new values.
   * @return The new stream.
   */
  flatMap<R>(mapper: (e: T) => Stream<R>): Stream<R>;

  /**
   * Return a stream consisting of the distinct elements (according to the {@link Set.has} method) of this stream.
   *
   * For ordered streams, the selection of distinct elements is stable
   * (for duplicated elements, the element appearing first in the encounter order is preserved.)
   * For unordered streams, no stability guarantees are made.
   *
   * This is an intermediate operation.
   * @returns The new stream.
   */
  distinct(): Stream<T>;

  /**
   * Return a stream consisting of the elements of this stream,
   * sorted according to the specified comparator function.
   * If no comparator is provided, the `<` operator is used.
   * If the elements of this stream do not support this operator,
   * an {@link Error} may be thrown when the terminal operation is executed.
   *
   * This is an intermediate operation.
   * @param comparator A comparator to be used to compare the stream elements.
   * @returns The new stream.
   */
  sorted(comparator?: Comparator<T>): Stream<T>;

  /**
   * Return a stream consisting of the elements of this stream,
   * additionally performing the provided action on each element
   * as elements are consumed from the resulting stream.
   *
   * This is an intermediate operation.
   * @param action The action to perform on each element.
   * @returns The new stream.
   */
  peek(action: (e: T) => void): Stream<T>;

  /**
   * Return a stream consisting of the elements of this stream,
   * truncated to be no longer than `maxSize` in length.
   *
   * This is an intermediate operation.
   * @param maxSize The number of elements the stream should be limited to.
   * @returns The new stream.
   */
  limit(maxSize: number): Stream<T>;

  /**
   * Return a stream consisting of the remaining elements of this stream after
   * discarding the first `n` elements of the stream. If this stream contains
   * fewer than `n` elements then an empty stream will be returned.
   *
   * This is an intermediate operation.
   * @param n The number of leading elements to skip.
   * @returns The new stream.
   */
  skip(n: number): Stream<T>;

  /**
   * Return a {@link Generator} for the values of this stream.
   *
   * This is a terminal operation.
   * @returns The generator.
   */
  toGenerator(): Generator<T>;

  /**
   * Perform an action for each element of this stream.
   *
   * This is a terminal operation.
   * @param action An action to perform on the elements.
   */
  forEach(action: (e: T) => void): void;

  /**
   * Return an array containing the elements of this stream.
   *
   * This is a terminal operation.
   * @returns An array containing the elements of this stream.
   */
  toArray(): T[];

  /**
   * Perform a reduction on the elements of this stream,
   * using the provided identity value and an associative
   * accumulation function, and return the reduced value.
   *
   * This is a terminal operation.
   * @param identity The identity value for the accumulating function.
   * @param accumulator An associative function for combining two values.
   * @returns The result of the reduction.
   */
  reduce(identity: T, accumulator: (result: T, e: T) => T): T;

  /**
   * Perform a mutable reduction operation on the elements of this stream.
   * A mutable reduction is one in which the reduced value is a mutable
   * result container, such as an {@link Array} or {@link Set}, and elements
   * are incorporated by updating the state of the result rather than by
   * replacing the result.
   *
   * This is a terminal operation.
   * @param supplier A function that creates a new mutable result container.
   * @param accumulator A function that must fold an element into a result container.
   */
  collect<R>(supplier: () => R, accumulator: (result: R, e: T) => void): R;

  /**
   * Return the minimum element of this stream according to the provided comparator.
   * If no comparator is provided, the `<` is used.
   * This is a special case of a reduction.
   *
   * This is a terminal operation.
   * @param comparator A function to compare elements of this stream.
   * @returns {} An {@link Optional} describing the minimum element of this stream,
   * or an empty {@link Optional} if the stream is empty.
   * @throws {TypeError} If the minimum element is null.
   */
  min(comparator?: Comparator<T>): Optional<T>;

  /**
   * Return the maximum element of this stream according to the provided comparator.
   * If no comparator is provided, the `<` is used.
   * This is a special case of a reduction.
   *
   * This is a terminal operation.
   * @param comparator A function to compare elements of this stream.
   * @returns {} An {@link Optional} describing the maximum element of this stream,
   * or an empty {@link Optional} if the stream is empty.
   * @throws {TypeError} If the maximum element is null.
   */
  max(comparator?: Comparator<T>): Optional<T>;

  /**
   * Return the number of elements in this stream.
   * This is a special case of a reduction.
   *
   * This operation may optimize the stream to reduce
   * the number of performed operations if possible.
   *
   * This is a terminal operation.
   * @returns The number of elements in this stream.
   */
  count(): number;

  /**
   * Return whether any elements of this stream match the provided predicate.
   * May not evaluate the predicate on all elements if not necessary for determining the result.
   * If the stream is empty then `false` is returned and the predicate is not evaluated.
   *
   * This is a short-circuiting terminal operation.
   * @param predicate A predicate to apply to elements of this stream.
   * @returns True if any elements of the stream match the provided predicate, otherwise false.
   */
  anyMatch(predicate: (e: T) => boolean): boolean;

  /**
   * Return whether all elements of this stream match the provided predicate.
   * May not evaluate the predicate on all elements if not necessary for determining the result.
   * If the stream is empty then `true` is returned and the predicate is not evaluated.
   *
   * This is a short-circuiting terminal operation.
   * @param predicate A predicate to apply to elements of this stream.
   * @returns True if either all elements of the stream match the provided predicate
   * or the stream is empty, otherwise false.
   */
  allMatch(predicate: (e: T) => boolean): boolean;

  /**
   * Return whether no elements of this stream match the provided predicate.
   * May not evaluate the predicate on all elements if not necessary for
   * determining the result. If the stream is empty then `true` is returned
   * and the predicate is not evaluated.
   *
   * This is a short-circuiting terminal operation.
   * @param predicate A predicate to apply to elements of this stream.
   * @returns True if either no elements of the stream match the provided
   * predicate or the stream is empty, otherwise false.
   */
  noneMatch(predicate: (e: T) => boolean): boolean;

  /**
   * Return an {@link Optional} describing the first element of this stream,
   * or an empty {@link Optional} if the stream is empty. If the stream has
   * no encounter order, then any element may be returned.
   *
   * This is a short-circuiting terminal operation.
   * @return {} An {@link Optional} describing the first element of this stream,
   * or an empty {@link Optional} if the stream is empty.
   * @throws {TypeError} If the selected element is null.
   */
  findFirst(): Optional<T>;

  /**
   * Return the sum of elements in this stream. This is a special case of a reduction.
   *
   * This is a terminal operation.
   * @returns The sum of elements of this stream or 0 if the this stream is empty.
   * @throws {TypeError} If the elements of this stream are not numbers.
   */
  sum(): number;

  /**
   * Return a {@link Optional} describing the arithmetic mean of elements of this stream,
   * or an empty {@link Optional} if this stream is empty. This is a special case of a reduction.
   *
   * This is a terminal operation.
   * @returns {} A {@link Optional} containing the average element of this stream,
   * or an empty optional if the stream is empty.
   * @throws {TypeError} If the elements of this stream are not numbers.
   */
  average(): Optional<number>;
}

/**
 * A container object which may or may not contain a non-null-like value.
 * If a value is present, {@link isPresent()} returns true. If no value is present,
 * the object is considered empty and {@link isPresent()} returns false.
 *
 * The methods of this interface and the doc are taken from Java 17’s Optional class doc.
 * @see https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/Optional.html
 */
export class Optional<T> {
  /**
   * The singleton instance of the empty {@link Optional}.
   */
  static readonly #EMPTY: Optional<unknown> = new Optional();

  /**
   * Return an empty {@link Optional} instance.
   */
  static empty<T>(): Optional<T> {
    return this.#EMPTY as Optional<T>;
  }

  /**
   * Wrap the given value in a new {@link Optional} instance.
   * @param v The value to wrap. Must not be `null` nor `undefined`.
   * @returns A new {@link Optional} instance.
   * @throws {TypeError} If the value is `null` or `undefined`.
   */
  static of<T>(v: T): Optional<T> {
    if (v === null || v === undefined) {
      throw new TypeError("Value is null or undefined");
    }
    return new this(v);
  }

  /**
   * Wrap the given value in a new {@link Optional} instance.
   * @param v The value to wrap. May be `null` or `undefined`.
   * @returns A new {@link Optional} instance if the value is non-null,
   * an empty {@link Optional} instance otherwise.
   */
  static ofNullable<T>(v: T): Optional<T> {
    return v === null || v === undefined ? this.empty() : new this(v);
  }

  /**
   * The wrapped value.
   */
  readonly #value: T | null | undefined;

  /**
   * Create a new {@link Optional} instance for the given value.
   * @param value The value to wrap.
   */
  private constructor(value?: T | null | undefined) {
    this.#value = value;
  }

  /**
   * If a value is present, returns the value, otherwise throws an {@link Error}.
   */
  get(): T {
    if (this.isEmpty()) {
      throw new Error("Value is null or undefined");
    }
    return this.#value;
  }

  /**
   * If a value is not present, return `true`, otherwise `false`.
   */
  isEmpty(): boolean {
    return this.#value === null || this.#value === undefined;
  }

  /**
   * If a value is present, return `true`, otherwise `false`.
   */
  isPresent(): boolean {
    return !this.isEmpty();
  }

  /**
   * If a value is present, perform the given action with the value,
   * otherwise perform the given empty-based action if provided.
   * @param action The action to be performed, if a value is present.
   * @param emptyAction Optional. The empty-based action to be performed, if no value is present.
   */
  ifPresent(action: (v: T) => void, emptyAction?: () => void): void {
    if (this.isPresent()) {
      action(this.#value);
    } else {
      emptyAction?.();
    }
  }

  /**
   * If a value is present, and the value matches the given predicate,
   * return an {@link Optional} describing the value, otherwise return
   * an empty {@link Optional}.
   * @param predicate The predicate to apply to the value, if present.
   * @returns {} An {@link Optional} describing the value of this {@link Optional},
   * if a value is present and the value matches the given predicate, otherwise an
   * empty {@link Optional}.
   */
  filter(predicate: (v: T) => boolean): Optional<T> {
    return this.isPresent() && predicate(this.#value) ? this : Optional.empty();
  }

  /**
   * If a value is present, return an {@link Optional} describing
   * the result of applying the given mapping function to the value,
   * otherwise return an empty {@link Optional}.
   *
   * If the mapping function returns a null result then this method
   * returns an empty {@link Optional}.
   * @param mapper The mapping function to apply to the value, if present.
   * @returns {} An {@link Optional} describing the result of applying a
   * mapping function to the value of this {@link Optional}, if a value
   * is present, otherwise an empty {@link Optional}.
   */
  map<U>(mapper: (v: T) => U): Optional<U> {
    return this.isPresent() ? Optional.ofNullable(mapper(this.#value)) : Optional.empty();
  }

  /**
   * If a value is present, return the result of applying the given
   * {@link Optional}-bearing mapping function to the value, otherwise return
   * an empty {@link Optional}.
   * @param mapper The mapping function to apply to a value, if present.
   * @returns The result of applying an {@link Optional}-bearing mapping function
   * to the value of this Optional, if a value is present, otherwise an empty {@link Optional}.
   * @throws {TypeError} If the value returned by the function is `null` or `undefined`.
   */
  flatMap<U>(mapper: (v: T) => Optional<U>): Optional<U> {
    if (this.isEmpty()) {
      return Optional.empty();
    }
    const optional = mapper(this.#value);
    if (!optional) {
      throw new TypeError("Mapper function returned null or undefined")
    }
    return optional;
  }

  /**
   * If a value is present, return an {@link Optional} describing the value,
   * otherwise return an {@link Optional} produced by the supplying function.
   * @param supplier The supplying function that produces an {@link Optional} to be returned.
   * @returns {} An {@link Optional} describing the value of this {@link Optional},
   * if a value is present, otherwise an {@link Optional} produced by the supplying function.
   * @throws {TypeError} If the value returned by the function is `null` or `undefined`.
   */
  or(supplier: () => Optional<T>): Optional<T> {
    if (this.isPresent()) {
      return this;
    }
    const optional = supplier();
    if (!optional) {
      throw new TypeError("Supplier function returned null or undefined")
    }
    return optional;
  }

  /**
   * If a value is present, return the value, otherwise return
   * the result produced by the supplying function or value.
   * @param other The value to be returned, or a function that
   * provides the value to return, if no value is present.
   * @return The value, if present, otherwise the provided value.
   */
  orElse(other: T | (() => T)): T {
    if (this.isPresent()) {
      return this.#value;
    } else {
      return other instanceof Function ? other() : other;
    }
  }

  /**
   * If a value is present, return the value, otherwise throw the error returned by the provided supplier.
   * If no supplier is provided, an {@link Error} is thrown.
   * @param supplier Optional. A function that produces an exception to be thrown.
   * @returns The value, if present.
   * @throws {} The provided error or an {@link Error} if no value is present.
   * @throws {TypeError} If the value returned by the function is `null` or `undefined`.
   */
  orElseThrow(supplier?: () => Error): T {
    if (!this.isPresent()) {
      if (!supplier) {
        throw new Error();
      }
      const error = supplier();
      if (!error) {
        throw new TypeError("Supplier function returned null or undefined")
      }
      throw error;
    }
    return this.#value;
  }
}
