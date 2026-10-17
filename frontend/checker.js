document.addEventListener("DOMContentLoaded", function () {
    const inputText = document.getElementById("inputText");
    const wordCount = document.getElementById("wordCount");
    const charCount = document.getElementById("charCount");
    const checkBtn = document.getElementById("checkBtn");
    const resetBtn = document.getElementById("resetBtn");
    const progressWrap = document.getElementById("progressWrap");
    const progressFill = document.getElementById("progressFill");
    const progressLabel = document.getElementById("progressLabel");
    const resultCard = document.getElementById("resultCard");
    const uniquePct = document.getElementById("uniquePct");
    const similarPct = document.getElementById("similarPct");
    const sourcesFound = document.getElementById("sourcesFound");
    const wordsScanned = document.getElementById("wordsScanned");
    const ringFill = document.getElementById("ringFill");
    const downloadReportBtn = document.getElementById("downloadReportBtn");
    const fileInput = document.getElementById("fileInput");
    const browseBtn = document.getElementById("browseBtn");
    const dropzone = document.getElementById("dropzone");
    const fileSelected = document.getElementById("fileSelected");
    const fileName = document.getElementById("fileName");
    const removeFile = document.getElementById("removeFile");
    const urlInput = document.getElementById("urlInput");
    const excludeUrlInput = document.getElementById("excludeUrlInput");
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const modeButtons = document.querySelectorAll(".mode-btn");
    const menuToggle = document.getElementById("menuToggle");
    const mainNav = document.getElementById("mainNav");

    let activeTab = "text";
    let scanMode = "normal";
    let selectedFile = null;
    let lastReport = null;

    const circumference = 2 * Math.PI * 52;

    function updateCounts() {
        const text = inputText ? inputText.value : "";
        const words = text.trim() ? text.trim().split(/\s+/).length : 0;
        if (wordCount) wordCount.textContent = words.toLocaleString();
        if (charCount) charCount.textContent = text.length.toLocaleString();
    }

    function getScanOptions() {
        return {
            exclude_quotes: document.getElementById("toggleQuotes")?.checked || false,
            exclude_bibliography: document.getElementById("toggleBiblio")?.checked || false,
            detect_ai: document.getElementById("toggleAI")?.checked ?? true,
            fingerprint_matching: document.getElementById("toggleFingerprint")?.checked ?? true,
            scan_mode: scanMode
        };
    }

    function setProgress(value, label) {
        if (progressFill) progressFill.style.width = `${value}%`;
        if (progressLabel) progressLabel.textContent = label;
    }

    function showProgress(show) {
        if (progressWrap) progressWrap.hidden = !show;
        if (resultCard) resultCard.hidden = show;
    }

    function animateProgress() {
        return new Promise(function (resolve) {
            showProgress(true);
            let progress = 0;
            const interval = setInterval(function () {
                progress += Math.random() * 18 + 8;
                if (progress >= 92) {
                    clearInterval(interval);
                    setProgress(92, "Analyzing similarity patterns...");
                    resolve();
                    return;
                }
                setProgress(progress, "Scanning content...");
            }, 180);
        });
    }

    function updateRing(uniquePercent) {
        if (!ringFill) return;
        const offset = circumference - (uniquePercent / 100) * circumference;
        ringFill.style.strokeDasharray = `${circumference}`;
        ringFill.style.strokeDashoffset = `${offset}`;
    }

    function renderResults(result) {
        lastReport = result;
        setProgress(100, "Scan complete");
        setTimeout(function () {
            showProgress(false);
            if (resultCard) resultCard.hidden = false;
        }, 350);

        if (uniquePct) uniquePct.textContent = `${result.unique_percent}%`;
        if (similarPct) similarPct.textContent = `${result.similarity_percent}%`;
        if (sourcesFound) sourcesFound.textContent = result.sources_found.toLocaleString();
        if (wordsScanned) wordsScanned.textContent = result.words_scanned.toLocaleString();
        updateRing(result.unique_percent);

        if (typeof updateStatisticsUI === "function") {
            updateStatisticsUI();
        }
    }

    async function runScan(requestFn) {
        checkBtn.disabled = true;
        try {
            await animateProgress();
            const result = await requestFn();
            renderResults(result);
        } catch (error) {
            showProgress(false);
            alert(error.message || "Scan failed.");
        } finally {
            checkBtn.disabled = false;
        }
    }

    if (inputText) {
        inputText.addEventListener("input", updateCounts);
        updateCounts();
    }

    tabButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            activeTab = button.dataset.tab;
            tabButtons.forEach(function (btn) {
                btn.classList.toggle("active", btn === button);
            });
            tabPanels.forEach(function (panel) {
                panel.classList.toggle("active", panel.dataset.panel === activeTab);
            });
        });
    });

    modeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            scanMode = button.dataset.mode;
            modeButtons.forEach(function (btn) {
                btn.classList.toggle("active", btn === button);
            });
        });
    });

    if (browseBtn && fileInput) {
        browseBtn.addEventListener("click", function () {
            fileInput.click();
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", function () {
            if (fileInput.files && fileInput.files[0]) {
                selectedFile = fileInput.files[0];
                if (fileName) fileName.textContent = selectedFile.name;
                if (fileSelected) fileSelected.hidden = false;
            }
        });
    }

    if (removeFile) {
        removeFile.addEventListener("click", function () {
            selectedFile = null;
            if (fileInput) fileInput.value = "";
            if (fileSelected) fileSelected.hidden = true;
        });
    }

    if (dropzone) {
        dropzone.addEventListener("dragover", function (event) {
            event.preventDefault();
            dropzone.classList.add("dragover");
        });
        dropzone.addEventListener("dragleave", function () {
            dropzone.classList.remove("dragover");
        });
        dropzone.addEventListener("drop", function (event) {
            event.preventDefault();
            dropzone.classList.remove("dragover");
            if (event.dataTransfer.files && event.dataTransfer.files[0]) {
                selectedFile = event.dataTransfer.files[0];
                if (fileName) fileName.textContent = selectedFile.name;
                if (fileSelected) fileSelected.hidden = false;
            }
        });
    }

    if (checkBtn) {
        checkBtn.addEventListener("click", function () {
            const options = getScanOptions();

            if (activeTab === "text") {
                const text = inputText ? inputText.value.trim() : "";
                if (!text) {
                    alert("Please paste some text to scan.");
                    return;
                }
                runScan(function () {
                    return window.plagifyApi.checkText({ text, ...options });
                });
                return;
            }

            if (activeTab === "file") {
                if (!selectedFile) {
                    alert("Please upload a file to scan.");
                    return;
                }
                runScan(function () {
                    const formData = new FormData();
                    formData.append("file", selectedFile);
                    formData.append("exclude_quotes", options.exclude_quotes);
                    formData.append("exclude_bibliography", options.exclude_bibliography);
                    formData.append("detect_ai", options.detect_ai);
                    formData.append("fingerprint_matching", options.fingerprint_matching);
                    formData.append("scan_mode", options.scan_mode);
                    return window.plagifyApi.checkFile(formData);
                });
                return;
            }

            const url = urlInput ? urlInput.value.trim() : "";
            if (!url) {
                alert("Please enter a URL to scan.");
                return;
            }
            const excludeDomains = excludeUrlInput
                ? excludeUrlInput.value.split(",").map(function (item) {
                      return item.trim();
                  }).filter(Boolean)
                : [];
            runScan(function () {
                return window.plagifyApi.checkUrl({
                    url,
                    exclude_domains: excludeDomains,
                    ...options
                });
            });
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", function () {
            if (inputText) inputText.value = "";
            if (urlInput) urlInput.value = "";
            if (excludeUrlInput) excludeUrlInput.value = "";
            selectedFile = null;
            if (fileInput) fileInput.value = "";
            if (fileSelected) fileSelected.hidden = true;
            showProgress(false);
            if (resultCard) resultCard.hidden = true;
            lastReport = null;
            updateCounts();
        });
    }

    if (downloadReportBtn) {
        downloadReportBtn.addEventListener("click", function () {
            if (!lastReport) {
                alert("Run a scan first.");
                return;
            }
            const blob = new Blob([JSON.stringify(lastReport, null, 2)], {
                type: "application/json"
            });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = "plagify-report.json";
            link.click();
            URL.revokeObjectURL(link.href);
        });
    }

    if (menuToggle && mainNav) {
        menuToggle.addEventListener("click", function () {
            mainNav.classList.toggle("open");
        });
    }

    document.querySelectorAll(".faq-question").forEach(function (button) {
        button.addEventListener("click", function () {
            const item = button.closest(".faq-item");
            item.classList.toggle("open");
        });
    });
});
