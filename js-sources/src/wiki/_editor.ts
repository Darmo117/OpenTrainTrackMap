import $ from "jquery";
import { edit } from "ace-builds";
import "ace-builds/src-noconflict/mode-css";
import "ace-builds/src-noconflict/mode-javascript";
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/theme-chrome";
import "ace-builds/src-noconflict/theme-monokai";

/**
 * Script for the wiki page editor.
 */
export default function initEditor(): void {
  if (!window.ottm.user.get("useEditorSyntaxHighlighting")) return;

  const pageContentType = window.ottm.page.get("wContentType");
  if (typeof pageContentType !== "string")
    throw new Error("Missing page content type");

  const modes: Record<string, string> = {
    js: "javascript",
    css: "css",
    json: "json",
    module: "python",
    wikipage: "text", // TODO custom language: https://medium.com/@jackub/writing-custom-ace-editor-mode-5a7aa83dbe50
  };
  const mode = modes[pageContentType] ?? modes.wikipage;
  const editorID = "wiki-ace-editor";
  const $div = $(`#${editorID}`).show();
  const targetId = $div.data("ace-target") as string;
  const $textarea = $(`#${targetId}`).hide() as JQuery<HTMLTextAreaElement>;
  const editor = edit(editorID);
  editor.setOptions({
    mode: `ace/mode/${mode}`,
    useSoftTabs: true,
    fontSize: 16,
    minLines: 20,
    maxLines: 20,
  });
  editor.setTheme(
    window.ottm.page.get("darkMode") ? "ace/theme/monokai" : "ace/theme/chrome",
  );
  const session = editor.getSession();
  session.setValue($textarea.val() ?? "");
  // Update form’s textarea on each change in the editor
  session.on("change", () => {
    $textarea.val(session.getValue()).trigger("change");
  });
  $("#wiki-edit-form").on("submit", (e) => {
    const $commentInput: JQuery<HTMLInputElement> = $(
      "#wiki-edit-form-comment",
    );
    const comment = ($commentInput.val() ?? "").trim();
    if (!comment && window.ottm.user.get("warnWhenNoWikiEditComment")) {
      const message = window.ottm.translate("wiki.edit.no_summary_warning");
      if (!confirm(message)) e.preventDefault();
    }
  });

  if (!window.ottm.user.get("wCanEditPage")) editor.setReadOnly(true);
  window.wiki.editor = editor;
}
