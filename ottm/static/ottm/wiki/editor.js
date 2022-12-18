/**
 * Script for the wiki page editor.
 */
"use strict";

(function () {
  const mode = {
    js: "javascript",
    css: "css",
    json: "json",
    module: "python",
    wikipage: "text", // TODO custom language: https://medium.com/@jackub/writing-custom-ace-editor-mode-5a7aa83dbe50
  }[ottm.page.get("wContentType")];
  const editorID = "wiki-ace-editor";
  const $div = $(`#${editorID}`);
  const targetId = $div.data("ace-target");
  const $textarea = $(`#${targetId}`).hide();
  const editor = ace.edit(editorID, {
    mode: `ace/mode/${mode}`,
    useSoftTabs: true,
    fontSize: 16,
    minLines: 20,
    maxLines: 20,
  });
  editor.setTheme(ottm.page.get("darkMode") ? "ace/theme/monokai" : "ace/theme/chrome");
  editor.getSession().setValue($textarea.val());
  // Update form’s textarea on each change in the editor
  editor.getSession().on("change", () => $textarea.val(editor.getSession().getValue()).trigger("change"));
  $("#wiki-edit-form").on("submit", e => {
    if (!$("#wiki-edit-form-comment").val().trim() && ottm.user.get("warnWhenNoWikiEditComment")) {
      const message = ottm._translations.get("wiki.edit.no_summary_warning");
      if (!confirm(message)) {
        e.preventDefault();
      }
    }
  });

  if (!ottm.user.get("wCanEditPage")) {
    editor.setReadOnly(true);
  }
  ottm.wiki.editor = editor;
})();
