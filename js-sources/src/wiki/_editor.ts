import { edit } from "ace-code";

// TEMP
import "ace-code/styles/theme/monokai.css";
import "ace-code/styles/theme/chrome.css";

/**
 * Script for the wiki page editor.
 */
export default function initEditor(): void {
  if (!window.ottm.user.get("useEditorSyntaxHighlighting")) return;

  const pageContentType = window.ottm.page.get("wContentType");
  if (typeof pageContentType !== "string")
    throw new Error("Missing page content type");

  const mode = {
    js: "javascript",
    css: "css",
    json: "json",
    module: "python",
    wikipage: "text", // TODO custom language: https://medium.com/@jackub/writing-custom-ace-editor-mode-5a7aa83dbe50
  }[pageContentType];
  const editorID = "wiki-ace-editor";
  const $div = $(`#${editorID}`).show();
  const targetId = $div.data("ace-target") as string;
  const $textarea = $(`#${targetId}`).hide();
  const editor = edit(editorID);
  editor.setOptions({
    // FIXME not working
    mode: `ace/mode/${mode}`,
    useSoftTabs: true,
    fontSize: 16,
    minLines: 20,
    maxLines: 20,
  });
  editor.setTheme(
    // FIXME not working
    window.ottm.page.get("darkMode") ? "ace/theme/monokai" : "ace/theme/chrome",
  );
  editor.getSession().setValue($textarea.val() as string);
  // Update form’s textarea on each change in the editor
  editor.getSession().on("change", () => {
    $textarea.val(editor.getSession().getValue()).trigger("change");
  });
  $("#wiki-edit-form").on("submit", (e) => {
    const comment = ($("#wiki-edit-form-comment").val() as string).trim();
    if (!comment && window.ottm.user.get("warnWhenNoWikiEditComment")) {
      const message = window.ottm.translate("wiki.edit.no_summary_warning");
      if (!confirm(message)) e.preventDefault();
    }
  });

  if (!window.ottm.user.get("wCanEditPage")) editor.setReadOnly(true);
  window.wiki.editor = editor;
}
