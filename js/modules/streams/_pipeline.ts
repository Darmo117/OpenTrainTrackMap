import * as types from "./types";

/**
 * A pipeline object represents an operation to perform on the elements of a {@link types.Stream}.
 * {@link Pipeline} objects form a linked list of operations to perform
 * one after the other on each element of the {@link types.Stream} they belong to.
 */
export interface Pipeline<T> {
  /**
   * Indicate whether the total number of elements may differ before and after this {@link Pipeline} has been executed.
   */
  readonly mayChangeNumberOfElements: boolean;
  /**
   * The {@link Pipeline} that precedes this one in the operations chain.
   */
  readonly previousPipeline?: Pipeline<unknown>;

  /**
   * Return a {@link Generator} over the elements fed from the previous {@link Pipeline}.
   */
  [Symbol.iterator](): Generator<T>;

  /**
   * Close this {@link Pipeline}.
   * This clears all internal object collections that may exist
   * and renders this {@link Pipeline} unusable.
   */
  close(): void;
}

/**
 * This class is the entry point of any {@link Pipeline} chain.
 * It wraps an {@link Iterable} object and lazily iterates over its elements.
 * {@link SourcePipeline}s do not have a {@link previousPipeline} field.
 */
export class SourcePipeline<T> implements Pipeline<T> {
  readonly mayChangeNumberOfElements: boolean = false;
  /**
   * The wrapped iterable.
   */
  readonly iterable: Iterable<T>;
  /**
   * Indicate whether this pipeline has been closed.
   */
  #closed: boolean = false;

  /**
   * Create a new source pipeline for the given {@link Iterable}.
   * @param iterable An iterable object to wrap.
   */
  constructor(iterable: Iterable<T>) {
    this.iterable = iterable;
  }

  * [Symbol.iterator](): Generator<T> {
    for (const e of this.iterable) {
      if (this.#closed) {
        break;
      }
      yield e;
    }
    return null;
  }

  close(): void {
    this.#closed = true;
  }
}

/**
 * This pipeline filters out elements that do not match the specified predicate
 * and only returns the ones that do.
 */
export class FilterPipeline<T> implements Pipeline<T> {
  readonly mayChangeNumberOfElements: boolean = true;
  readonly previousPipeline: Pipeline<T>;
  /**
   * The predicate to check every value against.
   */
  readonly #predicate: (e: T) => boolean;

  /**
   * Create a new filter pipeline for the given predicate.
   * @param previousPipeline The pipeline that precedes this one.
   * @param predicate The predicate to check every value against.
   */
  constructor(previousPipeline: Pipeline<T>, predicate: (e: T) => boolean) {
    this.previousPipeline = previousPipeline;
    this.#predicate = predicate;
  }

  * [Symbol.iterator](): Generator<T> {
    for (const e of this.previousPipeline) {
      if (this.#predicate(e)) {
        yield e;
      }
    }
    return null;
  }

  close(): void {
    this.previousPipeline.close();
  }
}

/**
 * This pipeline applies the specified mapping function to each element.
 */
export class MapPipeline<T, R> implements Pipeline<R> {
  readonly mayChangeNumberOfElements: boolean = false;
  readonly previousPipeline: Pipeline<T>;
  /**
   * The function to apply to every element.
   */
  readonly #mapper: (e: T) => R;

  /**
   * Create a new map pipeline for the given mapping function.
   * @param previousPipeline The pipeline that precedes this one.
   * @param mapper The function to apply to every element.
   */
  constructor(previousPipeline: Pipeline<T>, mapper: (e: T) => R) {
    this.previousPipeline = previousPipeline;
    this.#mapper = mapper;
  }

  * [Symbol.iterator](): Generator<R> {
    for (const e of this.previousPipeline) {
      yield this.#mapper(e);
    }
    return null;
  }

  close(): void {
    this.previousPipeline.close();
  }
}

/**
 * This pipeline applies the specified mapping function to each element,
 * transforming each element into a new {@link types.Stream} object.
 */
