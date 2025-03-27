/**
 * TargetPage class - Manages target listing, details, and interactions
 */
class TargetPage extends ListPage {
    /**
     * Initialize the target page
     * @param {Object} config - Configuration options
     */
    constructor(config = {}) {
        // Call parent constructor with type 'targets'
        super('targets', config);
        
        this.api = window.api || new HyperBlendAPI();
        
        // Initialize page elements
        this.initializePage();
    }
    
    /**
     * Initialize page-specific elements and event listeners
     */
    initializePage() {
        // Set up event listeners for add target form
        this.setupAddTargetForm();
        
        // Add any other target-specific initialization
        console.log('Target page initialized');
    }
    
    /**
     * Set up the add target form functionality
     */
    setupAddTargetForm() {
        // Target-specific form setup can go here
    }
    
    /**
     * Override parent method for custom item formatting
     * @param {Object} item - Target data
     * @returns {string} HTML for the list item
     */
    getItemHtml(item) {
        // Create clickable card for the target
        const isSelected = this.currentItemId === item.id ? 'selected' : '';
        
        return `
            <div class="list-item-card ${isSelected}" data-id="${item.id}">
                <div class="list-item-header">
                    <h3 class="list-item-title">${item.name || 'Unnamed Target'}</h3>
                </div>
                <div class="list-item-details">
                    ${item.type ? `<div class="list-item-property"><span>Type:</span> <span>${item.type}</span></div>` : ''}
                    ${item.organism ? `<div class="list-item-property"><span>Organism:</span> <span>${item.organism}</span></div>` : ''}
                </div>
            </div>
        `;
    }
    
    /**
     * Get the HTML for detailed item view
     * @param {Object} item - Target data
     * @returns {string} HTML for the detailed view
     */
    getItemDetailHtml(item) {
        return `
            <div class="details-container">
                <h2 class="details-title">${item.name || 'Unnamed Target'}</h2>
                
                <!-- Basic info section -->
                <div class="details-section">
                    <h3 class="section-title">Target Information</h3>
                    <div class="details-properties">
                        ${this.getAdditionalPropertiesHtml(item)}
                    </div>
                </div>
                
                ${this.getAdditionalSectionsHtml(item)}
            </div>
        `;
    }
    
    /**
     * Override parent method for getting additional properties
     * @param {Object} item - Target data
     * @returns {string} HTML for additional properties
     */
    getAdditionalPropertiesHtml(item) {
        return `
            ${item.type ? `
                <div class="property-row">
                    <span class="property-name">Type</span>
                    <span class="property-value">${item.type}</span>
                </div>` : ''}
            
            ${item.organism ? `
                <div class="property-row">
                    <span class="property-name">Organism</span>
                    <span class="property-value">${item.organism}</span>
                </div>` : ''}
            
            ${item.gene_name ? `
                <div class="property-row">
                    <span class="property-name">Gene Name</span>
                    <span class="property-value">${item.gene_name}</span>
                </div>` : ''}
            
            ${item.external_id ? `
                <div class="property-row">
                    <span class="property-name">External ID</span>
                    <span class="property-value">${item.external_id}</span>
                </div>` : ''}
        `;
    }
    
    /**
     * Override parent method for getting additional sections
     * @param {Object} item - Target data
     * @returns {string} HTML for additional sections
     */
    getAdditionalSectionsHtml(item) {
        let html = '';
        
        // Add sequence section if available
        if (item.sequence) {
            html += `
                <div class="details-section">
                    <h3 class="section-title">Sequence</h3>
                    <div class="sequence-container">${item.sequence}</div>
                </div>`;
        }
        
        // Add molecules section if available
        if (item.molecules && item.molecules.length > 0) {
            html += this.renderMoleculesSection(item);
        }
        
        return html;
    }
    
    /**
     * Render the associated molecules section
     * @param {Object} item - Target data with molecules
     * @returns {string} HTML for the molecules section
     */
    renderMoleculesSection(item) {
        if (!item.molecules || item.molecules.length === 0) {
            return '';
        }
        
        const moleculesHtml = item.molecules.map(mol => `
            <div class="related-item">
                <div class="related-item-name">${mol.name || 'Unnamed Molecule'}</div>
                ${mol.formula ? `<div class="related-item-detail"><span>Formula:</span> ${mol.formula}</div>` : ''}
                ${mol.activity_value ? `
                    <div class="related-item-detail">
                        <span>Activity:</span> ${mol.activity_value} ${mol.activity_unit || ''}
                        ${mol.activity_type ? `(${mol.activity_type})` : ''}
                    </div>` : ''}
            </div>
        `).join('');
        
        return `
            <div class="details-section">
                <h3 class="section-title">Associated Molecules</h3>
                <div class="related-items">
                    ${moleculesHtml}
                </div>
            </div>
        `;
    }
}

// Initialize when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('targets.js: Document loaded, initializing');
    
    // Only initialize if not already initialized
    if (!window.targetPage) {
        window.targetPage = new TargetPage();
        console.log('Target page initialized');
    }
}); 