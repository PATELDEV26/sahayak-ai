// ============================================================
//  SahayakAI — script.js
//  Camera capture + OCR auto-fill + existing UI utilities
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

    // ── Language Toggle ──────────────────────────────────────
    const langBtn = document.getElementById('lang-toggle');
    let currentLang = localStorage.getItem('sahayak_lang') || 'en';

    function applyTranslation() {
        if (langBtn) {
            langBtn.textContent = currentLang === 'en' ? 'हिन्दी' : 'English';
        }
        document.querySelectorAll('[data-en]').forEach(el => {
            const text = el.getAttribute(`data-${currentLang}`);
            if (text) {
                if (el.tagName === 'INPUT' && el.type === 'submit') {
                    el.value = text;
                } else if (el.tagName === 'INPUT' && el.placeholder) {
                    el.placeholder = text;
                } else {
                    el.textContent = text;
                }
            }
        });
    }

    // Apply on load
    applyTranslation();

    if (langBtn) {
        langBtn.addEventListener('click', () => {
            currentLang = currentLang === 'en' ? 'hi' : 'en';
            localStorage.setItem('sahayak_lang', currentLang);
            applyTranslation();
        });
    }

    // ── Scheme Search on Result Page ─────────────────────────
    const searchInput = document.getElementById('scheme-search');
    if (searchInput) {
        searchInput.addEventListener('keyup', (e) => {
            const term = e.target.value.toLowerCase();
            document.querySelectorAll('.scheme-card').forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                card.style.display = title.includes(term) ? 'flex' : 'none';
            });
        });
    }

    // ── Eligibility Progress Bar Animation ───────────────────
    const progressBar = document.getElementById('progress-fill');
    if (progressBar) {
        const percentage = progressBar.getAttribute('data-percentage');
        setTimeout(() => { progressBar.style.width = percentage + '%'; }, 300);
    }

    // ── Helpers ──────────────────────────────────────────────
    const setStateIfPresent = (stateValue) => {
        if (!stateValue) return;
        const stateSelect = document.querySelector('select[name="state"]');
        if (!stateSelect) return;
        Array.from(stateSelect.options).forEach(opt => {
            if (opt.value.toLowerCase() === stateValue.toLowerCase()) {
                stateSelect.value = opt.value;
            }
        });
    };

    // ── Loading Overlay ──────────────────────────────────────
    function showLoadingOverlay() {
        if (document.getElementById('ai-loading-overlay')) return;
        const div = document.createElement('div');
        div.id = 'ai-loading-overlay';
        div.className = 'ai-loading-overlay';
        div.innerHTML = `
            <div class="ai-loading-card">
                <div class="ai-spinner"></div>
                <p style="font-weight:700;font-size:16px;margin:0">Reading your document...</p>
                <p style="color:#777;font-size:13px;margin:6px 0 0">Tesseract OCR is scanning </p>
            </div>`;
        document.body.appendChild(div);
    }

    function hideLoadingOverlay() {
        document.getElementById('ai-loading-overlay')?.remove();
    }

    // ── Banner helper ────────────────────────────────────────
    function showBanner(containerId, type, message) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = `
            <div class="${type === 'success' ? 'autofill-banner' : 'autofill-warning'}">
                ${message}
            </div>`;
    }

    // ── Apply OCR data to form fields ────────────────────────
    const docTypeConfig = {
        'doc-aadhaar': {
            type: 'aadhaar',
            bannerId: 'banner-aadhaar',
            apply: (data) => {
                let filled = 0;
                if (data.full_name) {
                    const el = document.querySelector('input[name="full_name"]');
                    if (el) { el.value = data.full_name; el.classList.add('autofilled'); filled++; }
                }
                if (data.date_of_birth) {
                    const parts = data.date_of_birth.split(/[-/]/);
                    if (parts.length === 3) {
                        const dob = new Date(parts[2], parts[1] - 1, parts[0]);
                        let age = new Date().getFullYear() - dob.getFullYear();
                        if (
                            new Date().getMonth() < dob.getMonth() ||
                            (new Date().getMonth() === dob.getMonth() &&
                             new Date().getDate() < dob.getDate())
                        ) { age--; }
                        const ageInput = document.querySelector('input[name="age"]');
                        if (ageInput && !isNaN(age)) { ageInput.value = age; ageInput.classList.add('autofilled'); filled++; }
                    }
                }
                if (data.address_state) { setStateIfPresent(data.address_state); filled++; }
                return filled;
            }
        },
        'doc-income': {
            type: 'income',
            bannerId: 'banner-income',
            apply: (data) => {
                let filled = 0;
                const incomeInput = document.querySelector('input[name="income"]');
                if (incomeInput && data.income) { incomeInput.value = data.income; incomeInput.classList.add('autofilled'); filled++; }
                if (data.full_name) {
                    const el = document.querySelector('input[name="full_name"]');
                    if (el && !el.value) { el.value = data.full_name; el.classList.add('autofilled'); filled++; }
                }
                if (data.address_state) { setStateIfPresent(data.address_state); filled++; }
                return filled;
            }
        },
        'doc-land': {
            type: 'land',
            bannerId: 'banner-land',
            apply: (data) => {
                let filled = 0;
                const landInput = document.querySelector('input[name="land_owned"]');
                if (landInput && data.land_owned) { landInput.value = data.land_owned; landInput.classList.add('autofilled'); filled++; }
                if (data.address_state) { setStateIfPresent(data.address_state); filled++; }
                return filled;
            }
        },
        'doc-death': {
            type: 'death',
            bannerId: 'banner-death',
            apply: (data) => {
                let filled = 0;
                if (data.full_name) {
                    const el = document.querySelector('input[name="full_name"]');
                    if (el && !el.value) { el.value = data.full_name; el.classList.add('autofilled'); filled++; }
                }
                if (data.gender) {
                    const genderSelect = document.querySelector('select[name="gender"]');
                    if (genderSelect) { genderSelect.value = data.gender; filled++; }
                }
                if (data.address_state) { setStateIfPresent(data.address_state); filled++; }
                return filled;
            }
        },
        'doc-bpl': {
            type: 'bpl',
            bannerId: 'banner-bpl',
            apply: (data) => {
                let filled = 0;
                if (data.bpl === 'Yes') {
                    const bplSelect = document.querySelector('select[name="bpl"]');
                    if (bplSelect) { bplSelect.value = 'Yes'; filled++; }
                }
                if (data.address_state) { setStateIfPresent(data.address_state); filled++; }
                return filled;
            }
        }
    };

    // ── Core OCR sender ──────────────────────────────────────
    function sendForOCR(file, inputId) {
        const config = docTypeConfig[inputId];
        if (!config) return;

        const ext = file.name.split('.').pop().toLowerCase();
        if (!['jpg', 'jpeg', 'png'].includes(ext)) {
            showBanner(config.bannerId, 'warning', '⚠️ OCR requires JPG or PNG image.');
            return;
        }

        showLoadingOverlay();

        const formData = new FormData();
        formData.append('file', file);
        formData.append('doc_type', config.type);

        fetch('/extract-document', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                hideLoadingOverlay();
                if (data.error) {
                    showBanner(config.bannerId, 'warning', '⚠️ Could not read document. Please fill manually.');
                    return;
                }
                const filled = config.apply(data);
                if (filled > 0) {
                    const conf = data.confidence;
                    const msg = conf === 'low'
                        ? '⚠️ Low confidence read — please verify all fields carefully.'
                        : `✅ ${filled} field(s) auto-filled from document! Please verify.`;
                    showBanner(config.bannerId, conf === 'low' ? 'warning' : 'success', msg);

                    // ── Language detection badge (Aadhaar only) ──────────
                    if (data.detected_language && config.type === 'aadhaar') {
                        const langNames = {
                            'guj': '🇮🇳 Gujarati',
                            'hin': '🇮🇳 Hindi',
                            'eng': '🇬🇧 English'
                        };
                        const detectedLang = langNames[data.detected_language] || 'English';
                        const langBadge = `<span style="
                            background:#E07B39;color:white;padding:3px 10px;
                            border-radius:20px;font-size:12px;font-weight:600;
                            margin-left:8px;display:inline-block;vertical-align:middle">
                            ${detectedLang} detected → Translated to English
                        </span>`;
                        const banner = document.querySelector(`#${config.bannerId} .autofill-banner`);
                        if (banner) banner.innerHTML += langBadge;
                    }
                } else {
                    showBanner(config.bannerId, 'warning', '⚠️ Could not extract details. Please fill manually.');
                }
            })
            .catch(() => {
                hideLoadingOverlay();
                showBanner(config.bannerId, 'warning', '⚠️ Something went wrong. Please fill manually.');
            });
    }

    // ── Show image preview ───────────────────────────────────
    function showPreview(imgEl, nameEl, src, name) {
        if (imgEl) { imgEl.src = src; imgEl.style.display = 'block'; }
        if (nameEl) nameEl.textContent = name;
    }

    // ── Wire up each upload widget ───────────────────────────
    // widgetId  → container div id  (e.g. 'widget-aadhaar')
    // configId  → docTypeConfig key (e.g. 'doc-aadhaar')
    // The hidden file input inside the widget must have id = configId + '-input'
    function initWidget(widgetId, configId) {
        const widget       = document.getElementById(widgetId);
        if (!widget) return;

        const fileInput    = document.getElementById(configId + '-input');
        const openCamBtn   = widget.querySelector('.open-camera-btn');
        const camContainer = widget.querySelector('.camera-container');
        const videoEl      = widget.querySelector('.camera-feed');
        const captureBtn   = widget.querySelector('.capture-btn');
        const closeCamBtn  = widget.querySelector('.close-camera-btn');
        const canvasEl     = widget.querySelector('.capture-canvas');
        const previewImg   = widget.querySelector('.doc-preview-img');
        const previewName  = widget.querySelector('.doc-preview-name');

        let stream = null;

        function stopCamera() {
            if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
            if (camContainer) camContainer.style.display = 'none';
        }

        // File input change
        if (fileInput) {
            fileInput.addEventListener('change', function () {
                const file = this.files[0];
                if (!file) return;
                const cfg = docTypeConfig[configId];
                if (file.size > 5 * 1024 * 1024) {
                    if (cfg) showBanner(cfg.bannerId, 'warning', '❌ File too large (Max 5MB)');
                    this.value = '';
                    return;
                }
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = e => showPreview(previewImg, previewName, e.target.result, file.name);
                    reader.readAsDataURL(file);
                } else {
                    showPreview(previewImg, previewName, '', file.name);
                }
                sendForOCR(file, configId);
            });
        }

        // Open camera
        if (openCamBtn) {
            openCamBtn.addEventListener('click', async () => {
                if (camContainer) camContainer.style.display = 'block';
                try {
                    stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: { ideal: 'environment' }, width: 1280, height: 720 }
                    });
                    if (videoEl) videoEl.srcObject = stream;
                } catch (err) {
                    alert('Camera access denied. Please allow camera permission or use file upload.');
                    if (camContainer) camContainer.style.display = 'none';
                }
            });
        }

        // Close camera
        if (closeCamBtn) {
            closeCamBtn.addEventListener('click', stopCamera);
        }

        // Capture photo
        if (captureBtn) {
            captureBtn.addEventListener('click', () => {
                if (!videoEl || !canvasEl) return;
                canvasEl.width  = videoEl.videoWidth;
                canvasEl.height = videoEl.videoHeight;
                canvasEl.getContext('2d').drawImage(videoEl, 0, 0);
                stopCamera();

                const dataUrl = canvasEl.toDataURL('image/jpeg', 0.95);
                showPreview(previewImg, previewName, dataUrl, 'Camera capture');

                canvasEl.toBlob(blob => {
                    const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' });
                    sendForOCR(file, configId);
                }, 'image/jpeg', 0.95);
            });
        }
    }

    // Initialise all widgets present on the page
    // widgetId              configId (= docTypeConfig key AND file-input prefix)
    initWidget('widget-aadhaar',   'doc-aadhaar');
    initWidget('widget-income',    'doc-income');
    initWidget('widget-land',      'doc-land');
    initWidget('widget-death',     'doc-death');
    initWidget('widget-bpl',       'doc-bpl');
    initWidget('widget-marksheet', 'doc-marksheet');
    initWidget('widget-bank',      'doc-bank');
});