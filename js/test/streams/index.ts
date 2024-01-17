import * as core from "../../test-framework";
import * as assert from "../../test-framework/assert";

import * as st from "../../modules/streams";

core.options.showPassed = false;

core.doTests(
    core.describe("emptyStream()",
        core.test("returns a stream with no elements", () => {
          assert.arrayEqual([], st.emptyStream().toArray());
        }),
    ),

    core.describe("stream()",
        core.test("returns an ordered stream for arrays", () => {
          assert.arrayEqual([1, 2, 3, 4], st.stream([1, 2, 3, 4]).toArray());
        }),

        core.test("returns an unordered stream for sets", () => {
          const values = st.stream(new Set([1, 2, 3, 4])).toArray();
          assert.setEqual(new Set([1, 2, 3, 4]), new Set(values));
        }),
    ),

    core.describe("streamOfObject()",
        core.test("returns an unordered stream of all entries", () => {
          const o: { [k: string]: number } = {
            a: 1,
            b: 2,
          };
          const values = st.streamOfObject(o).toArray();
          assert.equal(2, values.length);
          for (const [k, v] of values) {
            assert.isTrue(o.hasOwnProperty(k));
            assert.equal(o[k], v);
          }
        }),
    ),
);
