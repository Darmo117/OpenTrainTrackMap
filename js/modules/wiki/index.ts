import * as types from "../types";
import initEditor from "./editor";

type GadgetCode = {
  name: string;
  version?: string;
  init: () => void;
  run: () => void;
};

/**
 * Base class for wiki gadgets.
 */
export class WikiGadget {
  /** This gadget’s name. */
  readonly name: string;
  /** This gadget’s version. */
  readonly version: string | undefined;
  /** The actual gadget object. */
  readonly #code: GadgetCode;

  /**
   * Create a new gadget.
   * @param code The actual gadget object.
   * @throws Error If the passed object is malformed or the object’s init() function threw an error.
   */
  constructor(code: GadgetCode) {
    if (!code.hasOwnProperty("name")) {
      throw new Error("Missing \"name\" property in gadget");
    }
    this.name = code.name;
    this.version = code.version;
    this.#code = code;
    this.#code.init();
  }

  /**
   * Called when this gadget has been initialized and the manager is ready.
   * @returns True if the gadget was run successfully, false if any error occurred.
   */
  run(): boolean {
    try {
      this.#code.run();
    } catch (e) {
      console.error(e);
      return false;
    }
    return true;
  }
}

/**
 * This class manages wiki gadgets.
 */
export class WikiGadgetManager {
  /** Mapping of all successfully loaded gadgets. */
  readonly #gadgets: types.Dict<WikiGadget> = {};
  /** Number of gadgets still loading. */
  #gadgetsQueueSize: number = 0;
  /** Whether all gadgets have been registered. */
  #finishedRegistration: boolean = false;
  /** Whether this manager is locked. Once locked, no more gadgets can be registered. */
  #locked: boolean = false;

  /**
   * Register a gadget to be loaded asynchronously.
   * @param gadgetName The gadget’s name.
   * @throws Error If this manager is locked.
   */
  registerGadget(gadgetName: string) {
    if (this.#locked) {
      throw new Error("Cannot register gadgets when manager is locked");
    }
    console.log(`Registering gadget "${gadgetName}…"`);
    this.#gadgetsQueueSize++;
    const apiPath = window.ottm.config.get("wApiPath");
    $.get(
      apiPath,
      {
        action: "query",
        query: "gadget",
        title: gadgetName,
      },
      data => {
        try {
          const gadget = new WikiGadget(eval(data));
          this.#gadgets[gadget.name] = gadget;
        } catch (e) {
          console.error(`Error while loading gadget "${gadgetName}":\n${e}`);
        }
        this.#gadgetsQueueSize--;
        if (this.#gadgetsQueueSize === 0 && this.#finishedRegistration) {
          this.#lock();
        }
      }
    );
  }

  /**
   * Indicate that gadgets registration is finished.
   * If the loading queue is already empty, lock this manager immediately.
   */
  finishRegistration() {
    this.#finishedRegistration = true;
    if (this.#gadgetsQueueSize === 0) {
      this.#lock();
    }
  }

  /**
   * Lock this manager after all gadgets have been loaded.
   */
  #lock() {
    this.#locked = true;
  }

  /**
   * Return the gadget with the given name.
   * @param name Gadget’s name.
   * @return The gadget or undefined if none matched.
   */
  getGadget(name: string): WikiGadget | undefined {
    return this.#gadgets[name];
  }

  /**
   * Check whether the given gadget is registered.
   * @param name Gadget name to check.
   * @return True if a gadget with the specified name is registered, false otherwise.
   */
  isGadgetRegistered(name: string): boolean {
    return this.#gadgets[name] !== undefined;
  }
}

/**
 * @param content Current page content.
 * @return The new content or an object with additional parameters.
 */
export type PageContentTransformer = (content: string) => (string | {
  content: string,
  summary?: string,
  minor?: boolean,
  hidden?: boolean,
  follow?: boolean,
});

/**
 * An object returned by the {@link WikiAPI.editPage} method.
 */
export type PageEditResponse = {
  success: boolean;
  errorMessage?: string;
};

/**
 * This class provides methods to interact with the wiki’s HTTP API.
 */
export class WikiAPI {
  /**
   * Edit a wiki page.
   * @param title Page’s title.
   * @param transformer Function to apply to the page’s current content.
   * @return A promise returning the server’s response as a {@link PageEditResponse} object.
   */
  editPage(title: string, transformer: PageContentTransformer): Promise<PageEditResponse> {
    // TODO
    return null;
  }

  /**
   * Get the content of the given page.
   * @param title Page’s title.
   * @return A promise returning the page’s wikicode.
   */
  getPage(title: string): Promise<string> {
    // TODO
    return null;
  }

  /**
   * Get the list of categories of the given page.
   * @param title Page’s title.
   * @param includeHidden Whether to include hidden categories.
   * @return A promise returning the titles of the page’s categories.
   */
  getPageCategories(title: string, includeHidden: boolean = false): Promise<string[]> {
    // TODO
    return null;
  }

  /**
   * Get the list of categories that match the given prefix.
   * @param prefix Categories’ prefix.
   * @return A promise returning the category titles.
   */
  getCategories(prefix: string): Promise<string[]> {
    // TODO
    return null;
  }

  /**
   * Parse the given wikicode.
   * @param content The content to parse.
   * @return A promise returning the generated HTML code.
   */
  parseWikicode(content: string): Promise<string> {
    // TODO
    return null;
  }

  /**
   * Make the current user follow the given page.
   * @param title Page’s title.
   * @return A promise.
   */
  followPage(title: string): Promise<void> {
    // TODO
    return null;
  }

  /**
   * Make the current user unfollow the given page.
   * @param title Page’s title.
   * @return A promise.
   */
  unfollowPage(title: string): Promise<void> {
    // TODO
    return null;
  }
}

declare global {
  interface Window {
    wiki: {
      gadgetsManager: WikiGadgetManager,
      api: WikiAPI,
      editor: any,
    };
    // Actual object is defined by ottm/static/ottm/libs/highlight/highlight.js
    hljs: {
      highlightElement: (e: HTMLElement) => void,
    };
  }
}

export default function initWiki() {
  window.wiki = {
    gadgetsManager: new WikiGadgetManager(),
    api: new WikiAPI(),
    editor: null,
  };
  // Apply HLJS on all tagged elements
  $(".hljs").each((_, e) => window.hljs.highlightElement(e));
  const action = window.ottm.page.get("wAction");
  if (action === "edit" || action === "submit") {
    initEditor();
  } else if (action === "talk") {
    // TODO
  }
}
