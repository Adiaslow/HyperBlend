class ListPage {
    constructor(itemType) {
        this.itemType = itemType;
        this.items = [];
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.initialized = false;
        this.initializationAttempts = 0;
        this.maxAttempts = 10;
        this.initializationInterval = 100; // ms between retries
        this.isLoading = false;
        this.initialLoadComplete = false;  // New flag to track initial load
        this._searchHandler = null; // Store reference to search handler

        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    initialize() {
        try {
            // If already initialized, don't do anything
            if (this.initialized) {
                console.log(`${this.itemType} list page already initialized`);
                return;
            }

            console.log(`Starting initialization for ${this.itemType} list page...`);
            
            // First ensure the API client exists
            if (!window.api) {
                return this.retryInitialization('API client not available');
            }

            // Then check if it has the required methods for this specific type
            if (!this.validateAPIClient()) {
                return this.retryInitialization(`API method list${this.itemType}s not found`);
            }

            console.log(`Initializing ${this.itemType} list page components...`);
            
            // Store API reference
            this.api = window.api;

            // Initialize UI elements
            this.initializeElements();
            
            // Set up event listeners FIRST
            this.initializeEventListeners();
            
            // Then load initial data for this specific type
            this.loadItems();
            
            this.initialized = true;
            console.log(`${this.itemType} list page initialized successfully`);
        } catch (error) {
            console.error('Error during initialization:', error);
            this.handleInitializationError(error);
        }
    }

    validateAPIClient() {
        const methodName = `list${this.itemType}s`;
        return typeof window.api[methodName] === 'function';
    }

    retryInitialization(reason) {
        this.initializationAttempts++;
        if (this.initializationAttempts < this.maxAttempts) {
            console.log(`${reason}, retrying... (Attempt ${this.initializationAttempts}/${this.maxAttempts})`);
            setTimeout(() => this.initialize(), this.initializationInterval);
        } else {
            this.handleInitializationError(new Error(`Initialization failed after ${this.maxAttempts} attempts: ${reason}`));
        }
    }

    handleInitializationError(error) {
        console.error('Fatal initialization error:', error);
        this.showError('Unable to initialize list page. Please refresh the page or contact support if the problem persists.');
    }

    initializeElements() {
        console.log('Initializing list page elements...');
        
        // Get list container
        this.listContainer = document.querySelector('.list-container');
        if (!this.listContainer) {
            throw new Error('List container not found');
        }
        console.log('Found list container');

        // Get item list
        this.itemList = document.getElementById('itemList');
        if (!this.itemList) {
            throw new Error('Item list element not found');
        }
        console.log('Found item list');

        // Get other elements
        this.searchInput = document.getElementById('searchInput');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.itemModal = document.getElementById('itemModal');
        this.confirmModal = document.getElementById('confirmModal');
        this.paginationContainer = document.getElementById('pagination');
        this.itemCountDisplay = document.getElementById('itemCount');

        // Initialize loading state
        if (this.loadingSpinner) {
            this.hideLoading();
        } else {
            console.warn('Loading spinner element not found');
        }

        console.log('List page elements initialized');
    }

    initializeEventListeners() {
        // Search with debounce
        if (this.searchInput) {
            // Clear any existing value WITHOUT triggering the input event
            this.searchInput.value = '';
            
            // Store reference to the handler for cleanup
            this._searchHandler = debounce((event) => {
                const query = event.target.value.trim();
                // Only trigger search if we've completed initial load
                if (this.initialLoadComplete) {
                    this.loadItems(query);
                }
            }, 300);
            
            this.searchInput.addEventListener('input', this._searchHandler);
        }

        // Item click handler
        if (this.itemList) {
            this.itemList.addEventListener('click', (event) => {
                const itemElement = event.target.closest('.item');
                if (itemElement) {
                    const itemId = itemElement.dataset.id;
                    this.handleItemClick(itemId);
                }
            });
        }

        // Modal close handlers
        if (this.itemModal) {
            const closeButtons = this.itemModal.querySelectorAll('.close-modal');
            closeButtons.forEach(button => {
                button.addEventListener('click', () => this.closeModal(this.itemModal));
            });
        }

        if (this.confirmModal) {
            const closeButtons = this.confirmModal.querySelectorAll('.close-modal');
            closeButtons.forEach(button => {
                button.addEventListener('click', () => this.closeModal(this.confirmModal));
            });
        }
    }

    async loadItems(query = '') {
        try {
            // If we're already loading, skip
            if (this.isLoading) {
                console.log('Skipping load - already loading');
                return;
            }

            this.isLoading = true;
            this.showLoading();
            console.log(`Loading ${this.itemType}s with query:`, query);
            
            // Get the specific method for this item type
            const method = `list${this.itemType}s`;
            if (typeof this.api[method] !== 'function') {
                throw new Error(`API method ${method} not found`);
            }
            
            // Only call the API method for this specific type
            const response = await this.api[method](query || undefined);
            console.log(`Received ${this.itemType}s response:`, response);
            
            // Handle response based on structure
            let newItems = [];
            if (response && typeof response === 'object') {
                if (Array.isArray(response)) {
                    newItems = response;
                } else if (response.status === 'success') {
                    // Extract items from the response based on item type
                    const key = this.itemType.toLowerCase() + 's';
                    if (response[key] && Array.isArray(response[key])) {
                        newItems = response[key];
                    } else {
                        console.warn(`No ${key} array found in response:`, response);
                    }
                } else if (response.items && Array.isArray(response.items)) {
                    newItems = response.items;
                } else {
                    console.warn('Unexpected response structure:', response);
                }
            } else {
                console.warn('Invalid response:', response);
            }
            
            // Update items if:
            // 1. We have new items OR
            // 2. We have a search query OR
            // 3. This is our first load
            if (newItems.length > 0 || query !== '' || !this.initialLoadComplete) {
                this.items = newItems;
                console.log(`Processed ${this.items.length} ${this.itemType}s:`, this.items);
            }
            
            // Always render items, even if empty
            this.renderItems();
            this.updateItemCount();
            
            // Mark initial load as complete
            if (!this.initialLoadComplete) {
                this.initialLoadComplete = true;
                console.log('Initial load complete');
            }
        } catch (error) {
            console.error('Error loading items:', error);
            this.showError(`Error loading ${this.itemType}s. Please try again.`);
            // Show error state in the list
            if (this.itemList) {
                this.itemList.innerHTML = `
                    <div class="p-4 text-red-600 bg-red-50 border border-red-200 rounded">
                        <p class="font-medium">Error loading ${this.itemType}s</p>
                        <p class="text-sm">${error.message}</p>
                    </div>
                `;
            }
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    renderItems() {
        if (!this.itemList) {
            console.error('Item list element not found');
            return;
        }

        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pageItems = this.items.slice(startIndex, endIndex);

        console.log(`Rendering ${pageItems.length} items for page ${this.currentPage}`);

        if (pageItems.length === 0) {
            this.itemList.innerHTML = `
                <div class="p-4 text-gray-600 bg-gray-50 border border-gray-200 rounded">
                    No ${this.itemType}s found
                </div>
            `;
            return;
        }

        this.itemList.innerHTML = pageItems.map(item => this.renderItemHtml(item)).join('');
        this.updatePagination();
    }

    renderItemHtml(item) {
        if (!item || !item.name) {
            console.warn('Invalid item data:', item);
            return '';
        }

        // Ensure we have a valid ID and it's a string
        const rawId = item.id != null ? String(item.id) : '';
        const itemId = this.cleanItemId(rawId) || rawId;

        return `
            <div class="item p-4 border rounded-lg mb-4 hover:bg-gray-50 cursor-pointer" data-id="${itemId}">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="text-lg font-semibold">${item.name}</h3>
                        ${item.description ? `<p class="text-gray-600 mt-1">${this.truncateString(item.description, 150)}</p>` : ''}
                    </div>
                    ${this.renderItemBadge(item)}
                </div>
                ${this.renderItemSpecificInfo(item)}
            </div>
        `;
    }

    renderItemBadge(item) {
        const type = item.type ? item.type.toLowerCase() : this.itemType.toLowerCase();
        return `
            <span class="px-2 py-1 rounded ${this.getBadgeClasses(type)} text-sm">
                ${item.type || type}
            </span>
        `;
    }

    getBadgeClasses(type) {
        const classes = {
            molecule: 'bg-green-100 text-green-800',
            target: 'bg-blue-100 text-blue-800',
            organism: 'bg-purple-100 text-purple-800',
            effect: 'bg-yellow-100 text-yellow-800',
            physiological: 'bg-red-100 text-red-800',
            behavioral: 'bg-blue-100 text-blue-800',
            perceptual: 'bg-purple-100 text-purple-800',
            emotional: 'bg-pink-100 text-pink-800',
            cognitive: 'bg-indigo-100 text-indigo-800',
            consciousness: 'bg-teal-100 text-teal-800',
            therapeutic: 'bg-green-100 text-green-800',
            interpersonal: 'bg-orange-100 text-orange-800'
        };
        return classes[type] || 'bg-gray-100 text-gray-800';
    }

    truncateString(str, length) {
        if (!str) return '';
        return str.length > length ? str.substring(0, length) + '...' : str;
    }

    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    renderItemSpecificInfo(item) {
        switch (this.itemType.toLowerCase()) {
            case 'molecule':
                return `
                    <div class="mt-2 text-sm text-gray-500">
                        ${item.formula ? `<span class="mr-4">Formula: ${item.formula}</span>` : ''}
                        ${item.molecular_weight ? `<span>MW: ${item.molecular_weight}</span>` : ''}
                    </div>
                `;
            case 'target':
                return `
                    <div class="mt-2 text-sm text-gray-500">
                        ${item.organism ? `<span class="mr-4">Organism: ${item.organism}</span>` : ''}
                        ${item.type ? `<span>Type: ${item.type}</span>` : ''}
                    </div>
                `;
            case 'organism':
                return `
                    <div class="mt-2 text-sm text-gray-500">
                        ${item.taxonomy ? `<span>Taxonomy: ${item.taxonomy}</span>` : ''}
                    </div>
                `;
            case 'effect':
                return `
                    <div class="mt-2 text-sm text-gray-500">
                        ${item.category ? `<span>Category: ${item.category}</span>` : ''}
                    </div>
                `;
            default:
                return '';
        }
    }

    async handleItemClick(itemId) {
        try {
            if (!itemId) {
                throw new Error('No item ID provided');
            }

            // Clean up and validate the item ID
            const cleanId = this.cleanItemId(itemId);
            if (!cleanId) {
                throw new Error('Invalid item ID format');
            }

            this.showLoading();
            const item = await this.api.getMolecule(cleanId);
            
            if (!item) {
                throw new Error('Item not found');
            }
            
            // Show item details
            this.showInfoContainer(item);
        } catch (error) {
            console.error('Error fetching item details:', error);
            
            let errorMessage = 'Error loading item details. ';
            if (error.message.includes('503')) {
                errorMessage += 'The service is temporarily unavailable. Please try again in a few moments.';
            } else if (error.message.includes('Invalid item ID')) {
                errorMessage += 'The item ID format is invalid. Please try refreshing the page.';
            } else {
                errorMessage += error.message;
            }
            
            this.showError(errorMessage);
            
            // If we have an info container, show the error there too
            if (this.infoContent) {
                this.infoContent.innerHTML = `
                    <div class="p-4 text-red-600 bg-red-50 border border-red-200 rounded">
                        <p class="font-medium">Error</p>
                        <p class="text-sm">${errorMessage}</p>
                        <button onclick="window.location.reload()" class="mt-2 px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200">
                            Retry
                        </button>
                    </div>
                `;
            }
        } finally {
            this.hideLoading();
        }
    }

    cleanItemId(itemId) {
        // Handle null, undefined, or non-string input
        if (!itemId || typeof itemId !== 'string') {
            console.warn('Invalid itemId provided to cleanItemId:', itemId);
            return null;
        }
        
        // If the ID contains colons, take the UUID part (assuming format like "4:uuid:66")
        if (itemId.includes(':')) {
            const parts = itemId.split(':');
            // If we have a UUID in the middle, return it
            if (parts.length === 3 && this.isValidUUID(parts[1])) {
                return parts[1];
            }
            // If the whole thing is a UUID, return it
            if (parts.length === 1 && this.isValidUUID(parts[0])) {
                return parts[0];
            }
            return null;
        }
        
        // If it's already a clean UUID, return it
        return this.isValidUUID(itemId) ? itemId : null;
    }

    isValidUUID(uuid) {
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        return uuidRegex.test(uuid);
    }

    showItemModal(item) {
        if (!this.itemModal) return;

        const modalContent = this.renderModalContent(item);
        this.itemModal.querySelector('.modal-content').innerHTML = modalContent;
        this.itemModal.classList.remove('hidden');
    }

    renderModalContent(item) {
        return `
            <div class="p-6">
                <div class="flex justify-between items-start mb-4">
                    <h2 class="text-2xl font-bold">${item.name}</h2>
                    <button class="close-modal text-gray-500 hover:text-gray-700">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                ${this.renderModalSpecificContent(item)}
            </div>
        `;
    }

    renderModalSpecificContent(item) {
        switch (this.itemType.toLowerCase()) {
            case 'molecule':
                return `
                    <div class="space-y-4">
                        ${item.description ? `<p class="text-gray-600">${item.description}</p>` : ''}
                        <div class="grid grid-cols-2 gap-4">
                            ${item.formula ? `<div><span class="font-semibold">Formula:</span> ${item.formula}</div>` : ''}
                            ${item.molecular_weight ? `<div><span class="font-semibold">MW:</span> ${item.molecular_weight}</div>` : ''}
                            ${item.smiles ? `<div class="col-span-2"><span class="font-semibold">SMILES:</span> <span class="font-mono text-sm">${item.smiles}</span></div>` : ''}
                        </div>
                        ${this.renderRelatedItems(item)}
                    </div>
                `;
            case 'target':
                return `
                    <div class="space-y-4">
                        ${item.description ? `<p class="text-gray-600">${item.description}</p>` : ''}
                        <div class="grid grid-cols-2 gap-4">
                            ${item.organism ? `<div><span class="font-semibold">Organism:</span> ${item.organism}</div>` : ''}
                            ${item.type ? `<div><span class="font-semibold">Type:</span> ${item.type}</div>` : ''}
                        </div>
                        ${this.renderRelatedItems(item)}
                    </div>
                `;
            case 'organism':
                return `
                    <div class="space-y-4">
                        ${item.description ? `<p class="text-gray-600">${item.description}</p>` : ''}
                        <div class="grid grid-cols-2 gap-4">
                            ${item.taxonomy ? `<div><span class="font-semibold">Taxonomy:</span> ${item.taxonomy}</div>` : ''}
                        </div>
                        ${this.renderRelatedItems(item)}
                    </div>
                `;
            case 'effect':
                return `
                    <div class="space-y-4">
                        ${item.description ? `<p class="text-gray-600">${item.description}</p>` : ''}
                        <div class="grid grid-cols-2 gap-4">
                            ${item.category ? `<div><span class="font-semibold">Category:</span> ${item.category}</div>` : ''}
                        </div>
                        ${this.renderRelatedItems(item)}
                    </div>
                `;
            default:
                return '';
        }
    }

    renderRelatedItems(item) {
        if (!item.related_items || item.related_items.length === 0) return '';

        return `
            <div class="mt-6">
                <h3 class="text-lg font-semibold mb-3">Related Items</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    ${item.related_items.map(related => `
                        <div class="p-3 border rounded-lg">
                            <div class="font-medium">${related.name}</div>
                            <div class="text-sm text-gray-500">${related.type}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    async searchDatabase(query) {
        // Only search if there's actually a query
        if (query) {
            await this.loadItems(query);
        } else {
            // If no query, load all items
            await this.loadItems();
        }
    }

    updatePagination() {
        if (!this.paginationContainer) return;

        const totalPages = Math.ceil(this.items.length / this.itemsPerPage);
        let paginationHtml = '';

        if (totalPages > 1) {
            paginationHtml = `
                <div class="flex justify-center space-x-2">
                    <button class="pagination-btn" ${this.currentPage === 1 ? 'disabled' : ''} 
                            onclick="this.currentPage = 1; this.renderItems()">
                        First
                    </button>
                    <button class="pagination-btn" ${this.currentPage === 1 ? 'disabled' : ''} 
                            onclick="this.currentPage--; this.renderItems()">
                        Previous
                    </button>
                    <span class="px-4 py-2">Page ${this.currentPage} of ${totalPages}</span>
                    <button class="pagination-btn" ${this.currentPage === totalPages ? 'disabled' : ''} 
                            onclick="this.currentPage++; this.renderItems()">
                        Next
                    </button>
                    <button class="pagination-btn" ${this.currentPage === totalPages ? 'disabled' : ''} 
                            onclick="this.currentPage = ${totalPages}; this.renderItems()">
                        Last
                    </button>
                </div>
            `;
        }

        this.paginationContainer.innerHTML = paginationHtml;
    }

    updateItemCount() {
        if (this.itemCountDisplay) {
            const count = this.items.length;
            this.itemCountDisplay.textContent = `${count.toLocaleString()} ${this.itemType}${count === 1 ? '' : 's'}`;
        }
    }

    showLoading() {
        if (this.loadingSpinner) {
            this.loadingSpinner.classList.remove('hidden');
        }
    }

    hideLoading() {
        if (this.loadingSpinner) {
            this.loadingSpinner.classList.add('hidden');
        }
    }

    showError(message) {
        const errorContainer = document.getElementById('errorContainer') || this.createErrorContainer();
        errorContainer.textContent = message;
        errorContainer.classList.remove('hidden');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorContainer.classList.add('hidden');
        }, 5000);
    }

    createErrorContainer() {
        const container = document.createElement('div');
        container.id = 'errorContainer';
        container.className = 'error-message fixed top-4 right-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg hidden';
        document.body.appendChild(container);
        return container;
    }

    closeModal(modal) {
        if (modal) {
            modal.classList.add('hidden');
        }
    }
}

// Initialize page with item type from data attribute
async function initializeListPage() {
    // Guard against multiple initializations using a more robust check
    if (window.listPage && window.listPage.initialized) {
        console.log('List page already initialized and running, skipping...');
        return;
    }

    const container = document.querySelector('.list-container');
    if (!container) {
        console.error('List container not found');
        return;
    }

    const itemType = container.querySelector('.list-header h2')?.textContent?.trim()?.replace(/s$/, '') || '';
    if (!itemType) {
        console.error('No item type found in header');
        return;
    }

    try {
        console.log(`Initializing ${itemType} list page...`);
        
        // Wait for API client to be available
        let attempts = 0;
        const maxAttempts = 50;
        while (!window.api && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (!window.api) {
            throw new Error('API client not found after waiting');
        }

        // Wait for API client to be initialized
        await window.api.waitForInitialization();
        
        // Create list page instance only if it doesn't exist or isn't properly initialized
        if (!window.listPage || !window.listPage.initialized) {
            // Clean up any existing instance
            if (window.listPage) {
                console.log('Cleaning up existing uninitialized instance...');
                // Remove event listeners if they exist
                if (window.listPage.searchInput) {
                    window.listPage.searchInput.removeEventListener('input', window.listPage._searchHandler);
                }
            }
            window.listPage = new ListPage(itemType);
        }
    } catch (error) {
        console.error('Error initializing list page:', error);
        const errorContainer = document.createElement('div');
        errorContainer.className = 'error-message fixed top-4 right-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg';
        errorContainer.textContent = 'Unable to initialize list page. Please refresh the page or contact support if the problem persists.';
        document.body.appendChild(errorContainer);
    }
}

// Start initialization when DOM is ready - with improved guard
if (!window.listPageInitializing) {
    window.listPageInitializing = true;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initializeListPage().finally(() => {
                window.listPageInitializing = false;
            });
        });
    } else {
        initializeListPage().finally(() => {
            window.listPageInitializing = false;
        });
    }
} 