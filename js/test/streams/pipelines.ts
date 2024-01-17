import * as core from "../../test-framework";
import * as assert from "../../test-framework/assert";

import * as pl from "../../modules/streams/_pipeline";
import * as st from "../../modules/streams";

function source<T>(values: Iterable<T>): pl.SourcePipeline<T> {
  return new pl.SourcePipeline(values);
}

core.options.showPassed = false;

core.doTests(
    core.describe("SourcePipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("keeps original order of ordered collection", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...source(values)]);
            }),

            core.test("keeps all values of unordered collection", () => {
              let values = new Set([1, 2, 3, 4]);
              assert.setEqual(values, new Set([...source(values)]));
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = source([1, 2, 3, 4]);
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("FilterPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("filters out values that do not match the predicate", () => {
              const values = [...new pl.FilterPipeline(source([1, 2, 3, 4]), e => e > 2)];
              assert.isTrue(![1, 2].some(v => values.includes(v)));
            }),

            core.test("keeps values that match the predicate", () => {
              const values = [...new pl.FilterPipeline(source([1, 2, 3, 4]), e => e > 2)];
              assert.isTrue([3, 4].every(v => values.includes(v)));
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.FilterPipeline(source(values), () => true)]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.FilterPipeline(source([1, 2, 3, 4]), () => true);
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("MapPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("transforms values according to provided function", () => {
              const values = [...new pl.MapPipeline(source([1, 2, 3, 4]), e => e * 2)];
              assert.arrayEqual([2, 4, 6, 8], values);
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.MapPipeline(source(values), e => e)]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.MapPipeline(source([1, 2, 3, 4]), e => e);
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("FlatMapPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("flattens the given streams", () => {
              const streams = [
                st.stream([1, 2]),
                st.stream([3, 4]),
                st.stream([5, 6]),
                st.stream([7, 8]),
              ];
              const values = [...new pl.FlatMapPipeline(source([0, 1, 2, 3]), e => streams[e])];
              assert.arrayEqual([1, 2, 3, 4, 5, 6, 7, 8], values);
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.FlatMapPipeline(source(values), e => st.stream([e]))]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.FlatMapPipeline(source([1, 2, 3, 4]), e => st.stream([e]));
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("DistinctPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("removes duplicates", () => {
              const count = (v: number) => values.filter(x => x === v).length;
              const values = [...new pl.DistinctPipeline(source([1, 1, 2, 3, 4, 3]))];
              assert.isTrue(values.every(v => count(v) === 1));
            }),

            core.test("keeps only first occurence of all duplicates", () => {
              let values = [3, 1, 2, 1, 3, 4];
              assert.arrayEqual([3, 1, 2, 4], [...new pl.DistinctPipeline(source(values))]);
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.DistinctPipeline(source(values))]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.DistinctPipeline(source([1, 2, 3, 4]));
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("SortedPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("sorts values with no comparator", () => {
              const values = [...new pl.SortedPipeline(source([5, 3, 4, 6, 8, 2]))];
              assert.arrayEqual([2, 3, 4, 5, 6, 8], values);
            }),

            core.test("sorts values with comparator", () => {
              const values = [...new pl.SortedPipeline(source([5, 3, 4, 6, 8, 2]), (a, b) => b - a)];
              assert.arrayEqual([8, 6, 5, 4, 3, 2], values);
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.SortedPipeline(source(values))]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.SortedPipeline(source([1, 2, 3, 4]));
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("PeekPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("performs action on all values", () => {
              const actual: number[] = [];
              for (const _ of new pl.PeekPipeline(source([1, 2, 3, 4]), v => actual.push(v))) {
                // Do nothing
              }
              assert.arrayEqual([1, 2, 3, 4], actual);
            }),

            core.test("function does not modify values", () => {
              const values = [...new pl.PeekPipeline(source([1, 2, 3, 4]), v => v * 2)];
              assert.arrayEqual([1, 2, 3, 4], values);
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.PeekPipeline(source(values), () => {
              })]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.PeekPipeline(source([1, 2, 3, 4]), () => {
              });
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("LimitPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("returns the first n values if there are enough", () => {
              const values = [...new pl.LimitPipeline(source([1, 2, 3, 4]), 2)];
              assert.arrayEqual([1, 2], values);
            }),

            core.test("returns all values if there aren’t enough", () => {
              const values = [...new pl.LimitPipeline(source([1, 2, 3, 4]), 10)];
              assert.arrayEqual([1, 2, 3, 4], values);
            }),

            core.test("throws error if n < 0", () => {
              assert.throws(Error, () => new pl.LimitPipeline(source([1, 2, 3, 4]), -1));
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.LimitPipeline(source(values), 10)]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.LimitPipeline(source([1, 2, 3, 4]), 10);
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),

    core.describe("SkipPipeline",
        core.describe("#[Symbol.iterator]()",
            core.test("skips the first n values and returns the rest if there are enough", () => {
              const values = [...new pl.SkipPipeline(source([1, 2, 3, 4]), 2)];
              assert.arrayEqual([3, 4], values);
            }),

            core.test("returns no values if there aren’t enough", () => {
              const values = [...new pl.SkipPipeline(source([1, 2, 3, 4]), 10)];
              assert.arrayEqual([], values);
            }),

            core.test("returns all values if n = 0", () => {
              const values = [...new pl.SkipPipeline(source([1, 2, 3, 4]), 0)];
              assert.arrayEqual([1, 2, 3, 4], values);
            }),

            core.test("throws error if n < 0", () => {
              assert.throws(Error, () => new pl.SkipPipeline(source([1, 2, 3, 4]), -1));
            }),

            core.test("keeps original order of previous pipeline", () => {
              let values = [1, 2, 3, 4];
              assert.arrayEqual(values, [...new pl.SkipPipeline(source(values), 0)]);
            }),

            core.test("stops when closed", () => {
              let i = 0;
              const p = new pl.SkipPipeline(source([1, 2, 3, 4]), 0);
              for (const _ of p) {
                if (i == 2) {
                  p.close();
                }
                i++;
              }
              assert.equal(3, i);
            }),
        ),
    ),
);
