/**
 * List Page JavaScript - Reusable across all list views
 * Provides clickable rows and multi-column sorting functionality
 */

/**
 * Initialize clickable table rows
 * Rows with data-href attribute will navigate on click
 */
function initClickableRows() {
    document.querySelectorAll('.clickable-row[data-href]').forEach(row => {
        row.addEventListener('click', function() {
            window.location.href = this.dataset.href;
        });
    });
}

/**
 * Initialize multi-column sorting functionality
 * @param {string} currentSort - Current sort parameter from backend (e.g., "name,-date")
 */
function initSorting(currentSort) {
    const sortLinks = document.querySelectorAll('.sort-link');
    
    // Parse current sort state
    function parseSortState() {
        if (!currentSort) return [];
        return currentSort.split(',').map(s => s.trim()).filter(s => s);
    }
    
    // Update visual indicators
    function updateSortIndicators() {
        const sortFields = parseSortState();
        sortLinks.forEach(link => {
            const field = link.dataset.field;
            const indicator = link.querySelector('.sort-indicator');
            if (!indicator) return;
            
            indicator.textContent = '';
            indicator.className = 'sort-indicator';
            
            // Find field in sort list
            for (let i = 0; i < sortFields.length; i++) {
                const sortField = sortFields[i];
                const isDesc = sortField.startsWith('-');
                const fieldName = isDesc ? sortField.substring(1) : sortField;
                
                if (fieldName === field) {
                    const priority = sortFields.length > 1 ? (i + 1) : '';
                    indicator.textContent = priority + (isDesc ? '↓' : '↑');
                    indicator.className = 'sort-indicator active';
                    break;
                }
            }
        });
    }
    
    // Handle sort link clicks
    sortLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const field = this.dataset.field;
            let sortFields = parseSortState();
            
            if (e.shiftKey) {
                // Shift+click: add/modify in multi-column sort
                let found = false;
                for (let i = 0; i < sortFields.length; i++) {
                    const sortField = sortFields[i];
                    const isDesc = sortField.startsWith('-');
                    const fieldName = isDesc ? sortField.substring(1) : sortField;
                    
                    if (fieldName === field) {
                        // Toggle direction
                        sortFields[i] = isDesc ? field : '-' + field;
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    // Add new field
                    sortFields.push(field);
                }
            } else {
                // Regular click: replace all sorts with this field
                const currentField = sortFields.find(s => s === field || s === '-' + field);
                if (currentField) {
                    // Toggle direction if same field
                    sortFields = [currentField.startsWith('-') ? field : '-' + field];
                } else {
                    // New field, default ascending
                    sortFields = [field];
                }
            }
            
            // Build URL and navigate
            const url = new URL(window.location);
            url.searchParams.delete('page'); // Reset to page 1
            url.searchParams.set('sort', sortFields.join(','));
            window.location.href = url.toString();
        });
    });
    
    // Initialize indicators
    updateSortIndicators();
}

/**
 * Initialize all list page functionality
 * Call this function on DOMContentLoaded with the current sort parameter
 * @param {string} currentSort - Current sort parameter from backend
 */
function initListPage(currentSort) {
    initClickableRows();
    initSorting(currentSort || '');
}

// Auto-initialize if window.listPageSort is defined
document.addEventListener('DOMContentLoaded', function() {
    if (typeof window.listPageSort !== 'undefined') {
        initListPage(window.listPageSort);
    }
});






