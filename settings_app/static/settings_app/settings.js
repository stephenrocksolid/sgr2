/**
 * Settings Page JavaScript
 * Modern tab switching and modal handling
 */

document.addEventListener('DOMContentLoaded', function() {
    // ========================================
    // Tab Switching
    // ========================================
    const tabs = document.querySelectorAll('.settings-tab');
    const tabContents = document.querySelectorAll('.settings-tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.dataset.tab;
            
            // Update active tab button
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Update active content
            tabContents.forEach(content => {
                if (content.id === targetTab + '-tab') {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });
            
            // Update URL without page reload
            const url = new URL(window.location);
            url.searchParams.set('tab', targetTab);
            window.history.pushState({}, '', url);
        });
    });

    // ========================================
    // Modal Handling (Legacy support)
    // ========================================
    window.openSettingsModal = function(url) {
        fetch(url)
            .then(response => response.text())
            .then(html => {
                // Remove any existing modals
                document.querySelectorAll('.settings-modal-overlay').forEach(el => el.remove());
                
                // Insert the new modal
                document.body.insertAdjacentHTML('beforeend', html);
            });
    };
    
    window.closeSettingsModal = function() {
        document.querySelectorAll('.settings-modal-overlay').forEach(el => el.remove());
    };

    // ========================================
    // Close modal on outside click
    // ========================================
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('settings-modal-overlay')) {
            e.target.remove();
        }
    });

    // ========================================
    // Close modal on Escape key
    // ========================================
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.settings-modal-overlay').forEach(el => el.remove());
        }
    });

    // ========================================
    // Toggle user active status
    // ========================================
    window.toggleUserActive = function(userId) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch(`/settings/users/${userId}/toggle-active/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Trigger HTMX refresh of users table
                htmx.trigger('#users-table-container', 'userUpdated');
            } else {
                alert(data.error || 'Failed to toggle user status');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        });
    };

    // ========================================
    // Handle HTMX modal form submissions
    // ========================================
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        // If a modal was just loaded, focus the first input
        const modal = evt.target.querySelector('.settings-modal');
        if (modal) {
            const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        }
    });

    // Handle successful form submissions (204 response with HX-Trigger)
    document.body.addEventListener('htmx:beforeSwap', function(evt) {
        // If we get a 204 response, close any open modals
        if (evt.detail.xhr.status === 204) {
            document.querySelectorAll('.settings-modal-overlay').forEach(el => el.remove());
        }
    });

    // ========================================
    // Form validation helpers
    // ========================================
    window.validateSettingsForm = function(form) {
        let isValid = true;
        
        // Remove existing error states
        form.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
        form.querySelectorAll('.settings-field-error').forEach(el => {
            el.remove();
        });
        
        // Check required fields
        form.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('is-invalid');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'settings-field-error';
                errorDiv.textContent = 'This field is required';
                field.parentNode.appendChild(errorDiv);
            }
        });
        
        return isValid;
    };

    // ========================================
    // Delete confirmation
    // ========================================
    window.confirmDelete = function(message, form) {
        if (confirm(message || 'Are you sure you want to delete this item?')) {
            if (form) {
                form.submit();
            }
            return true;
        }
        return false;
    };
});

/**
 * Helper function to show toast notifications
 */
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `settings-toast settings-toast-${type}`;
    toast.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success' 
                ? '<polyline points="20 6 9 17 4 12"></polyline>' 
                : '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>'}
        </svg>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after delay
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
