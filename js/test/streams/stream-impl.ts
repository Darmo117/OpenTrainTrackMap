import * as core from "../../test-framework";
import * as assert from "../../test-framework/assert";

import {StreamImpl} from "../../modules/streams/_stream-impl";

core.options.showPassed = false;

function stream<T>(iterable: Iterable<T>): StreamImpl<T> {
  return StreamImpl.for(iterable);
}

core.doTests(
    core.describe("StreamImpl",
        core.describe("#for()",
            core.test("returns a stream for the given iterable", () => {
              assert.arrayEqual([1, 2, 3, 4], StreamImpl.for([1, 2, 3, 4]).toArray());
            }),
        ),

        core.describe("#filter()",
            core.test("filters out values that do not match the predicate", () => {
              const values = stream([1, 2, 3, 4]).filter(e => e > 2).toArray();
              assert.isTrue(![1, 2].some(v => values.includes(v)));
            }),

            core.test("keeps values that match the predicate", () => {
              const values = stream([1, 2, 3, 4]).filter(e => e > 2).toArray();
              assert.isTrue([3, 4].every(v => values.includes(v)));
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).filter(() => true).toArray());
            }),
        ),

        core.describe("#map()",
            core.test("transforms values according to provided function", () => {
              const values = stream([1, 2, 3, 4]).map(e => e * 2).toArray();
              assert.arrayEqual([2, 4, 6, 8], values);
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).map(e => e).toArray());
            }),
        ),

        core.describe("#flatMap()",
            core.test("flattens the given streams", () => {
              const streams = [
                stream([1, 2]),
                stream([3, 4]),
                stream([5, 6]),
                stream([7, 8]),
              ];
              const values = stream([0, 1, 2, 3]).flatMap(e => streams[e]).toArray();
              assert.arrayEqual([1, 2, 3, 4, 5, 6, 7, 8], values);
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).flatMap(e => stream([e])).toArray());
            }),
        ),

        core.describe("#distinct()",
            core.test("removes duplicates", () => {
              const count = (v: number) => values.filter(x => x === v).length;
              const values = stream([1, 1, 2, 3, 4, 3]).distinct().toArray();
              assert.isTrue(values.every(v => count(v) === 1));
            }),

            core.test("keeps only first occurence of all duplicates", () => {
              let values = [3, 1, 2, 1, 3, 4];
              assert.arrayEqual([3, 1, 2, 4], stream(values).distinct().toArray());
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).distinct().toArray());
            }),
        ),

        core.describe("#sorted()",
            core.test("sorts values with no comparator", () => {
              const values = stream([5, 3, 4, 6, 8, 2]).sorted().toArray();
              assert.arrayEqual([2, 3, 4, 5, 6, 8], values);
            }),

            core.test("sorts values with comparator", () => {
              const values = stream([5, 3, 4, 6, 8, 2]).sorted((a, b) => b - a).toArray();
              assert.arrayEqual([8, 6, 5, 4, 3, 2], values);
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).sorted().toArray());
            }),
        ),

        core.describe("#peek()",
            core.test("performs action on all values", () => {
              const actual: number[] = [];
              stream([1, 2, 3, 4]).peek(v => actual.push(v)).toArray();
              assert.arrayEqual([1, 2, 3, 4], actual);
            }),

            core.test("function does not modify values", () => {
              const values = stream([1, 2, 3, 4]).peek(v => v * 2).toArray();
              assert.arrayEqual([1, 2, 3, 4], values);
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).peek(() => {
              }).toArray());
            }),
        ),

        core.describe("#limit()",
            core.test("returns the first n values if there are enough", () => {
              const values = stream([1, 2, 3, 4]).limit(2).toArray();
              assert.arrayEqual([1, 2], values);
            }),

            core.test("returns all values if there aren’t enough", () => {
              const values = stream([1, 2, 3, 4]).limit(10).toArray();
              assert.arrayEqual([1, 2, 3, 4], values);
            }),

            core.test("throws error if n < 0", () => {
              assert.throws(Error, () => stream([1, 2, 3, 4]).limit(-1));
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).limit(10).toArray());
            }),
        ),

        core.describe("#skip()",
            core.test("skips the first n values and returns the rest if there are enough", () => {
              const values = stream([1, 2, 3, 4]).skip(2).toArray();
              assert.arrayEqual([3, 4], values);
            }),

            core.test("returns no values if there aren’t enough", () => {
              const values = stream([1, 2, 3, 4]).skip(10).toArray();
              assert.arrayEqual([], values);
            }),

            core.test("returns all values if n = 0", () => {
              const values = stream([1, 2, 3, 4]).skip(0).toArray();
              assert.arrayEqual([1, 2, 3, 4], values);
            }),

            core.test("throws error if n < 0", () => {
              assert.throws(Error, () => stream([1, 2, 3, 4]).skip(-1));
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).skip(0).toArray());
            }),
        ),

        core.describe("#toGenerator()",
            core.test("yields all the values", () => {
              let nb = 0;
              for (const _ of stream([1, 2, 3, 4]).toGenerator()) {
                nb++;
              }
              assert.equal(4, nb);
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...stream(values).toGenerator()]);
            }),
        ),

        core.describe("#forEach()",
            core.test("iterates over all the values", () => {
              let nb = 0;
              stream([1, 2, 3, 4]).forEach(() => nb++);
              assert.equal(4, nb);
            }),

            core.test("keeps original order", () => {
              const values: number[] = [];
              stream([1, 2, 3, 4]).forEach(v => values.push(v));
              assert.arrayEqual([1, 2, 3, 4], values);
            }),
        ),

        core.describe("#toArray()",
            core.test("returns all the values", () => {
              let nb = 0;
              for (const _ of stream([1, 2, 3, 4]).toArray()) {
                nb++;
              }
              assert.equal(4, nb);
            }),

            core.test("keeps original order", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, stream(values).toArray());
            }),
        ),

        core.describe("#reduce()",
            core.test("reduces correctly", () => {
              assert.equal(10, stream([1, 2, 3, 4]).reduce(0, (a, b) => a + b));
            }),

            core.test("returns the identity if stream is empty", () => {
              assert.equal(0, stream<number>([]).reduce(0, (a, b) => a + b));
            }),
        ),

        core.describe("#collect()",
            core.test("reduces correctly", () => {
              const set = stream([1, 2, 3, 4]).collect(() => new Set(), (acc, e) => acc.add(e));
              assert.setEqual(new Set([1, 2, 3, 4]), set);
            }),

            core.test("returns the empty container if stream is empty", () => {
              const set = stream([]).collect(() => new Set(), (acc, e) => acc.add(e));
              assert.equal(0, set.size);
            }),
        ),

        core.describe("#min()",
            core.test("finds min with no comparator", () => {
              assert.equal(1, stream([1, 2, 3, 4]).min().get());
            }),

            core.test("finds min with comparator", () => {
              assert.arrayEqual([], stream([[], [2], [3, 4]]).min((a, b) => a.length - b.length).get());
            }),

            core.test("returns an empty optional if stream is empty", () => {
              assert.isTrue(stream([]).min().isEmpty());
            }),

            core.test("throws error if selected min is null", () => {
              assert.throws(TypeError, () => stream([null]).min());
            }),

            core.test("throws error if selected min is undefined", () => {
              assert.throws(TypeError, () => stream([undefined]).min());
            }),
        ),

        core.describe("#max()",
            core.test("finds max with no comparator", () => {
              assert.equal(4, stream([1, 2, 3, 4]).max().get());
            }),

            core.test("finds max with comparator", () => {
              assert.arrayEqual([3, 4], stream([[], [2], [3, 4]]).max((a, b) => a.length - b.length).get());
            }),

            core.test("returns an empty optional if stream is empty", () => {
              assert.isTrue(stream([]).max().isEmpty());
            }),

            core.test("throws error if selected max is null", () => {
              assert.throws(TypeError, () => stream([null]).max());
            }),

            core.test("throws error if selected max is undefined", () => {
              assert.throws(TypeError, () => stream([undefined]).max());
            }),
        ),

        core.describe("#count()",
            core.test("counts correctly", () => {
              assert.equal(4, stream([1, 2, 3, 4]).count());
            }),

            core.test("returns 0 if stream is empty", () => {
              assert.equal(0, stream([]).count());
            }),

            core.test("discards all trailing non-count-changing operations", () => {
              let witnessMap = false;
              let witnessSorted = false;
              let witnessPeek = false;
              stream([1, 2, 3, 4])
                  .filter(e => e > 2)
                  .map(e => {
                    witnessMap = true;
                    return e * 2;
                  })
                  .sorted((a, b) => {
                    witnessSorted = true;
                    return a - b;
                  })
                  .peek(() => witnessPeek = true)
                  .count();
              assert.isFalse(witnessMap);
              assert.isFalse(witnessSorted);
              assert.isFalse(witnessPeek);
            }),

            core.test("doesn’t iterate if there aren’t any count-changing operations", () => {
              class IterableMock implements Iterable<number> {
                #values: number[] = [1, 2, 3, 4];

                visited: boolean = false;

                get length(): number {
                  return this.#values.length;
                }

                * [Symbol.iterator](): Generator<number> {
                  for (const v of this.#values) {
                    this.visited = true;
                    yield v;
                  }
                }
              }

              const it = new IterableMock();
              stream(it).peek(() => null).count();
              assert.isFalse(it.visited);
            }),
        ),

        core.describe("#anyMatch()",
            core.test("returns true if any value matches predicate", () => {
              assert.isTrue(stream([1, 2, 3, 4]).anyMatch(e => e === 2));
            }),

            core.test("returns false if no value matches predicate", () => {
              assert.isFalse(stream([1, 2, 3, 4]).anyMatch(e => e === 0));
            }),

            core.test("returns false if stream is empty", () => {
              assert.isFalse(stream([]).anyMatch(e => e === 0));
            }),

            core.test("short-circuits", () => {
              let nb = 0;
              stream([1, 2, 3, 4]).anyMatch(e => {
                nb++;
                return e === 2;
              });
              assert.equal(2, nb);
            }),
        ),

        core.describe("#allMatch()",
            core.test("returns true if all values match predicate", () => {
              assert.isTrue(stream([1, 2, 3, 4]).allMatch(e => e > 0));
            }),

            core.test("returns false if any value doesn’t match predicate", () => {
              assert.isFalse(stream([1, 2, 3, 4]).allMatch(e => e === 2));
            }),

            core.test("returns true if stream is empty", () => {
              assert.isTrue(stream([]).allMatch(e => e === 0));
            }),

            core.test("short-circuits", () => {
              let nb = 0;
              stream([1, 2, 3, 4]).allMatch(e => {
                nb++;
                return e <= 2;
              });
              assert.equal(3, nb);
            }),
        ),

        core.describe("#noneMatch()",
            core.test("returns true if no values match predicate", () => {
              assert.isTrue(stream([1, 2, 3, 4]).noneMatch(e => e < 0));
            }),

            core.test("returns false if any value matches predicate", () => {
              assert.isFalse(stream([1, 2, 3, 4]).noneMatch(e => e === 2));
            }),

            core.test("returns true if stream is empty", () => {
              assert.isTrue(stream([]).noneMatch(e => e === 0));
            }),

            core.test("short-circuits", () => {
              let nb = 0;
              stream([1, 2, 3, 4]).noneMatch(e => {
                nb++;
                return e === 2;
              });
              assert.equal(2, nb);
            }),
        ),

        core.describe("#findFirst()",
            core.test("returns an Optional containing the first value if iterable is ordered", () => {
              assert.equal(1, stream([1, 2, 3, 4]).findFirst().get());
            }),

            core.test("returns an Optional containing a value of iterable if it is unordered", () => {
              const iterable = new Set([1, 2, 3, 4]);
              assert.isTrue(iterable.has(stream(iterable).findFirst().get()));
            }),

            core.test("returns an empty Optional if stream is empty", () => {
              assert.isTrue(stream([]).findFirst().isEmpty());
            }),
        ),

        core.describe("#sum()",
            core.test("returns the sum of numbers in the stream", () => {
              assert.equal(10, stream([1, 2, 3, 4]).sum());
            }),

            core.test("returns 0 if the stream is empty", () => {
              assert.equal(0, stream([]).sum());
            }),

            core.test("throws an error if the stream contains a non-number value", () => {
              assert.throws(TypeError, () => stream([1, "b"]).sum());
            }),
        ),

        core.describe("#average()",
            core.test("returns an Optional containing the average of numbers in the stream", () => {
              assert.equalDelta(2.5, stream([1, 2, 3, 4]).average().get(), 1e-10);
            }),

            core.test("returns an empty Optional if the stream is empty", () => {
              assert.isTrue(stream([]).average().isEmpty());
            }),

            core.test("throws an error if the stream contains a non-number value", () => {
              assert.throws(TypeError, () => stream([1, "b"]).average());
            }),
        ),

        core.describe("#join()",
            core.test("joins the values in the stream", () => {
              assert.equal("a,b,c,d", stream(["a", "b", "c", "d"]).join(","));
            }),

            core.test("converts values to strings", () => {
              assert.equal("1,null,undefined,[object Object]", stream([1, null, undefined, {}]).join(","));
            }),

            core.test("returns an empty string if the stream is empty", () => {
              assert.equal("", stream([]).join(","));
            }),
        ),
    ),
);
