const $ = (selector) => document.querySelector(selector);

let notes = [];
let selectedId = null;
let query = "";
let activeTag = "";

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function markdown(value) {
  return escapeHtml(value)
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^- (.*)$/gm, "<li>$1</li>")
    .replace(/\n/g, "<br>");
}

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function currentNote() {
  return notes.find((note) => note.id === selectedId) || null;
}

function noteTags(note) {
  return String(note.meta?.tags || "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function allTags() {
  return [...new Set(notes.flatMap(noteTags))].sort((a, b) => a.localeCompare(b));
}

function filteredNotes() {
  const needle = query.toLowerCase();
  return notes
    .filter((note) => {
      const haystack = `${note.title} ${note.body} ${note.meta?.tags || ""}`.toLowerCase();
      return !needle || haystack.includes(needle);
    })
    .filter((note) => !activeTag || noteTags(note).includes(activeTag))
    .sort((a, b) => Number(Boolean(b.meta?.pinned)) - Number(Boolean(a.meta?.pinned)) || b.updated_at - a.updated_at);
}

function render() {
  const note = currentNote();
  $("#app").innerHTML = `
    <aside class="notes-sidebar">
      <div class="row">
        <button id="newNote">New note</button>
        <button class="ghost" id="exportNotes">Export</button>
      </div>
      <input id="search" placeholder="Search notes" value="${escapeHtml(query)}">
      <div class="tag-list">
        <button class="${activeTag ? "ghost" : ""}" data-tag="">All</button>
        ${allTags().map((tag) => `<button class="${activeTag === tag ? "" : "ghost"}" data-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`).join("")}
      </div>
      <div class="note-list">
        ${filteredNotes().map((entry) => `
          <button class="note-row ${entry.id === selectedId ? "selected" : ""}" data-id="${entry.id}">
            <strong>${entry.meta?.pinned ? "Pinned · " : ""}${escapeHtml(entry.title || "Untitled")}</strong>
            <span>${escapeHtml((entry.body || "").slice(0, 90))}</span>
          </button>
        `).join("") || `<p class="muted">No notes yet.</p>`}
      </div>
    </aside>
    <section class="editor-panel">
      ${note ? editor(note) : emptyState()}
    </section>
  `;
  bindEvents();
}

function emptyState() {
  return `
    <div class="empty">
      <h2>Select or create a note</h2>
      <p class="muted">Notes are stored in SQLite. Use Markdown for headings, lists, emphasis, and inline code.</p>
    </div>
  `;
}

function editor(note) {
  return `
    <form id="noteForm" class="note-form">
      <div class="row space">
        <input id="title" placeholder="Note title" value="${escapeHtml(note.title)}" required>
        <label class="pin-toggle"><input id="pinned" type="checkbox" ${note.meta?.pinned ? "checked" : ""}> Pin</label>
      </div>
      <input id="tags" placeholder="tags, comma separated" value="${escapeHtml(note.meta?.tags || "")}">
      <div class="editor-grid">
        <textarea id="body" placeholder="Write the note...">${escapeHtml(note.body)}</textarea>
        <article id="preview" class="preview">${markdown(note.body)}</article>
      </div>
      <div class="row">
        <button>Save</button>
        <button type="button" class="danger" id="deleteNote">Delete</button>
      </div>
    </form>
  `;
}

function bindEvents() {
  $("#newNote").addEventListener("click", createNote);
  $("#exportNotes").addEventListener("click", exportNotes);
  $("#search").addEventListener("input", (event) => {
    query = event.target.value;
    render();
  });
  document.querySelectorAll("[data-tag]").forEach((button) => {
    button.addEventListener("click", () => {
      activeTag = button.dataset.tag;
      render();
    });
  });
  document.querySelectorAll("[data-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedId = Number(button.dataset.id);
      render();
    });
  });
  if ($("#noteForm")) {
    $("#noteForm").addEventListener("submit", saveNote);
    $("#deleteNote").addEventListener("click", deleteNote);
    $("#body").addEventListener("input", () => {
      $("#preview").innerHTML = markdown($("#body").value);
    });
  }
}

async function loadNotes() {
  notes = await api("/api/items");
  if (selectedId && !notes.some((note) => note.id === selectedId)) selectedId = null;
  if (!selectedId && notes.length) selectedId = filteredNotes()[0]?.id || notes[0].id;
  render();
}

async function createNote() {
  const created = await api("/api/items", {
    method: "POST",
    body: JSON.stringify({
      title: "Untitled note",
      body: "",
      status: "active",
      meta: { tags: "", pinned: false },
    }),
  });
  selectedId = created.id;
  await loadNotes();
}

async function saveNote(event) {
  event.preventDefault();
  const note = currentNote();
  if (!note) return;
  await api(`/api/items/${note.id}`, {
    method: "PUT",
    body: JSON.stringify({
      ...note,
      title: $("#title").value.trim(),
      body: $("#body").value,
      status: "active",
      meta: {
        ...note.meta,
        tags: $("#tags").value.trim(),
        pinned: $("#pinned").checked,
      },
    }),
  });
  await loadNotes();
}

async function deleteNote() {
  const note = currentNote();
  if (!note || !confirm("Delete this note?")) return;
  await api(`/api/items/${note.id}`, { method: "DELETE" });
  selectedId = null;
  await loadNotes();
}

async function exportNotes() {
  const data = await api("/api/export");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  link.download = "notes-stash-backup.json";
  link.click();
}

document.body.innerHTML = `
  <main class="notes-app">
    <header class="top">
      <div>
        <h1>${escapeHtml(APP.name)}</h1>
        <p class="muted">${escapeHtml(APP.desc)}</p>
      </div>
    </header>
    <div id="app" class="notes-layout"></div>
  </main>
`;

loadNotes();
