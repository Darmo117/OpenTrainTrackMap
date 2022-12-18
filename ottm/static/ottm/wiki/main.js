// noinspection JSUnusedGlobalSymbols

/**
 * Wiki script.
 */
"use strict";

/**
 * Base class for wiki gadgets.
 * @abstract
 */
class WikiGadget {
  /** @type {string} */
  #name;
  /** @type {string} */
  #version;

  /**
   * Create a new gadget.
   * @param name {string} Gadget’s name.
   * @param version {string} Gadget’s version.
   */
  constructor(name, version) {
    if (new.target === WikiGadget) {
      throw new TypeError("Cannot construct WikiGadget instances directly");
    }
    this.#name = name;
    this.#version = version;
  }

  /** @return {string} This gadget’s name. */
  get name() {
    return this.#name;
  }

  /** @return {string} This gadget’s version. */
  get version() {
    return this.#version;
  }

  /**
   * Called when this gadget has been initialized and the manager is ready.
   */
  onReady() {
    throw new Error("method WikiGadget.onInit() not implemented");
  }
}

/**
 * This class manages wiki gadgets.
 */
class WikiGadgetManager {
  /** @type {number} Number of gadgets still loading. */
  #gadgetsQueueSize;
  /** @type {Object<string, WikiGadget>} Mapping of all successfully loaded gadgets. */
  #gadgets;
  /** @type {boolean} Whether all gadgets have been registered. */
  #finishedRegistration;
  /** @type {boolean} Whether this manager is locked. Once locked, no more gadgets can be registered. */
  #locked;

  constructor() {
    this.#gadgetsQueueSize = 0;
    this.#gadgets = {};
    this.#finishedRegistration = false;
    this.#locked = false;
  }

  /**
   * Register a gadget to be loaded asynchronously.
   * @param gadgetName {string} The gadget’s name.
   */
  registerGadget(gadgetName) {
    if (this.#locked) {
      throw new Error("Cannot register gadgets when manager is locked");
    }
    console.log(`Registering gadget "${gadgetName}…"`);
    this.#gadgetsQueueSize++;
    const apiPath = ottm.config.get("wApiPath");
    $.get(
      apiPath,
      {
        action: "query",
        query: "gadget",
        title: encodeURIComponent(gadgetName),
      },
      data => {
        try {
          /** @type {WikiGadget} */
          const gadget = eval(data); // We expect a function returning a WikiGadget subclass instance in the response data.
          this.#gadgets[gadget.name] = gadget;
        } catch (e) {
          console.error(`Error while loading gadget "${gadgetName}":\n${e}`);
        }
        this.#gadgetsQueueSize--;
        if (this.#gadgetsQueueSize === 0 && this.#finishedRegistration) {
          this.#lock();
        }
      },
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
   * @param name {string} Gadget’s name.
   * @return {WikiGadget|undefined} The gadget or undefined if none matched.
   */
  getGadget(name) {
    return this.#gadgets[name];
  }

  /**
   * Check whether the given gadget is registered.
   * @param name {string} Gadget name to check.
   * @return {boolean} True if a gadget with the specified name is registered, false otherwise.
   */
  isGadgetRegistered(name) {
    return this.#gadgets[name] !== undefined;
  }
}

/**
 * This class provides methods to interact with the wiki HTTP API.
 */
class WikiAPI {
  constructor() {
  }

  /**
   * @callback transformCB
   * @param {string} c Current page content.
   * @return {string|{content: string, summary: string?, minor: boolean?, hidden: boolean?, follow: boolean?}}
   *  The new content or an object with additional parameters.
   */
  /**
   * Edit a wiki page.
   * @param title {string} Page’s title.
   * @param transform {transformCB} Function to apply to the page’s current content.
   * @return {*} A jQuery promise.
   */
  editPage(title, transform) {
    // TODO
  }

  /**
   * Get the content of the given page.
   * @param title {string} Page’s title.
   * @return {*} A jQuery promise.
   */
  getPage(title) {
    // TODO
  }

  /**
   * Get the list of categories of the given page.
   * @param title {string} Page’s title.
   * @return {*} A jQuery promise.
   */
  getPageCategories(title) {
    // TODO
  }

  /**
   * Get the list of categories that match the given prefix.
   * @param prefix {string} Categories’ prefix.
   * @return {*} A jQuery promise.
   */
  getCategories(prefix) {
    // TODO
  }

  /**
   * Parse the given wikicode.
   * @param content {string} The content to parse.
   * @return {*} A jQuery promise.
   */
  parseWikicode(content) {
    // TODO
  }

  /**
   * Make the current user follow the given page.
   * @param title {string} Page’s title.
   * @return {*} A jQuery promise.
   */
  followPage(title) {
    // TODO
  }

  /**
   * Make the current user unfollow the given page.
   * @param title {string} Page’s title.
   * @return {*} A jQuery promise.
   */
  unfollowPage(title) {
    // TODO
  }
}

(function () {
  window.wiki = {
    gadgetsManager: new WikiGadgetManager(),
    api: new WikiAPI(),
  };
  // Apply HLJS on all tagged elements
  $(".hljs").each((_, element) => hljs.highlightElement(element));
})();
