/* Apache VHost Manager - Frontend JavaScript */

(function () {
    'use strict';

    // Sidebar toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            document.body.classList.toggle('sb-sidenav-toggled');
        });
    }

    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function () {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // =====================
    // Repeatable Aliases
    // =====================
    const aliasContainer = document.getElementById('alias-container');
    const addAliasBtn = document.getElementById('add-alias');

    if (addAliasBtn && aliasContainer) {
        addAliasBtn.addEventListener('click', function () {
            const index = aliasContainer.querySelectorAll('.alias-row').length;
            const row = document.createElement('div');
            row.className = 'input-group mb-2 alias-row';
            row.innerHTML = `
                <input type="text" class="form-control" name="server_alias-${index}" placeholder="www.example.com">
                <button type="button" class="btn btn-outline-danger remove-alias"><i class="bi bi-dash-lg"></i></button>
            `;
            aliasContainer.appendChild(row);
            attachRemoveHandler(row.querySelector('.remove-alias'));
        });

        // Attach to existing rows
        aliasContainer.querySelectorAll('.remove-alias').forEach(attachRemoveHandler);
    }

    // =====================
    // Repeatable Request Headers
    // =====================
    const reqHeaderContainer = document.getElementById('req-header-container');
    const addReqHeaderBtn = document.getElementById('add-req-header');

    if (addReqHeaderBtn && reqHeaderContainer) {
        addReqHeaderBtn.addEventListener('click', function () {
            const index = reqHeaderContainer.querySelectorAll('.header-row').length;
            const row = document.createElement('div');
            row.className = 'row g-2 mb-2 header-row';
            row.innerHTML = `
                <div class="col-5"><input type="text" class="form-control" name="request_headers-${index}-key" placeholder="Header Name"></div>
                <div class="col-5"><input type="text" class="form-control" name="request_headers-${index}-value" placeholder="Header Value"></div>
                <div class="col-2"><button type="button" class="btn btn-outline-danger w-100 remove-header"><i class="bi bi-dash-lg"></i></button></div>
            `;
            reqHeaderContainer.appendChild(row);
            attachRemoveHandler(row.querySelector('.remove-header'));
        });

        reqHeaderContainer.querySelectorAll('.remove-header').forEach(attachRemoveHandler);
    }

    // =====================
    // Repeatable Response Headers
    // =====================
    const respHeaderContainer = document.getElementById('resp-header-container');
    const addRespHeaderBtn = document.getElementById('add-resp-header');

    if (addRespHeaderBtn && respHeaderContainer) {
        addRespHeaderBtn.addEventListener('click', function () {
            const index = respHeaderContainer.querySelectorAll('.header-row').length;
            const row = document.createElement('div');
            row.className = 'row g-2 mb-2 header-row';
            row.innerHTML = `
                <div class="col-5"><input type="text" class="form-control" name="response_headers-${index}-key" placeholder="Header Name"></div>
                <div class="col-5"><input type="text" class="form-control" name="response_headers-${index}-value" placeholder="Header Value"></div>
                <div class="col-2"><button type="button" class="btn btn-outline-danger w-100 remove-header"><i class="bi bi-dash-lg"></i></button></div>
            `;
            respHeaderContainer.appendChild(row);
            attachRemoveHandler(row.querySelector('.remove-header'));
        });

        respHeaderContainer.querySelectorAll('.remove-header').forEach(attachRemoveHandler);
    }

    // Helper: attach remove button handler
    function attachRemoveHandler(btn) {
        if (!btn) return;
        btn.addEventListener('click', function () {
            btn.closest('.alias-row, .header-row').remove();
        });
    }

    // =====================
    // Form submission loading state
    // =====================
    document.querySelectorAll('form').forEach(function (form) {
        form.addEventListener('submit', function () {
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Processing...';
                // Store original text to restore on page navigation
                submitBtn.dataset.originalText = originalText;
            }
        });
    });

    // =====================
    // Confirmation dialogs
    // =====================
    document.querySelectorAll('form[onsubmit]').forEach(function (form) {
        const originalOnsubmit = form.onsubmit;
        form.onsubmit = function (e) {
            if (typeof originalOnsubmit === 'function') {
                return originalOnsubmit.call(form, e);
            }
        };
    });

})();

