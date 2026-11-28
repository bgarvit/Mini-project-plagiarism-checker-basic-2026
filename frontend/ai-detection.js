/**
 * PLAGIFY AI Detection Script
 * Handles text/file input, analysis, and results display
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // Initialize AOS
  AOS.init({ duration: 600, easing: 'ease-out-cubic', once: true, offset: 50 });

  const token = window.plagifyApi?.getToken?.();
  const authGate = document.getElementById('aiAuthGate');
  const workspace = document.getElementById('aiWorkspace');

  // Check authentication
  if (!token) {
    authGate.hidden = false;
    workspace.hidden = true;
    return;
  }
  authGate.hidden = true;
  workspace.hidden = false;

  // Elements
  const tabs = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');
  const textEl = document.getElementById('aiText');
  const wordCount = document.getElementById('aiWordCount');
  const fileInput = document.getElementById('aiFileInput');
  const browseBtn = document.getElementById('aiBrowseBtn');
  const fileSelected = document.getElementById('aiFileSelected');
  const fileName = document.getElementById('aiFileName');
  const removeFile = document.getElementById('aiRemoveFile');
  const analyzeBtn = document.getElementById('aiAnalyzeBtn');
  const resetBtn = document.getElementById('aiResetBtn');
  const loading = document.getElementById('aiLoading');
  const errorEl = document.getElementById('aiError');
  const resultEl = document.getElementById('aiResult');

  let activeTab = 'text';
  let selectedFile = null;

  // Tab switching
  tabs.forEach((btn) => {
    btn.addEventListener('click', () => {
      activeTab = btn.dataset.tab;
      tabs.forEach((b) => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-selected', b === btn);
      });
      panels.forEach((p) => p.classList.toggle('active', p.dataset.panel === activeTab));
    });
  });

  // Word count for text input
  textEl?.addEventListener('input', () => {
    const text = textEl.value.trim();
    const count = text ? text.split(/\s+/).length : 0;
    wordCount.textContent = count;
  });

  // File upload
  browseBtn?.addEventListener('click', () => fileInput?.click());
  fileInput?.addEventListener('change', () => {
    const file = fileInput.files?.[0] || null;
    const error = validateFile(file);
    if (error) {
      errorEl.textContent = error;
      errorEl.hidden = false;
      if (fileInput) fileInput.value = '';
      return;
    }
    selectedFile = file;
    if (selectedFile) {
      fileName.textContent = selectedFile.name;
      fileSelected.hidden = false;
      errorEl.hidden = true;
    }
  });
  removeFile?.addEventListener('click', () => {
    selectedFile = null;
    if (fileInput) fileInput.value = '';
    fileSelected.hidden = true;
    errorEl.hidden = true;
  });

  // Drag and drop for file input
  const dropzone = document.getElementById('aiDropzone');
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(evt => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach(evt => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });
    dropzone.addEventListener('drop', (e) => {
      const file = e.dataTransfer?.files?.[0];
      if (file) {
        const error = validateFile(file);
        if (error) {
          errorEl.textContent = error;
          errorEl.hidden = false;
          return;
        }
        selectedFile = file;
        fileName.textContent = file.name;
        fileSelected.hidden = false;
        errorEl.hidden = true;
      }
    });
  }

  // Analyze button
  analyzeBtn?.addEventListener('click', async () => {
    errorEl.hidden = true;
    resultEl.hidden = true;

    const text = activeTab === 'text' ? textEl.value.trim() : '';
    const file = activeTab === 'file' ? selectedFile : null;

    if (!text && !file) {
      errorEl.textContent = 'Paste text or upload a file.';
      errorEl.hidden = false;
      return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="spinner spinner-sm"></span> Analyzing…';
    loading.hidden = false;

    try {
      const data = await window.plagifyApi.analyzeAI({ text: text || undefined, file: file || undefined });
      displayResults(data);
      showToast('Analysis complete', 'success');
    } catch (err) {
      errorEl.textContent = err.message || 'Detection failed';
      errorEl.hidden = false;
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = '<i class="bi bi-search"></i> Analyze for AI';
      loading.hidden = true;
    }
  });

  // Reset button
  resetBtn?.addEventListener('click', () => {
    if (textEl) textEl.value = '';
    if (wordCount) wordCount.textContent = '0';
    selectedFile = null;
    if (fileInput) fileInput.value = '';
    if (fileSelected) fileSelected.hidden = true;
    if (resultEl) resultEl.hidden = true;
    if (errorEl) errorEl.hidden = true;
    // Switch to text tab
    tabs.forEach(b => b.classList.toggle('active', b.dataset.tab === 'text'));
    panels.forEach(p => p.classList.toggle('active', p.dataset.panel === 'text'));
    activeTab = 'text';
  });

  function displayResults(data) {
    const pct = Math.round((data.ai_probability || 0) * 100);
    const circ = 2 * Math.PI * 62;

    document.getElementById('aiPct').textContent = pct + '%';
    document.getElementById('aiVerdict').textContent = formatVerdict(data.verdict);
    document.getElementById('aiConf').textContent = data.confidence ? data.confidence.charAt(0).toUpperCase() + data.confidence.slice(1) : '—';
    document.getElementById('aiProvider').textContent = formatProvider(data.provider);
    document.getElementById('aiWords').textContent = data.word_count ?? '—';
    document.getElementById('aiLimitations').textContent = data.limitations || '';

    // Update ring
    const ring = document.getElementById('aiRing');
    ring.style.strokeDasharray = String(circ);
    ring.style.strokeDashoffset = String(circ * (1 - pct / 100));

    // Color the ring based on probability
    if (pct >= 65) ring.style.stroke = 'var(--clr-accent)';
    else if (pct >= 40) ring.style.stroke = 'var(--clr-secondary)';
    else ring.style.stroke = 'var(--clr-primary)';

    resultEl.hidden = false;
    resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function formatVerdict(verdict) {
    const map = {
      'likely_ai': 'Likely AI',
      'mixed_or_uncertain': 'Mixed / Uncertain',
      'likely_human': 'Likely Human',
      'insufficient_text': 'Insufficient Text'
    };
    return map[verdict] || verdict || '—';
  }

  function formatProvider(provider) {
    const map = {
      'lmscan': 'LMScan (Local)',
      'gptzero': 'GPTZero API',
      'sapling': 'Sapling API',
      'heuristic': 'Statistical Heuristic'
    };
    return map[provider] || provider || '—';
  }

  // Mobile menu toggle
  document.getElementById('menuToggle')?.addEventListener('click', () => {
    document.getElementById('mainNav')?.classList.toggle('open');
  });
});

function validateFile(file) {
  const allowedTypes = ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'];
  const allowedExtensions = ['.txt', '.pdf', '.docx', '.doc'];
  const maxSize = 25 * 1024 * 1024; // 25MB
  
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowedExtensions.includes(ext)) {
    return 'Invalid file type. Please upload TXT, PDF, or DOCX files only.';
  }
  
  if (file.size > maxSize) {
    return 'File size exceeds 25MB limit. Please choose a smaller file.';
  }
  
  if (file.size === 0) {
    return 'File is empty. Please choose a valid document.';
  }
  
  return null;
}