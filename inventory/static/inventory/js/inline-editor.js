/**
 * InlineEditor - Spreadsheet-like inline editing for Django tables
 * 
 * Usage:
 *   1. Add class="editable" and data-field="field_name" to editable <td> elements
 *   2. Add data-[model]-id="pk" to <tr> elements
 *   3. Initialize: new InlineEditor('model-name', '/update/url/pattern/')
 */

class InlineEditor {
    constructor(modelName, urlPattern) {
        this.modelName = modelName;
        this.urlPattern = urlPattern;
        this.currentCell = null;
        this.originalValue = null;
        this.init();
    }
    
    init() {
        // Handle double-click on editable cells
        document.addEventListener('dblclick', (e) => {
            const cell = e.target.closest('td.editable');
            if (cell && !this.currentCell) {
                e.stopPropagation();
                this.startEdit(cell);
            }
        });
        
        // Handle click outside to save
        document.addEventListener('click', (e) => {
            if (this.currentCell && !e.target.closest('.inline-editor-wrapper')) {
                this.saveEdit();
            }
        });
    }
    
    startEdit(cell) {
        // Prevent navigation to detail page
        const row = cell.closest('tr');
        row.classList.add('editing');
        
        this.currentCell = cell;
        this.originalValue = cell.textContent.trim();
        const fieldName = cell.dataset.field;
        const dataType = cell.dataset.type || 'text';
        const currentValue = this.originalValue === '—' || this.originalValue === '' ? '' : this.originalValue;
        
        // Create input wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'inline-editor-wrapper';
        
        // Create input field based on type
        let input;
        if (dataType === 'number') {
            input = document.createElement('input');
            input.type = 'text'; // Use text to allow better control over decimals
            input.pattern = '[0-9]*\\.?[0-9]*';
            // Remove $ and commas for price fields
            const cleanValue = currentValue.replace(/[$,]/g, '');
            input.value = cleanValue;
        } else {
            input = document.createElement('input');
            input.type = 'text';
            input.value = currentValue;
        }
        
        input.className = 'inline-editor';
        wrapper.appendChild(input);
        
        // Replace cell content with input
        cell.innerHTML = '';
        cell.appendChild(wrapper);
        input.focus();
        input.select();
        
        // Save on Enter, cancel on Escape
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.saveEdit();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.cancelEdit();
            }
        });
        
        // Prevent row click from firing
        input.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }
    
    async saveEdit() {
        if (!this.currentCell) return;
        
        const input = this.currentCell.querySelector('.inline-editor');
        if (!input) return;
        
        const newValue = input.value.trim();
        const row = this.currentCell.closest('tr');
        const recordId = row.dataset[`${this.modelName}Id`];
        const fieldName = this.currentCell.dataset.field;
        const dataType = this.currentCell.dataset.type || 'text';
        
        // Validate number fields
        if (dataType === 'number' && newValue !== '') {
            if (!/^\d*\.?\d*$/.test(newValue)) {
                alert('Please enter a valid number');
                input.focus();
                return;
            }
        }
        
        // Show saving state
        this.currentCell.innerHTML = '<span class="saving">Saving...</span>';
        
        try {
            const url = this.urlPattern.replace('0', recordId);
            const response = await fetch(url, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify({
                    field: fieldName,
                    value: newValue
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Update cell with new value
                let displayValue = data.value;
                
                // Format display value
                if (displayValue === null || displayValue === '') {
                    displayValue = '—';
                } else if (fieldName === 'price' && displayValue !== '—') {
                    // Add $ if not present
                    if (!displayValue.startsWith('$')) {
                        displayValue = '$' + displayValue;
                    }
                }
                
                this.currentCell.textContent = displayValue;
                this.currentCell.classList.add('saved-flash');
                setTimeout(() => {
                    this.currentCell.classList.remove('saved-flash');
                }, 1000);
            } else {
                throw new Error(data.error || 'Save failed');
            }
        } catch (error) {
            console.error('Error saving:', error);
            alert('Error saving: ' + error.message);
            this.currentCell.textContent = this.originalValue;
        }
        
        row.classList.remove('editing');
        this.currentCell = null;
        this.originalValue = null;
    }
    
    cancelEdit() {
        if (!this.currentCell) return;
        
        this.currentCell.textContent = this.originalValue;
        const row = this.currentCell.closest('tr');
        row.classList.remove('editing');
        
        this.currentCell = null;
        this.originalValue = null;
    }
    
    getCsrfToken() {
        // Try to get from cookie first
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        if (cookieValue) return cookieValue;
        
        // Fallback to hidden input
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfInput ? csrfInput.value : '';
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InlineEditor;
}

