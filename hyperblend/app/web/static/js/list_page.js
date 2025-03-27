// list_page.js - Base class for list pages in the application
// # hyperblend/app/web/static/js/list_page.js

/**
 * ListPage - Base class for all pages that display lists of items
 * Handles common functionality like loading items, searching, and displaying details
 */
class ListPage {
    /**
     * Initialize list page
     * @param {string} itemType - Type of items being displayed (e.g., 'molecules', 'targets')
     * @param {Object} config - Configuration options
     */
    constructor(itemType, config = {}) {
        this.itemType = itemType;
        this.items = [];
        this.filteredItems = [];
        this.currentItemId = null;
        this.editMode = false;
        
        console.log(`Initializing ${itemType} list page`);
        
        // UI Elements
        this.itemsContainer = document.getElementById('itemsContainer');
        this.itemsList = document.getElementById('itemsList');
        this.searchInput = document.getElementById('searchInput');
        this.searchButton = document.getElementById('searchButton');
        this.detailsPanel = document.getElementById('itemDetailsPanel');
        this.detailsContent = document.getElementById('itemDetailsContent');
        this.detailsTitle = document.getElementById('itemDetailsTitle');
        this.closeDetailsButton = document.getElementById('closeDetailsButton');
        this.editItemButton = document.getElementById('editItemButton');
        this.deleteItemButton = document.getElementById('deleteItemButton');
        this.itemForm = document.getElementById('itemForm');
        this.resetFormButton = document.getElementById('resetFormButton');
        this.formResult = document.getElementById('formResult');
        
        // Log which elements were found
        console.log({
            itemsContainer: !!this.itemsContainer, 
            itemsList: !!this.itemsList,
            detailsPanel: !!this.detailsPanel,
            detailsContent: !!this.detailsContent,
            detailsTitle: !!this.detailsTitle
        });
        
        // Configuration
        this.config = {
            itemsPerPage: 50,
            ...config
        };
        
        // Initialize API instance
        this.api = new HyperBlendAPI();
        
        // Apply viewport constraints
        this.applyViewportConstraints();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load items
        this.fetchItems();
    }
    
    /**
     * Apply viewport constraints to make the page fit within viewport height
     */
    applyViewportConstraints() {
        // Let the flexbox layout handle sizing - don't set explicit heights
        
        // Make list container scrollable within its space
        if (this.itemsList) {
            this.itemsList.style.overflowY = 'auto';
        }
        
        // Make details panel scrollable
        if (this.detailsPanel) {
            this.detailsPanel.style.overflowY = 'auto';
        }
        
        // Add resize events to handle any needed adjustments
        window.addEventListener('resize', () => {
            // No explicit height adjustments needed - flexbox handles it
        });
    }
    
