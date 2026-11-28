/**
 * PLAGIFY Plagiarism Checker Script
 * Handles original document management, comparison, and results display
 */

document.addEventListener('DOMContentLoaded', async () => {
  'use strict';

  // Initialize AOS
  AOS.init({ duration: 600, easing: 'ease-out-cubic', once: true, offset: 50 });

  const token = window.plagifyApi?.getToken?.();
  const authGate = document.getElementById('authGate');
  const workspace = document.getElementById('plagWorkspace');

  // Check authentication
  if (!token) {
    authGate.hidden = false;
    workspace.hidden = true;
    return;
  }
  authGate.hidden = true;
  workspace.hidden = false;

  // Elements
  const statusEl = document.getElementById('origStatus');
  const origError = document.getElementById('origError');
  const deleteBtn = document.getElementById('origDeleteBtn');
  const replaceBtn = document.getElementById('origReplaceBtn');
  const viewDbBtn = document.getElementById('origViewDbBtn');
  const origDropzone = document.getElementById('origDropzone');
  const origLoading = document.getElementById('origLoading');
  const origInput = document.getElementById('origFileInput');
  const origUploadBtn = document.getElementById('origUploadBtn');
  const origFileSelected = document.getElementById('origFileSelected');
  const origFileName = document.getElementById('origFileName');
  const origRemoveFile = document.getElementById('origRemoveFile');

  const cmpInput = document.getElementById('cmpFileInput');
  const cmpDropzone = document.getElementById('cmpDropzone');
  const cmpBrowseBtn = document.getElementById('cmpBrowseBtn');
  const cmpFileSelected = document.getElementById('cmpFileSelected');
  const cmpFileName = document.getElementById('cmpFileName');
  const cmpRemoveFile = document.getElementById('cmpRemoveFile');
  const cmpBtn = document.getElementById('cmpBtn');
  const cmpLoading = document.getElementById('cmpLoading');
  const cmpError = document.getElementById('cmpError');
  const cmpResult = document.getElementById('cmpResult');

  const savedFilesModal = document.getElementById('savedFilesModal');
  const savedFilesList = document.getElementById('savedFilesList');
  const savedFilesSummary = document.getElementById('savedFilesSummary');
  const savedFilesClose = document.getElementById('savedFilesClose');

  const downloadReportBtn = document.getElementById('downloadReportBtn');

  let cmpFile = null;

  // Initialize
  await refreshOriginal();
  setupEventListeners();

  function setupEventListeners() {
    // Original document upload
    origUploadBtn?.addEventListener('click', () => origInput?.click());
    replaceBtn?.addEventListener('click', () => origInput?.click());

    origInput?.addEventListener('change', async () => {
      const file = origInput.files?.[0];
      if (!file) return;
      await saveOriginalToDatabase(file);
    });

    // Drag and drop for original
    if (origDropzone) {
      ['dragenter', 'dragover'].forEach(evt => {
        origDropzone.addEventListener(evt, (e) => {
          e.preventDefault();
          e.stopPropagation();
          origDropzone.classList.add('dragover');
        });
      });
      ['dragleave', 'drop'].forEach(evt => {
        origDropzone.addEventListener(evt, (e) => {
          e.preventDefault();
          e.stopPropagation();
          origDropzone.classList.remove('dragover');
        });
      });
      origDropzone.addEventListener('drop', async (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (file) await saveOriginalToDatabase(file);
      });
    }

    // Remove original file selection
    origRemoveFile?.addEventListener('click', () => {
      if (origInput) origInput.value = '';
      if (origFileSelected) origFileSelected.hidden = true;
    });

    // Delete original
    deleteBtn?.addEventListener('click', async () => {
      if (!confirm('Delete the registered original document from the database?')) return;
      try {
        await window.plagifyApi.deleteOriginal();
        if (origInput) origInput.value = '';
        await refreshOriginal();
        showToast('Original document deleted', 'success');
      } catch (err) {
        showError(origError, err.message);
      }
    });

    // View saved files
    viewDbBtn?.addEventListener('click', openSavedFilesModal);
    savedFilesClose?.addEventListener('click', closeSavedFilesModal);
    savedFilesModal?.addEventListener('click', (e) => {
      if (e.target === savedFilesModal) closeSavedFilesModal();
    });

    // Comparison document
    cmpBrowseBtn?.addEventListener('click', () => cmpInput?.click());
    cmpInput?.addEventListener('change', () => {
      const file = cmpInput.files?.[0] || null;
      const error = validateFile(file);
      if (error) {
        showError(cmpError, error);
        if (cmpInput) cmpInput.value = '';
        return;
      }
      cmpFile = file;
      if (cmpFile) {
        cmpFileName.textContent = cmpFile.name;
        cmpFileSelected.hidden = false;
        cmpError.hidden = true;
      }
    });
    cmpRemoveFile?.addEventListener('click', () => {
      cmpFile = null;
      if (cmpInput) cmpInput.value = '';
      cmpFileSelected.hidden = true;
      cmpError.hidden = true;
    });

    // Compare button
    cmpBtn?.addEventListener('click', handleCompare);

    // Download report
    downloadReportBtn?.addEventListener('click', downloadReport);

    // Drag and drop for comparison
    if (cmpDropzone) {
      ['dragenter', 'dragover'].forEach(evt => {
        cmpDropzone.addEventListener(evt, (e) => {
          e.preventDefault();
          e.stopPropagation();
          cmpDropzone.classList.add('dragover');
        });
      });
      ['dragleave', 'drop'].forEach(evt => {
        cmpDropzone.addEventListener(evt, (e) => {
          e.preventDefault();
          e.stopPropagation();
          cmpDropzone.classList.remove('dragover');
        });
      });
      cmpDropzone.addEventListener('drop', (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (file) {
          const error = validateFile(file);
          if (error) {
            showError(cmpError, error);
            return;
          }
          cmpFile = file;
          cmpFileName.textContent = file.name;
          cmpFileSelected.hidden = false;
          cmpError.hidden = true;
        }
      });
    }
  }

  async function refreshOriginal() {
    try {
      const data = await window.plagifyApi.getOriginal();
      if (data.registered && data.document) {
        statusEl.innerHTML = `
          <i class="bi bi-check-circle-fill" style="color: var(--clr-primary); margin-right: 8px;"></i>
          <strong>Original registered:</strong> ${escapeHtml(data.document.document_name)} 
          <span class="muted">· ${(data.document.text_length || '—')} chars · ${formatDate(data.document.created_at)}</span>
        `;
        statusEl.classList.remove('muted');
        deleteBtn.hidden = false;
        replaceBtn.hidden = false;
        if (origDropzone) origDropzone.hidden = true;
        if (origFileSelected) origFileSelected.hidden = true;
      } else {
        statusEl.innerHTML = `
          <i class="bi bi-info-circle" style="color: var(--clr-text-light); margin-right: 8px;"></i>
          No original document registered. Upload one to enable comparisons.
        `;
        statusEl.classList.add('muted');
        deleteBtn.hidden = true;
        replaceBtn.hidden = true;
        if (origDropzone) origDropzone.hidden = false;
      }
    } catch (err) {
      statusEl.textContent = 'Could not load original status: ' + err.message;
      statusEl.classList.add('muted');
    }
  }

  async function saveOriginalToDatabase(file) {
    if (!file) return;
    
    // Validate file
    const validationError = validateFile(file);
    if (validationError) {
      showError(origError, validationError);
      return;
    }
    
    origError.hidden = true;
    origLoading.hidden = false;
    if (origUploadBtn) origUploadBtn.disabled = true;

    try {
      const res = await window.plagifyApi.registerOriginal(file);
      showToast(res.message || 'Original document saved to database.', 'success');
      if (origInput) origInput.value = '';
      await refreshOriginal();
    } catch (err) {
      showError(origError, err.message || 'Failed to save original document. Please try again.');
    } finally {
      origLoading.hidden = true;
      if (origUploadBtn) origUploadBtn.disabled = false;
      if (origInput) origInput.value = '';
    }
  }

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

  async function openSavedFilesModal() {
    if (!savedFilesModal) return;
    savedFilesModal.hidden = false;
    savedFilesSummary.textContent = 'Loading…';
    savedFilesList.innerHTML = '';

    try {
      const data = await window.plagifyApi.listOriginals();
      const docs = data.documents || [];

      savedFilesSummary.textContent = docs.length === 0
        ? 'No files saved in the database yet.'
        : `${docs.length} file(s) stored for your account (latest is used for comparisons).`;

      docs.forEach((doc, idx) => {
        const item = document.createElement('div');
        item.className = 'saved-file-item';
        const hash = doc.content_hash ? String(doc.content_hash).slice(0, 12) + '…' : '—';
        const when = doc.created_at ? formatDate(doc.created_at) : '—';
        const len = doc.text_length != null ? `${doc.text_length} chars` : '';
        item.innerHTML = `
          <strong>${idx === 0 ? '<i class="bi bi-circle-fill" style="color: var(--clr-primary); margin-right: 6px;"></i>' : ''}${escapeHtml(doc.document_name || 'Untitled')}</strong>
          <div class="saved-file-meta">Saved: ${when} · hash ${escapeHtml(hash)}${len ? ' · ' + len : ''}${idx === 0 ? ' · active for comparison' : ''}</div>
        `;
        savedFilesList.appendChild(item);
      });
    } catch (err) {
      savedFilesSummary.textContent = err.message || 'Could not load saved files.';
    }
  }

  function closeSavedFilesModal() {
    if (savedFilesModal) savedFilesModal.hidden = true;
  }

  async function handleCompare() {
    cmpError.hidden = true;
    cmpResult.hidden = true;

    if (!cmpFile) {
      showError(cmpError, 'Choose a document to compare.');
      return;
    }

    cmpBtn.disabled = true;
    cmpBtn.innerHTML = '<span class="spinner spinner-sm"></span> Comparing…';
    cmpLoading.hidden = false;

    try {
      const data = await window.plagifyApi.compareToOriginal(cmpFile);
      displayResults(data);
      showToast('Comparison complete', 'success');
    } catch (err) {
      showError(cmpError, err.message || 'Compare failed');
    } finally {
      cmpBtn.disabled = false;
      cmpBtn.innerHTML = '<i class="bi bi-search"></i> Compare to Original';
      cmpLoading.hidden = true;
    }
  }

  function displayResults(data) {
    const pct = data.similarity_percent || 0;
    const circ = 2 * Math.PI * 62;

    // Update percentage ring
    document.getElementById('cmpPct').textContent = pct + '%';
    const ring = document.getElementById('cmpRing');
    ring.style.strokeDasharray = String(circ);
    ring.style.strokeDashoffset = String(circ * (1 - Math.min(pct, 100) / 100));

    // Color the ring based on percentage
    if (pct >= 70) ring.style.stroke = 'var(--clr-accent)';
    else if (pct >= 40) ring.style.stroke = 'var(--clr-secondary)';
    else ring.style.stroke = 'var(--clr-primary)';

    // Update metrics
    document.getElementById('cmpTfidf').textContent = (data.tfidf_cosine_similarity ?? '—') + '%';
    document.getElementById('cmpToken').textContent = (data.token_overlap ?? '—') + '%';
    document.getElementById('cmpShingle').textContent = (data.shingle_overlap ?? '—') + '%';
    document.getElementById('cmpCharGram').textContent = (data.char_gram_overlap ?? '—') + '%';
    document.getElementById('cmpSentJaccard').textContent = (data.sentence_match_avg ?? '—') + '%';
    document.getElementById('cmpSentTfidf').textContent = (data.sentence_tfidf_avg ?? '—') + '%';
    document.getElementById('cmpMatches').textContent = data.matched_passage_count ?? 0;
    document.getElementById('cmpOrigName').textContent = data.original?.document_name || '—';

    // Methodology and disclaimer
    document.getElementById('cmpMethod').textContent = data.scoring_method || '';
    document.getElementById('cmpDisclaimer').textContent = data.disclaimer || '';

    // Matched passages
    const list = document.getElementById('passageList');
    list.innerHTML = '';

    if (data.matched_passages && data.matched_passages.length > 0) {
      data.matched_passages.forEach((m) => {
        const div = document.createElement('div');
        div.className = 'passage-item';
        const algorithmBadge = m.match_algorithm === 'tfidf_cosine' ? 'TF-IDF Cosine' : 'Jaccard';
        const typeLabel = m.match_type.charAt(0).toUpperCase() + m.match_type.slice(1);
        div.innerHTML = `
          <div class="passage-meta">${algorithmBadge} · ${typeLabel} · ${(m.similarity * 100).toFixed(0)}%</div>
          <div><strong>Submitted:</strong> ${escapeHtml(m.submitted)}</div>
          <div style="margin-top: 8px;"><strong>Original:</strong> ${escapeHtml(m.original)}</div>
        `;
        list.appendChild(div);
      });
    } else {
      list.innerHTML = '<p class="muted" style="text-align: center; padding: 20px;">No significant matching passages found.</p>';
    }

    // Unmatched content - find sentences in submitted doc that weren't matched
    displayUnmatchedContent(data);

    cmpResult.hidden = false;
    cmpResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function displayUnmatchedContent(data) {
    const unmatchedSection = document.getElementById('unmatchedSection');
    const unmatchedList = document.getElementById('unmatchedList');
    
    if (!unmatchedSection || !unmatchedList) return;
    
    // Get submitted text from the compared file
    if (!cmpFile) {
      unmatchedSection.hidden = true;
      return;
    }
    
    // Read the file content to extract sentences
    const reader = new FileReader();
    reader.onload = function(e) {
      const text = e.target.result;
      const sentences = extractSentences(text);
      
      // Get matched submitted passages
      const matchedSubmitted = new Set();
      if (data.matched_passages) {
        data.matched_passages.forEach(m => {
          if (m.submitted) {
            matchedSubmitted.add(normalizeText(m.submitted));
          }
        });
      }
      
      // Find unmatched sentences with their positions
      const unmatched = [];
      sentences.forEach((sentence, idx) => {
        if (sentence.length > 20 && !matchedSubmitted.has(normalizeText(sentence))) {
          unmatched.push({ sentence, index: idx });
        }
      });
      
      if (unmatched.length > 0) {
        unmatchedList.innerHTML = '';
        unmatched.forEach((item, idx) => {
          const div = document.createElement('div');
          div.className = 'passage-item';
          div.style.borderLeft = '3px solid var(--clr-secondary)';
          
          // Calculate approximate location in submitted document
          const location = calculateLocation(item.index, sentences.length);
          
          div.innerHTML = `
            <div class="passage-meta" style="color: var(--clr-secondary);">
              <i class="bi bi-file-text"></i> Unique Content · Reference ${idx + 1}
            </div>
            <div style="font-size: 0.85rem; color: var(--clr-text-muted); margin-bottom: 4px;">
              <strong>Location in Submitted Document:</strong> ${location}
            </div>
            <div style="font-size: 0.85rem; color: var(--clr-text);">
              <strong>Status:</strong> Not found in original reference document
            </div>
          `;
          unmatchedList.appendChild(div);
        });
        unmatchedSection.hidden = false;
      } else {
        unmatchedSection.hidden = true;
      }
    };
    reader.readAsText(cmpFile);
  }

  function calculateLocation(sentenceIndex, totalSentences) {
    // Approximate page (assuming ~25 sentences per page)
    const page = Math.floor(sentenceIndex / 25) + 1;
    // Approximate paragraph (assuming ~5 sentences per paragraph)
    const paragraph = Math.floor(sentenceIndex / 5) + 1;
    // Line within paragraph
    const lineInPara = (sentenceIndex % 5) + 1;
    
    return `Page ${page}, Paragraph ${paragraph}, Line ${lineInPara}`;
  }

  function extractSentences(text) {
    // Simple sentence extraction - split by period, question mark, exclamation
    return text
      .split(/[.!?]+/)
      .map(s => s.trim())
      .filter(s => s.length > 10);
  }

  function normalizeText(text) {
    return text.toLowerCase().replace(/\s+/g, ' ').trim();
  }

  function downloadReport() {
    // TODO: Implement PDF report generation
    showToast('Report download coming soon', 'info');
  }

  function showError(el, message) {
    el.textContent = message;
    el.hidden = false;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>');
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  }

  // Mobile menu toggle
  document.getElementById('menuToggle')?.addEventListener('click', () => {
    document.getElementById('mainNav')?.classList.toggle('open');
  });
});