export class FlatMapPipeline<T, R> implements Pipeline<R> {
  readonly mayChangeNumberOfElements: boolean = true;
  readonly previousPipeline: Pipeline<T>;
  /**
   * The function to apply to every element.
   */
  readonly #mapper: (e: T) => types.Stream<R>;

  /**
   * Create a new flat-map pipeline for the given mapping function.
   * @param previousPipeline The pipeline that precedes this one.
   * @param mapper The function to apply to every element.
   */
  constructor(previousPipeline: Pipeline<T>, mapper: (e: T) => types.Stream<R>) {
    this.previousPipeline = previousPipeline;
    this.#mapper = mapper;
  }

  * [Symbol.iterator](): Generator<R> {
    for (const e of this.previousPipeline) {
      yield* this.#getGenerator(e);
    }
    return null;
  }

  /**
   * Return a {@link Generator} for the given element by applying the `#mapper` function to it.
   * @param e The element to get a {@link Generator} for.
   * @returns A new {@link Generator} object.
   */
  * #getGenerator(e: T): Generator<R> {
    const stream = this.#mapper(e);
    // TODO
    return null;
  }

  close(): void {
    this.previousPipeline.close();
  }
}

/**
 * This pipeline removes all duplicate elements.
 * It keeps track of values it has already seen with a {@link Set}.
 */
export class DistinctPipeline<T> implements Pipeline<T> {
  readonly mayChangeNumberOfElements: boolean = true;
  readonly previousPipeline: Pipeline<T>;
  /**
   * A set of all values that have already been seen.
   */
  readonly #seenValues: Set<T> = new Set();

  /**
   * Create a new distinct pipeline.
   * @param previousPipeline The pipeline that precedes this one.
   */
  constructor(previousPipeline: Pipeline<T>) {
    this.previousPipeline = previousPipeline;
  }

  * [Symbol.iterator](): Generator<T> {
    for (const e of this.previousPipeline) {
      if (!this.#seenValues.has(e)) {
        this.#seenValues.add(e);
        yield e;
      }
    }
    return null;
  }

  close(): void {
    this.previousPipeline.close();
    this.#seenValues.clear();
  }
}

/**
 * This pipeline sorts all elements before iterating over them.
 * It sorts all elements in an internal {@link Array}
 * the first time its {@link Generator} is called.
 */
export class SortedPipeline<T> implements Pipeline<T> {
  readonly mayChangeNumberOfElements: boolean = false;
  readonly previousPipeline: Pipeline<T>;
  /**
   * The comparator to use to sort elements.
   */
  readonly #comparator: (a: T, b: T) => number;
  /**
   * The sorted list of all elements.
   */
  readonly #sortedValues: T[] = [];
  /**
   * Indicate whether the elements have been sorted.
   */
  #hasSorted: boolean = false;
  /**
   * Indicate whether this pipeline has been closed.
   */
  #closed: boolean = false;

  /**
   * Create a new sorted pipeline for the given comparator.
   * @param previousPipeline The pipeline that precedes this one.
   * @param comparator The comparator to use to compare elements.
   * If not specified, the `<` operator will be used instead.
   */
  constructor(previousPipeline: Pipeline<T>, comparator?: types.Comparator<T>) {
    this.previousPipeline = previousPipeline;
    this.#comparator = comparator ?? ((a: T, b: T) => {
      if (a === b) {
        return 0;
      }
      return a < b ? -1 : 1;
    });
  }

  * [Symbol.iterator](): Generator<T> {
    if (!this.#hasSorted) {
      this.#sort();
    }
    for (const e of this.#sortedValues) {
      if (this.#closed) {
        break;
      }
      yield e;
    }
    return null;
  }

  /**
   * Sort the values of the previous pipeline into `#sortedValues`.
   * It implements the insertion sort algorithm.
   */
  #sort(): void {
    this.#hasSorted = true;
    // Not using Array.sort() as it would require copying every values into an array before sorting it
    for (const e of this.previousPipeline) {
      this.#insert(e);
    }
    this.previousPipeline.close();
  }

  /**
   * Insert the given value in `#sortedValues` list, assumed to be sorted.
   * @param value The value to insert.
   */
  #insert(value: T): void {
    for (let i = 0; i < this.#sortedValues.length; i++) {
      const v = this.#sortedValues[i];
      if (this.#comparator(value, v) < 0) { // value < v
        this.#sortedValues.splice(i, 0, value);
        return;
      }
    }
    this.#sortedValues.push(value);
  }

  close(): void {
    this.previousPipeline.close();
    this.#sortedValues.splice(0);
    this.#closed = true;
  }
}

