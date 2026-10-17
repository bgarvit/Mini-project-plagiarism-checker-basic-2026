document.addEventListener("DOMContentLoaded", async () => {
  const token = window.plagifyApi.getToken();
  const authGate = document.getElementById("authGate");
  const workspace = document.getElementById("plagWorkspace");
  if (!token) {
    authGate.hidden = false;
    workspace.hidden = true;
    return;
  }
  authGate.hidden = true;
  workspace.hidden = false;

  const statusEl = document.getElementById("originalStatus");
  const origError = document.getElementById("origError");
  const deleteBtn = document.getElementById("origDeleteBtn");
  const replaceBtn = document.getElementById("origReplaceBtn");
  const origDropzone = document.getElementById("origDropzone");
  const origLoading = document.getElementById("origLoading");
  const origInput = document.getElementById("origFileInput");
  let cmpFile = null;

  async function refreshOriginal() {
    try {
      const data = await window.plagifyApi.getOriginal();
      if (data.registered && data.document) {
        statusEl.textContent =
          `Stored in database: ${data.document.document_name} · hash ${String(data.document.content_hash || "").slice(0, 12)}…`;
        statusEl.classList.remove("muted");
        deleteBtn.hidden = false;
        if (replaceBtn) replaceBtn.hidden = false;
        if (origDropzone) origDropzone.hidden = true;
      } else {
        statusEl.textContent = "No original in the database yet. Upload one to enable comparisons.";
        statusEl.classList.add("muted");
        deleteBtn.hidden = true;
        if (replaceBtn) replaceBtn.hidden = true;
        if (origDropzone) origDropzone.hidden = false;
      }
    } catch (err) {
      statusEl.textContent = "Could not load original status: " + err.message;
    }
  }
  await refreshOriginal();

  async function saveOriginalToDatabase(file) {
    if (!file) return;
    origError.hidden = true;
    if (origLoading) origLoading.hidden = false;
    try {
      const res = await window.plagifyApi.registerOriginal(file);
      statusEl.textContent = res.message || "Original document saved to the database.";
      if (origInput) origInput.value = "";
      await refreshOriginal();
    } catch (err) {
      origError.textContent = err.message || "Failed to save original document.";
      origError.hidden = false;
    } finally {
      if (origLoading) origLoading.hidden = true;
      if (origInput) origInput.value = "";
    }
  }

  function openOriginalPicker() {
    origInput?.click();
  }

  document.getElementById("origUploadBtn")?.addEventListener("click", openOriginalPicker);
  replaceBtn?.addEventListener("click", openOriginalPicker);

  // Auto-save to database as soon as the user selects a file
  origInput?.addEventListener("change", async () => {
    const file = origInput.files?.[0];
    if (!file) return;
    await saveOriginalToDatabase(file);
  });

  // Drag-and-drop also saves immediately
  if (origDropzone) {
    ["dragenter", "dragover"].forEach((evt) => {
      origDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        origDropzone.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach((evt) => {
      origDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        origDropzone.classList.remove("dragover");
      });
    });
    origDropzone.addEventListener("drop", async (e) => {
      const file = e.dataTransfer?.files?.[0];
      if (file) await saveOriginalToDatabase(file);
    });
  }

  deleteBtn?.addEventListener("click", async () => {
    if (!confirm("Delete the registered original document from the database?")) return;
    try {
      await window.plagifyApi.deleteOriginal();
      if (origInput) origInput.value = "";
      await refreshOriginal();
    } catch (err) {
      origError.textContent = err.message;
      origError.hidden = false;
    }
  });

  const cmpInput = document.getElementById("cmpFileInput");
  const cmpSelected = document.getElementById("cmpFileSelected");
  const cmpName = document.getElementById("cmpFileName");
  document.getElementById("cmpBrowseBtn")?.addEventListener("click", () => cmpInput.click());
  cmpInput?.addEventListener("change", () => {
    cmpFile = cmpInput.files?.[0] || null;
    if (cmpFile) {
      cmpName.textContent = cmpFile.name;
      cmpSelected.hidden = false;
    }
  });
  document.getElementById("cmpRemoveFile")?.addEventListener("click", () => {
    cmpFile = null;
    cmpInput.value = "";
    cmpSelected.hidden = true;
  });

  const circ = 2 * Math.PI * 52;
  const cmpBtn = document.getElementById("cmpBtn");
  const loading = document.getElementById("cmpLoading");
  const cmpError = document.getElementById("cmpError");
  const cmpResult = document.getElementById("cmpResult");

  cmpBtn?.addEventListener("click", async () => {
    cmpError.hidden = true;
    cmpResult.hidden = true;
    if (!cmpFile) {
      cmpError.textContent = "Choose a document to compare.";
      cmpError.hidden = false;
      return;
    }
    cmpBtn.disabled = true;
    loading.hidden = false;
    try {
      const data = await window.plagifyApi.compareToOriginal(cmpFile);
      const pct = data.similarity_percent || 0;
      document.getElementById("cmpPct").textContent = pct + "%";
      document.getElementById("cmpToken").textContent = (data.token_overlap ?? "—") + "%";
      document.getElementById("cmpShingle").textContent = (data.shingle_overlap ?? "—") + "%";
      document.getElementById("cmpMatches").textContent = data.matched_passage_count ?? 0;
      document.getElementById("cmpOrigName").textContent =
        data.original?.document_name || "—";
      document.getElementById("cmpMethod").textContent = data.scoring_method || "";
      document.getElementById("cmpDisclaimer").textContent = data.disclaimer || "";
      const ring = document.getElementById("cmpRing");
      ring.style.strokeDasharray = String(circ);
      ring.style.strokeDashoffset = String(circ * (1 - Math.min(pct, 100) / 100));
      const list = document.getElementById("passageList");
      list.innerHTML = "";
      (data.matched_passages || []).forEach((m) => {
        const div = document.createElement("div");
        div.className = "passage-item";
        div.innerHTML = `<div class="passage-meta">${m.match_type} · ${(m.similarity * 100).toFixed(0)}%</div>
          <div><strong>Submitted:</strong> ${escapeHtml(m.submitted)}</div>
          <div><strong>Original:</strong> ${escapeHtml(m.original)}</div>`;
        list.appendChild(div);
      });
      cmpResult.hidden = false;
    } catch (err) {
      cmpError.textContent = err.message || "Compare failed";
      cmpError.hidden = false;
    } finally {
      cmpBtn.disabled = false;
      loading.hidden = true;
    }
  });

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  document.getElementById("menuToggle")?.addEventListener("click", () => {
    document.getElementById("mainNav")?.classList.toggle("open");
  });
});
