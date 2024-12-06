import { ServiceManager } from "ace-linters/build/service-manager";

const manager = new ServiceManager(self);

manager.registerService("css", {
  module: () => import("ace-linters/build/css-service"),
  className: "CssService",
  modes: "css",
});

manager.registerService("javascript", {
  module: () => import("ace-linters/build/javascript-service"),
  className: "JavascriptService",
  modes: "javascript",
});

manager.registerService("json", {
  module: () => import("ace-linters/build/json-service"),
  className: "JsonService",
  modes: "json",
});

manager.registerService("python", {
  module: () => import("ace-linters/build/python-service"),
  className: "PythonService",
  modes: "python",
});