/**
 * This pipeline applies the specified function to every element, without changing them.
 */
export class PeekPipeline<T> implements Pipeline<T> {
  readonly mayChangeNumberOfElements: boolean = false;
  readonly previousPipeline: Pipeline<T>;
  /**
   * The function to apply to each element.
   */
  readonly #action: (e: T) => void;

  /**
   * Create a new peek pipeline for the given function.
   * @param previousPipeline The pipeline that precedes this one.
   * @param action The function to apply to each element.
   */
  constructor(previousPipeline: Pipeline<T>, action: (e: T) => void) {
    this.previousPipeline = previousPipeline;
    this.#action = action;
  }

  * [Symbol.iterator](): Generator<T> {
    for (const e of this.previousPipeline) {
      this.#action(e);
      yield e;
    }
    return null;
  }

  close(): void {
    this.previousPipeline.close();
  }
}

/**
 * This pipeline iterates at most over the specified number of elements.
 */
export class LimitPipeline<T> implements Pipeline<T> {
  readonly mayChangeNumberOfElements: boolean = true;
  readonly previousPipeline: Pipeline<T>;
  /**
   * The maximum number of elements to iterate over.
   */
  readonly #maxSize: number;
  /**
   * The total number of iterations.
   */
  #nbSeen: number = 0;

  /**
   * Create a new limit pipeline for the given maximum number of elements.
   * @param previousPipeline The pipeline that precedes this one.
   * @param maxSize The maximum number of elements to iterate over.
   */
  constructor(previousPipeline: Pipeline<T>, maxSize: number) {
    if (maxSize < 0) {
      throw new Error("maxSize must be >= 0");
    }
    this.previousPipeline = previousPipeline;
    this.#maxSize = maxSize;
  }

  * [Symbol.iterator](): Generator<T> {
    for (const e of this.previousPipeline) {
      if (this.#nbSeen == this.#maxSize) {
        break;
      }
      this.#nbSeen++;
      yield e;
    }
    return null;
  }

  close(): void {
    this.previousPipeline.close();
  }
}

/**
 * This pipelinee skips the first `n` elements. If there are less than `n` elements in total,
 * this pipeline returns no elements.
 */
export class SkipPipeline<T> implements Pipeline<T> {
  readonly mayChangeNumberOfElements: boolean = true;
  readonly previousPipeline: Pipeline<T>;
  /**
   * The number of elements to skip.
   */
  readonly #n: number;
  /**
   * The number of skipped elements.
   */
  #nbSkipped: number = 0;

  /**
   * Create a new skip pipeline for the given number.
   * @param previousPipeline The pipeline that precedes this one.
   * @param n The number of elements to skip over from the first one (included).
   */
  constructor(previousPipeline: Pipeline<T>, n: number) {
    if (n < 0) {
      throw new Error("n must be >= 0");
    }
    this.previousPipeline = previousPipeline;
    this.#n = n;
  }

  * [Symbol.iterator](): Generator<T> {
    for (const e of this.previousPipeline) {
      if (this.#nbSkipped >= this.#n) {
        yield e;
      }
      this.#nbSkipped++;
    }
    return null;
  }

  close(): void {
    this.previousPipeline.close();
  }
}
