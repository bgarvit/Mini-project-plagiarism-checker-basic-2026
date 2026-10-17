document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");
  let activeTab = "text";
  let selectedFile = null;

  tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      activeTab = btn.dataset.tab;
      tabs.forEach((b) => b.classList.toggle("active", b === btn));
      panels.forEach((p) => p.classList.toggle("active", p.dataset.panel === activeTab));
    });
  });

  const textEl = document.getElementById("aiText");
  const wordCount = document.getElementById("aiWordCount");
  textEl?.addEventListener("input", () => {
    const w = textEl.value.trim() ? textEl.value.trim().split(/\s+/).length : 0;
    if (wordCount) wordCount.textContent = w;
  });

  const fileInput = document.getElementById("aiFileInput");
  const browseBtn = document.getElementById("aiBrowseBtn");
  const fileSelected = document.getElementById("aiFileSelected");
  const fileName = document.getElementById("aiFileName");
  const removeFile = document.getElementById("aiRemoveFile");
  browseBtn?.addEventListener("click", () => fileInput.click());
  fileInput?.addEventListener("change", () => {
    selectedFile = fileInput.files?.[0] || null;
    if (selectedFile) {
      fileName.textContent = selectedFile.name;
      fileSelected.hidden = false;
    }
  });
  removeFile?.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    fileSelected.hidden = true;
  });

  const circ = 2 * Math.PI * 52;
  const analyzeBtn = document.getElementById("aiAnalyzeBtn");
  const loading = document.getElementById("aiLoading");
  const errorEl = document.getElementById("aiError");
  const resultEl = document.getElementById("aiResult");

  analyzeBtn?.addEventListener("click", async () => {
    errorEl.hidden = true;
    resultEl.hidden = true;
    const text = activeTab === "text" ? textEl.value.trim() : "";
    const file = activeTab === "file" ? selectedFile : null;
    if (!text && !file) {
      errorEl.textContent = "Paste text or upload a file.";
      errorEl.hidden = false;
      return;
    }
    analyzeBtn.disabled = true;
    loading.hidden = false;
    try {
      const data = await window.plagifyApi.analyzeAI({ text: text || undefined, file: file || undefined });
      const pct = Math.round((data.ai_probability || 0) * 100);
      document.getElementById("aiPct").textContent = pct + "%";
      document.getElementById("aiVerdict").textContent = (data.verdict || "—").replace(/_/g, " ");
      document.getElementById("aiConf").textContent = data.confidence || "—";
      document.getElementById("aiProvider").textContent = data.provider || "—";
      document.getElementById("aiWords").textContent = data.word_count ?? "—";
      document.getElementById("aiLimitations").textContent = data.limitations || "";
      const ring = document.getElementById("aiRing");
      ring.style.strokeDasharray = String(circ);
      ring.style.strokeDashoffset = String(circ * (1 - pct / 100));
      resultEl.hidden = false;
    } catch (err) {
      errorEl.textContent = err.message || "Detection failed";
      errorEl.hidden = false;
    } finally {
      analyzeBtn.disabled = false;
      loading.hidden = true;
    }
  });

  document.getElementById("aiResetBtn")?.addEventListener("click", () => {
    textEl.value = "";
    wordCount.textContent = "0";
    selectedFile = null;
    fileInput.value = "";
    fileSelected.hidden = true;
    resultEl.hidden = true;
    errorEl.hidden = true;
  });

  document.getElementById("menuToggle")?.addEventListener("click", () => {
    document.getElementById("mainNav")?.classList.toggle("open");
  });
});
