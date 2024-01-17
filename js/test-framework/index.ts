/**
 * The structure of a test context.
 */
type Context = {
  type: "context";
  name: string;
  elements: Context[] | Test[];
};

/**
 * The structure of a test definition.
 */
type Test = {
  type: "test";
  description: string;
  action: () => void;
  disabled: boolean;
};

/**
 * Options used by the {@link doTests} function.
 */
export const options = {
  /**
   * Whether to show tests that passed.
   */
  showPassed: true,
  /**
   * Whether to show tests that were ignoredd.
   */
  showIgnored: false,
  /**
   * Whether to show the error messages of tests that failed.
   */
  showErrorMessages: true,
};

/**
 * Perform the tests of all passed contexts.
 * When all tests have been executed, the number of passed, ignored and failed tests is printed.
 * @param contexts The context to execute the tests of.
 */
export function doTests(...contexts: Context[]): void {
  let total = 0;
  let passed = 0;
  let failed = 0;
  let ignored = 0;

  console.log(); // New line

  tests(contexts);

  let message = `\nFound ${total} test(s): ${passed} passing`;
  if (ignored) {
    message += `, ${ignored} ignored`
  }
  let color;
  if (failed) {
    message += `, ${failed} failing`;
    color = ANSI.colors.RED;
  } else {
    color = ANSI.colors.GREEN;
  }
  printColor(message, color);

  /**
   * Recursively execute the given contexts/tests.
   * @param contexts The array of contexts/tests to execute.
   * @param depth The current depth in the context tree.
   */
  function tests(contexts: Context[] | Test[], depth: number = 0): void {
    const indent = "  ".repeat(depth);
    for (const e of contexts) {
      if (e.type === "context") {
        console.log(indent + e.name);
        tests(e.elements, depth + 1);
      } else {
        total++;
        const desc = e.description;
        if (e.disabled) {
          if (options.showIgnored) {
            printColor(indent + "ø " + desc, ANSI.brighter(ANSI.colors.BLACK));
          }
          ignored++;
          continue;
        }
        try {
          e.action();
          if (options.showPassed) {
            printSuccess(indent + "✓ " + desc);
          }
          passed++;
        } catch (e) {
          printError(indent + "✗ " + desc);
          if (options.showErrorMessages) {
            printColor(indent + (e as Error).message, ANSI.colors.YELLOW);
          }
          failed++;
        }
      }
    }
  }
}

/**
 * Define a context for a set of tests or sub-contexts.
 * The context’s name will be shown before any of its tests or sub-contexts are executed.
 * @param name The context’s name.
 * @param tests The set of tests or sub-contexts for this context.
 */
export function describe(name: string, ...tests: Test[] | Context[]): Context {
  return {
    type: "context",
    name,
    elements: tests,
  }
}

/**
 * Define a test with a specific description and action to perform.
 * @param description The test’s description that will be shown in the results.
 * @param action The function to execute. It must throw an AssertionError if the test fails.
 * @param disable Optional. Whether to disable this test.
 */
export function test(description: string, action: () => void, disable?: boolean): Test {
  return {
    type: "test",
    description,
    action,
    disabled: disable ?? false,
  };
}

const ANSI = {
  RESET: 0,
  colors: {
    BLACK: 30,
    RED: 31,
    GREEN: 32,
    YELLOW: 33,
    BLUE: 34,
    MAGENTA: 35,
    CYAN: 36,
    WHITE: 37,
  },
  brighter: (baseColor: number) => baseColor + 60,
  escape: (code: number) => `\x1b[${code}m`,
};

function printSuccess(message: string): void {
  console.log(`${ANSI.escape(ANSI.colors.GREEN)}${message}${ANSI.escape(ANSI.RESET)}`)
}

function printError(message: string): void {
  console.log(`${ANSI.escape(ANSI.colors.RED)}${message}${ANSI.escape(ANSI.RESET)}`)
}

function printColor(message: string, color: number): void {
  console.log(`${ANSI.escape(color)}${message}${ANSI.escape(ANSI.RESET)}`)
}
