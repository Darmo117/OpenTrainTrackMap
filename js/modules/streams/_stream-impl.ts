import * as types from "./types";
import * as pl from "./_pipeline";

/**
 * Internal implementation of the {@link types.Stream} interface.
 *
 * This implementation uses a pipeline of operations, chained one after the other.
 * Each operation is only executed when a terminal operation is called.
 */
export class StreamImpl<T> implements types.Stream<T> {
  /**
   * Return a new {@link StreamImpl} for the given iterable object.
   * @param iterable The iterable to warp.
   * @returns A new {@link StreamImpl} instance.
   */
  static for<T>(iterable: Iterable<T>): StreamImpl<T> {
    return new StreamImpl<T>(iterable);
  }

  /**
   * The last operation in the pipeline.
   */
  #pipeline: pl.Pipeline<T>;

  /**
   * Create a new stream for the given {@link Iterable} or {@link pl.Pipeline} object.
   * @param iterable The object to iterate over.
   * @param isPipeline Whether the first argument is a {@link pl.Pipeline} object.
   */
  private constructor(iterable: Iterable<T> | pl.Pipeline<T>, isPipeline: boolean = false) {
    if (isPipeline) {
      this.#pipeline = iterable as pl.Pipeline<T>;
    } else {
      this.#pipeline = new pl.SourcePipeline(iterable);
    }
  }

  /*
   * Intermediate operations
   */

  filter(predicate: (e: T) => boolean): types.Stream<T> {
    this.#pipeline = new pl.FilterPipeline(this.#pipeline, predicate);
    return this;
  }

