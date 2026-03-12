document.addEventListener('DOMContentLoaded', () => {
    
    // Language Toggle logic
    const langBtn = document.getElementById('lang-toggle');
    let currentLang = 'en';

    if (langBtn) {
        langBtn.addEventListener('click', () => {
            currentLang = currentLang === 'en' ? 'hi' : 'en';
            langBtn.textContent = currentLang === 'en' ? 'हिन्दी' : 'English';
            
            document.querySelectorAll('[data-en]').forEach(el => {
                const text = el.getAttribute(`data-${currentLang}`);
                if (text) el.textContent = text;
            });
        });
    }

    // File Validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            const feedbackId = e.target.id + '-feedback';
            let feedbackEl = document.getElementById(feedbackId);
            
            if (!feedbackEl) {
                feedbackEl = document.createElement('span');
                feedbackEl.id = feedbackId;
                feedbackEl.className = 'upload-feedback';
                e.target.parentNode.appendChild(feedbackEl);
            }

            if (file) {
                if (file.size > 5 * 1024 * 1024) {
                    feedbackEl.textContent = "❌ File too large (Max 5MB)";
                    feedbackEl.className = 'upload-feedback invalid-file';
                    e.target.value = ''; // Reset
                } else {
                    feedbackEl.textContent = `✅ ${file.name} ready`;
                    feedbackEl.className = 'upload-feedback valid-file';
                }
            }
        });
    });

    // Scheme Search on Result Page
    const searchInput = document.getElementById('scheme-search');
    if (searchInput) {
        searchInput.addEventListener('keyup', (e) => {
            const term = e.target.value.toLowerCase();
            const cards = document.querySelectorAll('.scheme-card');
            
            cards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                if (title.includes(term)) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Eligibility Progress Bar Animation
    const progressBar = document.getElementById('progress-fill');
    if (progressBar) {
        const percentage = progressBar.getAttribute('data-percentage');
        setTimeout(() => {
            progressBar.style.width = percentage + '%';
        }, 300);
    }
});
