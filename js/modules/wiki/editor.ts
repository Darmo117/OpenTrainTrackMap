declare global {
  interface Window {
    ace: AceAjax.Ace;
  }
}

/**
 * Script for the wiki page editor.
 */
export default function initEditor() {
  if (!window.ottm.user.get("useEditorSyntaxHighlighting")) {
    return;
  }
  const mode = {
    js: "javascript",
    css: "css",
    json: "json",
    module: "python",
    wikipage: "text", // TODO custom language: https://medium.com/@jackub/writing-custom-ace-editor-mode-5a7aa83dbe50
  }[window.ottm.page.get("wContentType") as string];
  const editorID = "wiki-ace-editor";
  const $div = $(`#${editorID}`).show();
  const targetId = $div.data("ace-target");
  const $textarea = $(`#${targetId}`).hide();
  const editor = window.ace.edit(editorID);
  editor.setOptions({
    mode: `ace/mode/${mode}`,
    useSoftTabs: true,
    fontSize: 16,
    minLines: 20,
    maxLines: 20,
  });
  // TODO let user choose theme?
  editor.setTheme(window.ottm.page.get("darkMode") ? "ace/theme/monokai" : "ace/theme/chrome");
  editor.getSession().setValue($textarea.val() as string);
  // Update form’s textarea on each change in the editor
  editor.getSession().on("change", () => $textarea.val(editor.getSession().getValue()).trigger("change"));
  $("#wiki-edit-form").on("submit", e => {
    const comment = ($("#wiki-edit-form-comment").val() as string).trim();
    if (!comment && window.ottm.user.get("warnWhenNoWikiEditComment")) {
      const message = window.ottm.translations.get("wiki.edit.no_summary_warning");
      if (!confirm(message)) {
        e.preventDefault();
      }
    }
  });

  if (!window.ottm.user.get("wCanEditPage")) {
    editor.setReadOnly(true);
  }
  window.wiki.editor = editor;
}