  map<R>(mapper: (e: T) => R): types.Stream<R> {
    return new StreamImpl(new pl.MapPipeline(this.#pipeline, mapper), true);
  }

  flatMap<R>(mapper: (e: T) => types.Stream<R>): types.Stream<R> {
    return new StreamImpl(new pl.FlatMapPipeline(this.#pipeline, mapper), true);
  }

  distinct(): types.Stream<T> {
    this.#pipeline = new pl.DistinctPipeline(this.#pipeline);
    return this;
  }

  sorted(comparator?: types.Comparator<T>): types.Stream<T> {
    this.#pipeline = new pl.SortedPipeline(this.#pipeline, comparator);
    return this;
  }

  peek(action: (e: T) => void): types.Stream<T> {
    this.#pipeline = new pl.PeekPipeline(this.#pipeline, action);
    return this;
  }

  limit(maxSize: number): types.Stream<T> {
    this.#pipeline = new pl.LimitPipeline(this.#pipeline, maxSize);
    return this;
  }

  skip(n: number): types.Stream<T> {
    this.#pipeline = new pl.SkipPipeline(this.#pipeline, n);
    return this;
  }

  /*
   * Terminal operations
   */

  * toGenerator(): Generator<T> {
    for (const e of this.#pipeline) {
      yield e;
    }
    this.#pipeline.close();
    return null;
  }

  forEach(action: (e: T) => void): void {
    for (const e of this.#pipeline) {
      action(e);
    }
    this.#pipeline.close();
  }

  toArray(): T[] {
    const values = [...this.#pipeline];
    this.#pipeline.close();
    return values;
  }

  reduce(identity: T, accumulator: (result: T, e: T) => T): T {
    let acc = identity;
    for (const e of this.#pipeline) {
      acc = accumulator(acc, e);
    }
    this.#pipeline.close();
    return acc;
  }

  collect<R>(supplier: () => R, accumulator: (result: R, e: T) => void): R {
    let acc = supplier();
    for (const e of this.#pipeline) {
      accumulator(acc, e);
    }
    this.#pipeline.close();
    return acc;
  }

  /**
   * The default comparator used by the {@link min} and {@link max} operations.
   * It uses the `===` and `<` operators to compares values.
   */
  private static readonly DEFAULT_COMPARATOR = (a: any, b: any) => {
    if (a === b) {
      return 0;
    }
    return a < b ? -1 : 1;
  };

  min(comparator: types.Comparator<T> = StreamImpl.DEFAULT_COMPARATOR): types.Optional<T> {
    let anyFound = false;
    let min: T = null as T;
    for (const e of this.#pipeline) {
      if (!anyFound) {
        anyFound = true;
        min = e;
      } else if (comparator(e, min) < 0) {
        min = e;
      }
    }
    return anyFound ? types.Optional.of(min) : types.Optional.empty();
  }

  max(comparator: types.Comparator<T> = StreamImpl.DEFAULT_COMPARATOR): types.Optional<T> {
    let anyFound = false;
    let max: T = null as T;
    for (const e of this.#pipeline) {
      if (!anyFound) {
        anyFound = true;
        max = e;
      } else if (comparator(e, max) > 0) {
        max = e;
      }
    }
    return anyFound ? types.Optional.of(max) : types.Optional.empty();
  }

  count(): number {
    let pipeline: pl.Pipeline<unknown> = this.#pipeline;
    // OPTIMIZATION:
    // Starting from the last pipeline, discard all that do not change the total number of elements,
    // until we find one that does or we get to the source pipeline.
    while (!(pipeline instanceof pl.SourcePipeline) && !pipeline.mayChangeNumberOfElements) {
      pipeline = pipeline.previousPipeline as pl.Pipeline<unknown>;
    }
    // OPTIMIZATION:
    // If the pipeline is the source, we check if its iterable has either a "length" or "size" property.
    // If it does, we return its value instead of iterating over its values.
    if (pipeline instanceof pl.SourcePipeline) {
      const iterable = pipeline.iterable;
      if ("length" in iterable) {
        this.#pipeline.close();
        return iterable.length as number;
      }
      if ("size" in iterable) {
        this.#pipeline.close();
        return iterable.size as number;
      }
    }
    // Iterate over the values to count.
    let count = 0;
    for (const _ of pipeline) {
      count++;
    }
    this.#pipeline.close();
    return count;
  }

  anyMatch(predicate: (e: T) => boolean): boolean {
    let anyMatch = false;
    for (const e of this.#pipeline) {
      if (predicate(e)) {
        anyMatch = true;
        break;
      }
    }
    this.#pipeline.close();
    return anyMatch;
  }

  allMatch(predicate: (e: T) => boolean): boolean {
    let allMatch = true;
    for (const e of this.#pipeline) {
      if (!predicate(e)) {
        allMatch = false;
        break;
      }
    }
    this.#pipeline.close();
    return allMatch;
  }

  noneMatch(predicate: (e: T) => boolean): boolean {
    let noneMatch = true;
    for (const e of this.#pipeline) {
      if (predicate(e)) {
        noneMatch = false;
        break;
      }
    }
    this.#pipeline.close();
    return noneMatch;
  }

  findFirst(): types.Optional<T> {
    // noinspection LoopStatementThatDoesntLoopJS
    for (const e of this.#pipeline) {
      this.#pipeline.close();
      return types.Optional.of(e);
    }
    return types.Optional.empty();
  }

  sum(): number {
    let sum = 0;
    for (const e of this.#pipeline) {
      if (typeof e !== "number") {
        this.#pipeline.close();
        throw new TypeError(`Expected number, got ${e}`);
      }
      sum += e;
    }
    this.#pipeline.close();
    return sum;
  }

  average(): types.Optional<number> {
    let sum = 0;
    let nb = 0;
    for (const e of this.#pipeline) {
      if (typeof e !== "number") {
        this.#pipeline.close();
        throw new TypeError(`Expected number, got ${e}`);
      }
      nb++;
      sum += e;
    }
    this.#pipeline.close();
    return nb !== 0 ? types.Optional.of(sum / nb) : types.Optional.empty();
  }

  join(joiner: string): string {
    let r = "";
    let first = true;
    for (const e of this.#pipeline) {
      if (first) {
        r += e;
        first = false;
      } else {
        r += joiner + e;
      }
    }
    return r;
  }
}