document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        // Find either a standard button of type submit, or explicitly find .btn-black (used on login/register)
        const submitBtn = form.querySelector('button[type="submit"]') || form.querySelector('input[type="submit"]');

        const checkFormValidity = () => {
            if (!submitBtn) return;
            // Let the browser handle standard validation (e.g. required dropdowns), 
            // so we don't prematurely block clicks unless we're strictly enforcing custom UI.
            // Leaving Native form validation untouched to let user trigger tooltips.
        };

        // Initial check
        checkFormValidity();

        // Listen for input changes
        form.addEventListener('input', checkFormValidity);
        form.addEventListener('change', checkFormValidity);

        form.addEventListener('submit', function (event) {
            // Check if form is valid (if using browser validation)
            if (!form.checkValidity()) {
                // If form is invalid, let the browser handle the error
                return;
            }

            if (submitBtn) {
                // Prevent double submission
                if (submitBtn.classList.contains('loading')) {
                    event.preventDefault();
                    return;
                }

                // Add loading class
                submitBtn.classList.add('loading');

                // Save original content safely
                const originalContent = submitBtn.innerHTML;
                submitBtn.dataset.originalContent = originalContent;

                // Determine loading text based on current text
                const btnText = submitBtn.innerText.trim().toLowerCase();
                let loadingText = "Processing...";

                if (btnText.includes("sign in") || btnText.includes("login") || btnText.includes("log in")) {
                    loadingText = "Signing In...";
                } else if (btnText.includes("create account") || btnText.includes("register")) {
                    loadingText = "Creating Account...";
                } else if (btnText.includes("save") || btnText.includes("submit")) {
                    loadingText = "Saving...";
                } else if (btnText.includes("update") || btnText.includes("add")) {
                    loadingText = "Updating...";
                } else if (btnText.includes("upload") || btnText.includes("import")) {
                    loadingText = "Importing...";
                } else if (btnText.includes("start") || btnText.includes("allocate") || btnText.includes("run")) {
                    loadingText = "Working...";
                }

                // SVG Spinner
                const spinner = `<svg style="animation: spin 1s linear infinite; height: 1.1rem; width: 1.1rem; display: inline-block; vertical-align: middle; margin-right: 0.5rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" stroke-opacity="0.25"></circle>
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>`;

                // Inject spinner and text
                submitBtn.innerHTML = spinner + `<span>${loadingText}</span>`;

                // Use pointer-events none just in case disabled blocks form submission value
                submitBtn.style.pointerEvents = 'none';
                submitBtn.style.opacity = '0.7';

                // Use setTimeout to allow form to submit before disabling, 
                // as disabling a button immediately can sometimes prevent form submission in some browsers.
                setTimeout(() => {
                    submitBtn.disabled = true;
                }, 10);
            }
        });
    });

    // Restore button state when navigating back (bfcache)
    window.addEventListener('pageshow', function (event) {
        // Always check for loading buttons regardless of persistence
        const loadingBtns = document.querySelectorAll('.btn.loading');
        loadingBtns.forEach(btn => {
            btn.classList.remove('loading');
            if (btn.dataset.originalContent) {
                btn.innerHTML = btn.dataset.originalContent;
            }
        });
    });

    // File input enhancement
    const fileInputs = document.querySelectorAll('.file-input');
    fileInputs.forEach(input => {
        input.addEventListener('change', function () {
            // Find the display text element relative to this input
            // Assuming markup: <label class="upload-area"> <p>Text</p> <input> </label>
            const label = this.closest('.upload-area');
            if (!label) return;

            const fileNameDisplay = label.querySelector('p'); // Get the first paragraph or specific ID if unique

            if (this.files && this.files.length > 0) {
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = this.files[0].name;
                    fileNameDisplay.style.color = 'var(--text-main)';
                    fileNameDisplay.style.fontWeight = '500';
                }
            } else {
                // Handle clear selection
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = "Click to upload sheet";
                    fileNameDisplay.style.color = ''; // Reset to CSS default
                    fileNameDisplay.style.fontWeight = '';
                }
            }
        });
    });
});
