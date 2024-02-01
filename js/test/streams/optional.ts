import * as core from "../../test-framework";
import * as assert from "../../test-framework/assert";

import {Optional} from "../../modules/streams";

core.options.showPassed = false;

core.doTests(
    core.describe("Optional",
        core.describe("#empty()",
            core.test("returns an empty Optional", () => {
              assert.isTrue(Optional.empty().isEmpty());
            }),
        ),

        core.describe("#of()",
            core.test("returns an non-empty Optional", () => {
              assert.isTrue(Optional.of(1).isPresent());
            }),

            core.test("returns an Optional containing the given value", () => {
              assert.equal(1, Optional.of(1).get());
            }),

            core.test("throws an error if the value is null", () => {
              assert.throws(TypeError, () => Optional.of(null));
            }),

            core.test("throws an error if the value is undefined", () => {
              assert.throws(TypeError, () => Optional.of(null));
            }),
        ),

        core.describe("#ofNullable()",
            core.test("returns an non-empty Optional if value is not null or undefined", () => {
              assert.isTrue(Optional.ofNullable(1).isPresent());
            }),

            core.test("returns an Optional containing the given value if it is not null or undefined", () => {
              assert.equal(1, Optional.ofNullable(1).get());
            }),

            core.test("returns an empty Option if value is null", () => {
              assert.isTrue(Optional.ofNullable(null).isEmpty());
            }),

            core.test("returns an empty Option if value is undefined", () => {
              assert.isTrue(Optional.ofNullable(undefined).isEmpty());
            }),
        ),

        core.describe("#get()",
            core.test("returns an the wrapped value if it is not null or undefined", () => {
              assert.equal(1, Optional.of(1).get());
            }),

            core.test("throws an error if the value is null", () => {
              assert.throws(TypeError, () => Optional.ofNullable(null).get());
            }),

            core.test("throws an error if the value is undefined", () => {
              assert.throws(TypeError, () => Optional.ofNullable(undefined).get());
            }),
        ),

        core.describe("#isEmpty()",
            core.test("returns true the wrapped value is null", () => {
              assert.isTrue(Optional.ofNullable(null).isEmpty());
            }),

            core.test("returns true the wrapped value is undefined", () => {
              assert.isTrue(Optional.ofNullable(undefined).isEmpty());
            }),

            core.test("returns false the wrapped value is not null nor undefined", () => {
              assert.isFalse(Optional.ofNullable(1).isEmpty());
            }),
        ),

        core.describe("#isPresent()",
            core.test("returns false the wrapped value is null", () => {
              assert.isFalse(Optional.ofNullable(null).isPresent());
            }),

            core.test("returns false the wrapped value is undefined", () => {
              assert.isFalse(Optional.ofNullable(undefined).isPresent());
            }),

            core.test("returns true the wrapped value is not null nor undefined", () => {
              assert.isTrue(Optional.ofNullable(1).isPresent());
            }),
        ),

        core.describe("#ifPresent()",
            core.test("is not called when the wrapped value is null", () => {
              let witness = false;
              Optional.ofNullable(null).ifPresent(() => witness = true);
              assert.isFalse(witness);
            }),

            core.test("is not called when the wrapped value is undefined", () => {
              let witness = false;
              Optional.ofNullable(undefined).ifPresent(() => witness = true);
              assert.isFalse(witness);
            }),

            core.test("is called with the wrapped value when the it is not null nor undefined", () => {
              let witness = 0;
              Optional.ofNullable(1).ifPresent(v => witness = v);
              assert.equal(1, witness);
            }),
        ),

        core.describe("#filter()",
            core.test("returns an optional with the same value if it matches the predicate", () => {
              assert.equal(1, Optional.of(1).filter(v => v > 0).get());
            }),

            core.test("returns an empty optional if the value does not match the predicate", () => {
              assert.isTrue(Optional.of(1).filter(v => v < 0).isEmpty());
            }),
        ),

        core.describe("#map()",
            core.test("returns an optional with the mapped value if it the optional is non-empty", () => {
              assert.equal(4, Optional.of(2).map(v => v * 2).get());
            }),

            core.test("returns an empty optional if the optional is empty", () => {
              assert.isTrue(Optional.empty<number>().map(v => v * 2).isEmpty());
            }),
        ),

        core.describe("#flatMap()",
            core.test("returns an optional with the mapped value if it the optional is non-empty", () => {
              assert.equal("  ", Optional.of(2).flatMap(v => Optional.of(" ".repeat(v))).get());
            }),

            core.test("returns an empty optional if the optional is empty", () => {
              assert.isTrue(Optional.empty<number>().flatMap(v => Optional.of(" ".repeat(v))).isEmpty());
            }),
        ),

        core.describe("#or()",
            core.test("returns the inital optional if it is non-empty", () => {
              const op = Optional.of(1);
              assert.equal(op, op.or(() => Optional.of(2)));
            }),

            core.test("returns the supplied optional if it the first optional is empty", () => {
              const or = Optional.of(1);
              assert.equal(or, Optional.empty<number>().or(() => or));
            }),
        ),

        core.describe("#orElse()",
            core.test("returns the wrapped value if the optional is non-empty", () => {
              assert.equal(1, Optional.of(1).orElse(2));
            }),

            core.test("returns the provided value if the optional is empty", () => {
              assert.equal(2, Optional.empty().orElse(2));
            }),

            core.test("returns the supplied value if the optional is empty", () => {
              assert.equal(2, Optional.empty().orElse(() => 2));
            }),

            core.test("the provided supplier is not called if the optional is non-empty", () => {
              let witness = false;
              Optional.of(1).orElse(() => {
                witness = true;
                return 2;
              });
              assert.isFalse(witness);
            }),
        ),

        core.describe("#orElseThrow()",
            core.test("returns the wrapped value if the optional is non-empty", () => {
              assert.equal(1, Optional.of(1).orElseThrow(() => new Error()));
            }),

            core.test("throws the provided error if the optional is empty", () => {
              assert.throws(EvalError, () => Optional.empty().orElseThrow(() => new EvalError()));
            }),

            core.test("the provided supplier is not called if the optional is non-empty", () => {
              let witness = false;
              Optional.of(1).orElseThrow(() => {
                witness = true;
                return new Error();
              });
              assert.isFalse(witness);
            }),
        ),
    ),
);
