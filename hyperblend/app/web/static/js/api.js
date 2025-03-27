// hyperblend/app/web/static/js/api.js

/**
 * HyperBlendAPI - Client for interacting with the HyperBlend API
 */
class HyperBlendAPI {
    /**
     * Initialize the API client
     */
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || '';
        this.apiRoot = `${this.baseUrl}/api`;
        this.initialized = false;
        this.initializationPromise = null;
        this.lastActivity = Date.now();
    }

    async waitForInitialization() {
        // Check if we need to re-initialize due to inactivity or back/forward cache
        if (this.initialized && Date.now() - this.lastActivity > 60000) {
            console.log('API client inactive for too long, reinitializing...');
            this.initialized = false;
            this.initializationPromise = null;
        }

        if (this.initialized) {
            return true;
        }

        if (!this.initializationPromise) {
            this.initializationPromise = this.initialize();
        }

        return this.initializationPromise;
    }

    async initialize() {
        try {
            console.log('Initializing API client...');
            
            // Try to access storage, but don't fail if it's not available
            try {
                // Check if we have cached credentials or settings
                if (window.localStorage) {
                    const cachedData = window.localStorage.getItem('hyperblend_api_cache');
                    if (cachedData) {
                        const data = JSON.parse(cachedData);
                        // Use cached data if available and not expired
                        if (data && data.expires > Date.now()) {
                            Object.assign(this, data.settings);
                        }
                    }
                }
            } catch (storageError) {
                console.warn('Storage access not available:', storageError);
                // Continue initialization without storage access
            }

            // Make a simple test request to verify API connectivity
            const response = await fetch(`${this.baseUrl}/api/statistics`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            await response.json();
            
            this.initialized = true;
            this.lastActivity = Date.now();
            console.log('API client initialized successfully');
            return true;
        } catch (error) {
            console.error('Error initializing API client:', error);
            this.initialized = false;
            throw error;
        }
    }

    /**
     * Make a fetch request and handle common responses
     * @param {string} path - API path to request
     * @param {Object} options - Fetch options
     * @param {boolean} useApiRoot - Whether to prefix the path with the API root
     * @returns {Promise<Object>} - Parsed JSON response
     */
    async fetchJson(path, options = {}, useApiRoot = true) {
        // Update last activity timestamp
        this.lastActivity = Date.now();
        
        // Ensure API is initialized
        await this.waitForInitialization();
        
        // Ensure headers exist and include Content-Type
        if (!options.headers) {
            options.headers = {};
        }
        
        if (!options.headers['Content-Type'] && (options.method === 'POST' || options.method === 'PUT')) {
            options.headers['Content-Type'] = 'application/json';
        }
        
        // Build the URL - if path already starts with http, use it directly,
        // otherwise prepend base URL with or without API root
        let url;
        if (path.startsWith('http')) {
            url = path;
        } else if (useApiRoot) {
            url = `${this.apiRoot}${path}`;
        } else {
            url = `${this.baseUrl}${path}`;
        }
        
        try {
            console.log(`${options.method || 'GET'} ${url}`);
            const response = await fetch(url, options);
            
            if (!response.ok) {
                // Log more details about the error response
                const statusText = response.statusText || 'No status text';
                let errorDetails = `HTTP error! status: ${response.status} (${statusText})`;
                
                try {
                    // Try to get error details from response body
                    const errorBody = await response.text();
                    if (errorBody) {
                        try {
                            // Try to parse as JSON
                            const errorJson = JSON.parse(errorBody);
                            if (errorJson.error) {
                                errorDetails += ` - ${errorJson.error}`;
                                if (errorJson.details) {
                                    errorDetails += `: ${errorJson.details}`;
                                }
                            } else {
                                errorDetails += ` - ${errorBody.slice(0, 100)}${errorBody.length > 100 ? '...' : ''}`;
                            }
                        } catch (e) {
                            // Not JSON, use text
                            errorDetails += ` - ${errorBody.slice(0, 100)}${errorBody.length > 100 ? '...' : ''}`;
                        }
                    }
                } catch (e) {
                    console.warn('Could not read error response body:', e);
                }
                
                // Create error with detailed message
                throw new Error(errorDetails);
            }
            
            // Handle empty responses
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const jsonData = await response.json();
                console.log(`Response received with ${JSON.stringify(jsonData).length} characters`);
                return jsonData;
            } else {
                return { success: true };
            }
        } catch (error) {
            console.error(`API Error (${path}):`, error);
            
            // If the error might be related to back/forward cache or closed channel
            if (error.message && (
                error.message.includes('channel is closed') || 
                error.message.includes('back/forward cache')
            )) {
                console.log('Connection issue detected, reinitializing API client...');
                this.initialized = false;
                await this.waitForInitialization();
                // Retry the request once
                return this.fetchJson(path, options, useApiRoot);
            }
            
            throw error;
        }
    }
    
    /**
     * Standardize a molecule ID to M-x format
     * @param {string} id - ID to standardize
     * @returns {string} Standardized ID
     */
    standardizeId(id) {
        if (!id) return id;
        
        // If already in M-x format, return as is
        if (id.startsWith('M-')) {
            return id;
        }
        
        // If it's a numeric ID, convert to M-x format
        if (/^\d+$/.test(id)) {
            return `M-${id}`;
        }
        
        // For complex IDs, leave as is (will be handled by the server)
        return id;
    }
    
    /**
     * Ensure an item has a standardized ID
     * @param {Object} item - Item to process
     * @returns {Object} Item with standardized ID
     */
    ensureStandardizedId(item) {
        if (!item || !item.id) return item;
        
        // Clone to avoid modifying the original
        const result = { ...item };
        
        // If ID is not in M-x format, preserve it as original_id and set standardized ID
        if (!result.id.startsWith('M-')) {
            if (!result.original_id) {
                result.original_id = result.id;
            }
            result.id = this.standardizeId(result.id);
        }
        
        return result;
    }
    
    /**
     * Get all molecules
     * @param {string} query - Optional search query
     * @returns {Promise<Array>} List of molecules
     */
    async getMolecules(query = '') {
        try {
            const path = `/molecules${query ? `?q=${encodeURIComponent(query)}` : ''}`;
            const response = await this.fetchJson(path);
            
            // Handle case where response is a direct array (our API returns this format)
            if (Array.isArray(response)) {
                return response.map(m => this.ensureStandardizedId(m));
            }
            
            // Process the response to ensure IDs are standardized (legacy format)
            if (response && response.molecules && Array.isArray(response.molecules)) {
                return response.molecules.map(m => this.ensureStandardizedId(m));
            }
            
            // Return empty array if response format is unexpected
            console.warn('Unexpected response format from /api/molecules:', response);
            return [];
        } catch (error) {
            console.error('Error fetching molecules:', error);
            // Return empty array instead of throwing to make UI more resilient
            return [];
        }
    }
    
    /**
     * Get a single molecule by ID
     * @param {string} id - Molecule ID
     * @returns {Promise<Object>} Molecule details
     */
    async getMolecule(id) {
        try {
            const standardizedId = this.standardizeId(id);
            const response = await this.fetchJson(`/molecules/${standardizedId}`);
            return this.ensureStandardizedId(response);
        } catch (error) {
            // If failed with M-x format, try with original ID
            if (id.startsWith('M-') && error.message.includes('404')) {
                const originalId = id.substring(2); // Remove 'M-' prefix
                const response = await this.fetchJson(`/molecules/${originalId}`);
                return this.ensureStandardizedId(response);
            }
            throw error;
        }
    }
    
    /**
     * Create a new molecule
     * @param {Object} molecule - Molecule data
     * @returns {Promise<Object>} Created molecule
     */
    async createMolecule(molecule) {
        const response = await this.fetchJson('/molecules', {
            method: 'POST',
            body: JSON.stringify(molecule)
        });
        return this.ensureStandardizedId(response);
    }
    
    /**
     * Update an existing molecule
     * @param {string} id - Molecule ID
     * @param {Object} data - Updated molecule data
     * @returns {Promise<Object>} Updated molecule
     */
    async updateMolecule(id, data) {
        const standardizedId = this.standardizeId(id);
        const response = await this.fetchJson(`/molecules/${standardizedId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        return this.ensureStandardizedId(response);
    }
    
    /**
     * Delete a molecule
     * @param {string} id - Molecule ID
     * @returns {Promise<Object>} Response
     */
    async deleteMolecule(id) {
        const standardizedId = this.standardizeId(id);
        return await this.fetchJson(`/molecules/${standardizedId}`, {
            method: 'DELETE'
        });
    }
    
    /**
     * Enrich a molecule with external data
     * @param {string} id - Molecule ID
     * @param {Object} identifiers - Identifiers to use for enrichment
     * @returns {Promise<Object>} Enriched data
     */
    async enrichMolecule(id, identifiers) {
        const standardizedId = this.standardizeId(id);
        return await this.fetchJson(`/api/molecules/enrich/${standardizedId}`, {
            method: 'POST',
            body: JSON.stringify({ identifiers })
        });
    }
    
    /**
     * Create or update a molecule
     * @param {Object} moleculeData - Molecule data
     * @returns {Promise<Object>} Created/updated molecule
     */
    async createOrUpdateMolecule(moleculeData) {
        console.log("createOrUpdateMolecule called with:", moleculeData);
        
        // Ensure we have data
        if (!moleculeData || typeof moleculeData !== 'object' || Object.keys(moleculeData).length === 0) {
            throw new Error("No valid molecule data provided");
        }
        
        // Clone the data to avoid modifications to the original object
        const data = JSON.parse(JSON.stringify(moleculeData));
        
        console.log("Sending to server:", data);
        console.log("JSON payload:", JSON.stringify(data));
        
        return await this.fetchJson('/molecules/create_or_update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
    }
    
    /**
     * Migrate molecule IDs to standardized format
     * @returns {Promise<Object>} Migration results
     */
    async migrateMoleculeIds() {
        return await this.fetchJson('/molecules/migrate_ids', {
            method: 'POST'
        });
    }
    
    /**
     * Get all targets
     * @returns {Promise<Array>} List of targets
     */
    async getTargets() {
        const response = await this.fetchJson('/targets');
        return response.targets || [];
    }
    
    /**
     * Get a single target by ID
     * @param {string} id - Target ID
     * @returns {Promise<Object>} Target details
     */
    async getTarget(id) {
        return await this.fetchJson(`/targets/${id}`);
    }
    
    /**
     * Get all organisms
     * @returns {Promise<Array>} List of organisms
     */
    async getOrganisms() {
        const response = await this.fetchJson('/organisms');
        return response.organisms || [];
    }
    
    /**
     * Get a single organism by ID
     * @param {string} id - Organism ID
     * @returns {Promise<Object>} Organism details
     */
    async getOrganism(id) {
        return await this.fetchJson(`/organisms/${id}`);
    }
    
    /**
     * Get all effects
     * @returns {Promise<Array>} List of effects
     */
    async getEffects() {
        const response = await this.fetchJson('/effects');
        return response.effects || [];
    }
    
    /**
     * Get a single effect by ID
     * @param {string} id - Effect ID
     * @returns {Promise<Object>} Effect details
     */
    async getEffect(id) {
        return await this.fetchJson(`/effects/${id}`);
    }

    // Statistics
    async getStatistics() {
        return this.fetchJson('/statistics');
    }

    // Targets
    async listTargets(query = '') {
        return this.fetchJson(`/targets${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    }

    async enrichTarget(id, searchIdentifiers = []) {
        return this.fetchJson(`/targets/${id}/enrich`, { 
            method: 'POST',
            body: JSON.stringify({ identifiers: searchIdentifiers })
        });
    }
    
    async enrichOrganism(id, searchIdentifiers = []) {
        return this.fetchJson(`/organisms/${id}/enrich`, { 
            method: 'POST',
            body: JSON.stringify({ identifiers: searchIdentifiers })
        });
    }
    
    async enrichEffect(id, searchIdentifiers = []) {
        return this.fetchJson(`/effects/${id}/enrich`, { 
            method: 'POST',
            body: JSON.stringify({ identifiers: searchIdentifiers })
        });
    }

    // Graph Data
    async getGraphData(query = '') {
        return this.fetchJson(`/graph${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    }

    // Node Details
    async getNodeDetails(id) {
        return this.fetchJson(`/nodes/${id}`);
    }

    // Relationships
    async getRelationships(nodeId) {
        return this.fetchJson(`/relationships?node_id=${encodeURIComponent(nodeId)}`);
    }

    /**
     * Get the molecule structure image URL
     * @param {string} moleculeId - ID of the molecule
     * @returns {string} URL to the molecule structure image
     */
    getMoleculeStructureUrl(moleculeId) {
        return `/molecules/${moleculeId}/structure`;
    }

    /**
     * Get the molecule structure as base64 encoded image
     * @param {string} moleculeId - ID of the molecule
     * @returns {Promise<Object>} Object containing the base64 encoded image
     */
    async getMoleculeStructureBase64(moleculeId) {
        // These endpoints are directly at /molecules/, not at /api/molecules/
        return this.fetchJson(`/molecules/${moleculeId}/structure_base64`, {}, false);
    }
}

// Initialize global API instance
console.log('Creating API client instance...');
window.api = new HyperBlendAPI();

// Start initialization
window.api.initialize().catch(error => {
    console.error('Failed to initialize API client:', error);
});

// Add event listener for page show events (handles back/forward navigation)
window.addEventListener('pageshow', (event) => {
    // Check if the page was restored from the bfcache
    if (event.persisted) {
        console.log('Page was restored from back/forward cache, reinitializing API client...');
        window.api.initialized = false;
        window.api.initialize().catch(error => {
            console.error('Failed to reinitialize API client after navigation:', error);
        });
    }
}); 