    /**
     * Set up event listeners for search, details panel, etc.
     */
    setupEventListeners() {
        // Search functionality
        if (this.searchInput && this.searchButton) {
            this.searchButton.addEventListener('click', () => this.searchItems());
            this.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.searchItems();
                }
            });
        }
        
        // Close details panel
        if (this.closeDetailsButton) {
            this.closeDetailsButton.addEventListener('click', () => this.closeDetails());
        }
        
        // Edit button 
        if (this.editItemButton) {
            this.editItemButton.addEventListener('click', () => {
                if (this.currentItemId) {
                    this.editItem(this.currentItemId);
                }
            });
        }
        
        // Delete button
        if (this.deleteItemButton) {
            this.deleteItemButton.addEventListener('click', () => {
                if (this.currentItemId) {
                    this.confirmDeleteItem(this.currentItemId);
                }
            });
        }
        
        // Form submission
        if (this.itemForm) {
            this.itemForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFormSubmit();
            });
        }
        
        // Reset form button
        if (this.resetFormButton) {
            this.resetFormButton.addEventListener('click', () => {
                this.resetForm();
            });
        }
        
        // Close details panel on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.detailsPanel) {
                this.closeDetails();
            }
        });
    }
    
    /**
     * Fetch items from the API
     */
    async fetchItems() {
        try {
            // Make sure API is ready
            if (this.api && this.api.waitForInitialization) {
                await this.api.waitForInitialization();
            }
            
            // Show loading state
            if (this.itemsList) {
                this.itemsList.innerHTML = '<div class="loading">Loading...</div>';
            }
            
            // Call appropriate API method based on item type
            if (this.itemType === 'molecules') {
                this.items = await this.api.getMolecules(this.searchQuery || '');
            } else if (this.itemType === 'targets') {
                this.items = await this.api.getTargets(this.searchQuery || '');
            } else if (this.itemType === 'organisms') {
                this.items = await this.api.getOrganisms(this.searchQuery || '');
            } else if (this.itemType === 'effects') {
                this.items = await this.api.getEffects(this.searchQuery || '');
            }
            
            // Ensure items is always an array
            if (!Array.isArray(this.items)) {
                this.items = [];
            }
            
            this.filteredItems = [...this.items];
            this.renderItems();
            
            // If we have a current item ID, refresh its details
            if (this.currentItemId) {
                this.fetchItemDetails(this.currentItemId, true);
            }
        } catch (error) {
            console.error(`Error fetching ${this.itemType}:`, error);
            
            // Check if error might be related to back/forward cache issues
            if (error.message && (
                error.message.includes('channel is closed') || 
                error.message.includes('back/forward cache')
            )) {
                console.log('Connection issue detected during fetch, reinitializing and retrying...');
                if (this.api) {
                    this.api.initialized = false;
                    await this.api.waitForInitialization();
                    // Try again after reinitialization
                    return this.fetchItems();
                }
            }
            
            if (this.itemsList) {
                this.itemsList.innerHTML = `
                    <div class="error-message">
                        Error loading ${this.itemType}: ${error.message}
                        <button class="retry-button" onclick="try { if (window.${this.itemType}Page) { window.${this.itemType}Page.fetchItems(); } else { location.reload(); } } catch(e) { console.error('Error retrying:', e); location.reload(); }">Retry</button>
                    </div>
                `;
            }
        }
    }
    
    /**
     * Render items to the list
     */
    renderItems() {
        if (!this.itemsList) return;
        
        if (this.filteredItems.length === 0) {
            this.itemsList.innerHTML = `<div class="empty-message">No ${this.itemType} found</div>`;
            return;
        }
        
        // Build HTML for items
        const itemsHtml = this.filteredItems.map(item => this.getItemHtml(item)).join('');
        this.itemsList.innerHTML = itemsHtml;
        
        // Set a global reference so the event handlers can access it
        window.currentPage = this;
        
        // Let the external event handlers take care of attaching click events
        // The attachListItemEventListeners function handles any list item with the .list-item-card class
        if (typeof attachListItemEventListeners === 'function') {
            attachListItemEventListeners();
        } else {
            console.warn('Generic list event handler function not found, falling back to direct attachment');
            
            // Fallback: Add click event listeners directly
            const cards = this.itemsList.querySelectorAll('.list-item-card');
            cards.forEach(card => {
                const itemId = card.getAttribute('data-id');
                if (itemId) {
                    card.addEventListener('click', () => {
                        // Highlight the selected card
                        cards.forEach(c => c.classList.remove('selected'));
                        card.classList.add('selected');
                        
                        // Show details for this item
                        this.fetchItemDetails(itemId);
                    });
                }
            });
        }
    }
    
    /**
     * Generate HTML for a single item in the list
     * @param {Object} item - Item data
     * @returns {string} HTML for the item
     */
    getItemHtml(item) {
        // Create clickable card for the item (no action buttons)
        const isSelected = this.currentItemId === item.id ? 'selected' : '';
        
        return `
            <div class="list-item-card ${isSelected}" data-id="${item.id}">
                <div class="list-item-header">
                    <h3 class="list-item-title">${item.name || 'Unnamed Item'}</h3>
                </div>
                <div class="list-item-details">
                    ${item.id ? `<div class="list-item-property"><span>ID:</span> <span>${item.id}</span></div>` : ''}
                    ${item.description ? `<div class="list-item-property"><span>Description:</span> <span class="truncate-text">${this.truncateText(item.description, 50)}</span></div>` : ''}
                </div>
            </div>
        `;
    }
    
    /**
     * Search items based on search input
     */
    searchItems() {
        const query = this.searchInput.value.trim().toLowerCase();
        
        if (!query) {
            this.filteredItems = [...this.items];
        } else {
            this.filteredItems = this.items.filter(item => {
                // Search by name
                if (item.name && item.name.toLowerCase().includes(query)) {
                    return true;
                }
                
                // Search by ID
                if (item.id && item.id.toString().toLowerCase().includes(query)) {
                    return true;
                }
                
                // Search by description if available
                if (item.description && item.description.toLowerCase().includes(query)) {
                    return true;
                }
                
                // Add other searchable fields as needed
                return false;
            });
        }
        
        this.renderItems();
    }
    
    /**
     * Fetch and display details for an item
     * @param {string} itemId - ID of the item to display
     * @param {boolean} skipApiCall - If true, skip API call and use loaded items
     * @returns {Object} The item details
     */
    async fetchItemDetails(itemId, skipApiCall = false) {
        console.log(`Fetching details for ${this.itemType} with ID: ${itemId}`);
        console.log(`Details panel element:`, this.detailsPanel);
        console.log(`Details content element:`, this.detailsContent);
        
        try {
            // Make sure API is ready
            if (this.api && this.api.waitForInitialization) {
                await this.api.waitForInitialization();
            }
            
            // Look for the item in already loaded items first
            const foundItem = this.findItemById(itemId);
            let itemDetails = foundItem;
            
            // If not found in loaded items or we need fresh data, call API
            if (!skipApiCall || !foundItem) {
                // Call appropriate API method based on item type
                if (this.itemType === 'molecules') {
                    itemDetails = await this.api.getMolecule(itemId);
                } else if (this.itemType === 'targets') {
                    itemDetails = await this.api.getTarget(itemId);
                } else if (this.itemType === 'organisms') {
                    itemDetails = await this.api.getOrganism(itemId);
                } else if (this.itemType === 'effects') {
                    itemDetails = await this.api.getEffect(itemId);
                }
                
                // Update the local item if found
                if (itemDetails && foundItem) {
                    this.updateLoadedItem(itemDetails);
                }
            }
            
            if (!itemDetails) {
                throw new Error(`${this.itemType} not found`);
            }
            
            // Update current item
            this.currentItemId = itemId;
            
            // Update details panel
            if (this.detailsTitle) {
                this.detailsTitle.textContent = `${itemDetails.name || 'Unnamed'} Details`;
            }
            
            if (this.detailsContent) {
                console.log(`Updating details content with:`, itemDetails);
                const detailsHtml = this.getItemDetailHtml(itemDetails);
                console.log(`Generated HTML:`, detailsHtml);
                this.detailsContent.innerHTML = detailsHtml;
            } else {
                console.error(`Details content element not found`);
            }
            
            // Show details panel (it's always visible in the three-column layout)
            if (this.detailsPanel) {
                console.log(`Adding 'active' class to details panel`);
                this.detailsPanel.classList.add('active');
            } else {
                console.error(`Details panel element not found`);
            }
            
            return itemDetails;
        } catch (error) {
            console.error(`Error fetching ${this.itemType} details:`, error);
            
            // Check if error might be related to back/forward cache issues
            if (error.message && (
                error.message.includes('channel is closed') || 
                error.message.includes('back/forward cache')
            )) {
                console.log('Connection issue detected during fetchItemDetails, reinitializing and retrying...');
                if (this.api) {
                    this.api.initialized = false;
                    await this.api.waitForInitialization();
                    // Try again after reinitialization (but don't create an infinite loop)
                    if (!skipApiCall) {
                        return this.fetchItemDetails(itemId, skipApiCall);
                    }
                }
            }
            
            if (this.detailsContent) {
                this.detailsContent.innerHTML = `
                    <div class="error-message">
                        Error loading ${this.itemType} details: ${error.message}
                        <button class="retry-button" onclick="window.${this.itemType}Page.fetchItemDetails('${itemId}', false)">Retry</button>
                    </div>
                `;
            }
            return null;
        }
    }
    
    /**
     * Generate HTML for item details
     * @param {Object} item - The item to display
     * @returns {string} HTML representation
     */
    getItemDetailHtml(item) {
        // Base implementation with consistent structure
        return `
            <div class="details-container">
                <h2 class="details-title">${item.name || 'Unnamed Item'}</h2>
                
                <div class="details-section">
                    <h3 class="section-title">Basic Information</h3>
                    <div class="details-properties">
                        ${item.id ? `
                            <div class="property-row">
                                <span class="property-name">ID</span>
                                <span class="property-value">${item.id}</span>
                            </div>` : ''}
                        
                        ${item.description ? `
                            <div class="property-row">
                                <span class="property-name">Description</span>
                                <span class="property-value">${item.description}</span>
                            </div>` : ''}
                            
                        ${this.getAdditionalPropertiesHtml(item)}
                    </div>
                </div>
                
                ${this.getAdditionalSectionsHtml(item)}
            </div>
        `;
    }
    
    /**
     * Generate HTML for additional properties in the basic info section
     * @param {Object} item - The item data
     * @returns {string} HTML for additional properties
     */
    getAdditionalPropertiesHtml(item) {
        // Base implementation returns empty string
        // Subclasses should override this to provide type-specific properties
        return '';
    }
    
    /**
     * Generate HTML for additional sections beyond basic info
     * @param {Object} item - The item data
     * @returns {string} HTML for additional sections
     */
    getAdditionalSectionsHtml(item) {
        // Base implementation returns empty string
        // Subclasses should override this to provide type-specific sections
        return '';
    }
    
    /**
     * Close the details panel
     */
    closeDetails() {
        this.currentItemId = null;
        
        if (this.detailsPanel) {
            this.detailsPanel.classList.remove('active');
        }
        
        if (this.detailsContent) {
            this.detailsContent.innerHTML = `
                <div class="no-selection">
                    <p>Select an item from the list to view details</p>
                </div>
            `;
        }
        
        if (this.detailsTitle) {
            this.detailsTitle.textContent = `${this.itemType} Details`;
        }
    }
    
    /**
     * Populate the form with item data for editing
     * @param {string} itemId - ID of the item to edit
     */
    async editItem(itemId) {
        try {
            const item = await this.fetchItemDetails(itemId, true);
            if (!item) return;
            
            this.editMode = true;
            this.populateForm(item);
            
            // Scroll to the form
            this.itemForm.scrollIntoView({ behavior: 'smooth' });
        } catch (error) {
            console.error(`Error editing ${this.itemType}:`, error);
            this.showFormMessage(`Error editing ${this.itemType}: ${error.message}`, 'error');
        }
    }
    
    /**
     * Reset the form to add mode
     */
    resetForm() {
        this.itemForm.reset();
        this.editMode = false;
        this.currentItemId = null;
        this.formResult.classList.add('hidden');
    }
    
    /**
     * Show a message in the form result area
     * @param {string} message - Message to display
     * @param {string} type - Message type (success/error)
     */
    showFormMessage(message, type = 'success') {
        if (this.formResult) {
            this.formResult.textContent = message;
            this.formResult.className = `result-message ${type}`;
            this.formResult.classList.remove('hidden');
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                this.formResult.classList.add('hidden');
            }, 5000);
        }
    }
    
    /**
     * Handle form submission (create or update)
     */
    async handleFormSubmit() {
        try {
            const formData = this.getFormData();
            
            if (this.editMode && this.currentItemId) {
                // Update existing item
                const updatedItem = await this.updateItem(this.currentItemId, formData);
                if (updatedItem) {
                    this.showFormMessage(`${this.itemType} updated successfully`);
                    this.updateLoadedItem(updatedItem);
                    this.renderItems();
                    this.fetchItemDetails(updatedItem.id, true);
                }
            } else {
                // Create new item
                const newItem = await this.createItem(formData);
                if (newItem) {
                    this.showFormMessage(`${this.itemType} created successfully`);
                    this.items.unshift(newItem);
                    this.filteredItems = [...this.items];
                    this.renderItems();
                    this.fetchItemDetails(newItem.id, true);
                    this.resetForm();
                }
            }
        } catch (error) {
            console.error(`Error submitting ${this.itemType} form:`, error);
            this.showFormMessage(`Error: ${error.message}`, 'error');
        }
    }
    
    /**
     * Get form data as an object
     * @returns {Object} Form data object
     */
    getFormData() {
        // Base implementation - should be overridden by subclasses
        return {};
    }
    
    /**
     * Populate form fields with item data
     * @param {Object} item - Item data to populate
     */
    populateForm(item) {
        // Base implementation - should be overridden by subclasses
        console.log('populateForm() should be implemented by subclasses');
    }
    
    /**
     * Find an item by ID in the loaded items
     * @param {string} itemId - ID to find
     * @returns {Object|null} Found item or null
     */
    findItemById(itemId) {
        if (!this.items || !this.items.length) return null;
        
        return this.items.find(item => 
            item.id === itemId || 
            (item.original_id && item.original_id === itemId)
        );
    }
    
    /**
     * Update an item in the loaded items array
     * @param {Object} updatedItem - Updated item data
     */
    updateLoadedItem(updatedItem) {
        if (!updatedItem || !updatedItem.id) return;
        
        const index = this.items.findIndex(item => item.id === updatedItem.id);
        if (index !== -1) {
            this.items[index] = updatedItem;
            
            // Also update in filtered items if present
            const filteredIndex = this.filteredItems.findIndex(item => item.id === updatedItem.id);
            if (filteredIndex !== -1) {
                this.filteredItems[filteredIndex] = updatedItem;
            }
        } else {
            // If not found by ID, try to find by original_id
            const originalIdIndex = this.items.findIndex(item => 
                item.original_id && item.original_id === updatedItem.id
            );
            
            if (originalIdIndex !== -1) {
                this.items[originalIdIndex] = updatedItem;
                
                // Also update in filtered items if present
                const filteredOriginalIdIndex = this.filteredItems.findIndex(item => 
                    item.original_id && item.original_id === updatedItem.id
                );
                
                if (filteredOriginalIdIndex !== -1) {
                    this.filteredItems[filteredOriginalIdIndex] = updatedItem;
                }
            } else {
                // If not found at all, add it
                this.items.push(updatedItem);
                this.filteredItems.push(updatedItem);
            }
        }
    }
    
    /**
     * Truncate text for display
     * @param {string} text - Text to truncate
     * @param {number} maxLength - Maximum length
     * @returns {string} Truncated text
     */
    truncateText(text, maxLength = 100) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
}

// Initialize page with item type from data attribute
document.addEventListener('DOMContentLoaded', function() {
    // This function should be implemented in specific page files
    console.log('ListPage class loaded successfully');
});