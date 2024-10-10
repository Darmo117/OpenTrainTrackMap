import tslint from "typescript-eslint";
import js from "@eslint/js";
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';
import globals from "globals";

export default tslint.config({}, {
  extends: [
    js.configs.recommended,
    ...tslint.configs.strictTypeChecked,
    ...tslint.configs.stylisticTypeChecked,
    eslintPluginPrettierRecommended, // Keep last to avoid conflicts
  ],
  files: ["**/*.ts"],
  languageOptions: {
    ecmaVersion: 2020,
    globals: globals.browser,
    parserOptions: {
      project: "./tsconfig.json",
      tsconfigRootDir: import.meta.dirName,
    }
  },
  rules: {
    "@typescript-eslint/no-unused-vars": [
      "error",
      {argsIgnorePattern: "^_"}, // Ignore params starting with "_"
    ],
    "@typescript-eslint/restrict-template-expressions": [
      "off",
    ],
    "@typescript-eslint/no-base-to-string": [
      "off",
    ]
  }
});
