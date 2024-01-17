type Context = {
  type: "context";
  name: string;
  elements: Context[] | Test[];
};

type Test = {
  type: "test";
  description: string;
  action: () => void;
  disabled: boolean;
};

export const options = {
  showPassed: true,
  showIgnored: false,
  showErrorMessages: true,
};

export function doTests(...contexts: Context[]) {
  let total = 0;
  let passed = 0;
  let failed = 0;
  let ignored = 0;

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

export function describe(name: string, ...tests: Test[] | Context[]): Context {
  return {
    type: "context",
    name,
    elements: tests,
  }
}

export function test(description: string, action: () => void, disable?: boolean): Test {
  return {
    type: "test",
    description,
    action,
    disabled: disable ?? false,
  };
}

export class AssertionError extends Error {
  constructor(expected: any, actual: any, more?: any) {
    let s = `Assertion Error: expected ${expected}, got ${actual}`;
    if (more) {
      s += ` ${more}`;
    }
    super(s);
  }
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
