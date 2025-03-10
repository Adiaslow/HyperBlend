// hyperblend/app/web/static/js/api.js

class HyperBlendAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.initialized = false;
        this.initializationPromise = null;
    }

    async waitForInitialization() {
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
            console.log('API client initialized successfully');
            return true;
        } catch (error) {
            console.error('Error initializing API client:', error);
            this.initialized = false;
            throw error;
        }
    }

    async fetchJson(endpoint, options = {}) {
        if (!this.initialized) {
            throw new Error('API client not initialized');
        }

        const maxRetries = 3;
        let retryCount = 0;
        let lastError;

        while (retryCount < maxRetries) {
            try {
                const response = await fetch(`${this.baseUrl}${endpoint}`, {
                    ...options,
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    }
                });
                
                if (response.status === 503) {
                    retryCount++;
                    if (retryCount < maxRetries) {
                        // Wait for a bit before retrying (exponential backoff)
                        await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
                        continue;
                    }
                }
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                return await response.json();
            } catch (error) {
                lastError = error;
                if (retryCount >= maxRetries - 1) {
                    console.error(`API Error (${endpoint}):`, error);
                    throw error;
                }
                retryCount++;
                // Wait before retrying
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
            }
        }
        
        throw lastError;
    }

    // Statistics
    async getStatistics() {
        return this.fetchJson('/api/statistics');
    }

    // Molecules
    async listMolecules(query = '') {
        return this.fetchJson(`/api/molecules${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    }

    async getMolecule(id) {
        return this.fetchJson(`/api/molecules/${id}`);
    }

    // Targets
    async listTargets(query = '') {
        return this.fetchJson(`/api/targets${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    }

    async getTarget(id) {
        return this.fetchJson(`/api/targets/${id}`);
    }

    // Organisms
    async listOrganisms(query = '') {
        return this.fetchJson(`/api/organisms${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    }

    async getOrganism(id) {
        return this.fetchJson(`/api/organisms/${id}`);
    }

    // Effects
    async listEffects(query = '') {
        return this.fetchJson(`/api/effects${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    }

    async getEffect(id) {
        return this.fetchJson(`/api/effects/${id}`);
    }

    // Graph Data
    async getGraphData(query = '') {
        return this.fetchJson(`/api/graph${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    }

    // Node Details
    async getNodeDetails(id) {
        return this.fetchJson(`/api/nodes/${id}`);
    }

    // Relationships
    async getRelationships(nodeId) {
        return this.fetchJson(`/api/relationships?node_id=${encodeURIComponent(nodeId)}`);
    }

    // Enrichment
    async enrichMolecule(id) {
        return this.fetchJson(`/api/molecules/${id}/enrich`, { method: 'POST' });
    }

    async enrichTarget(id) {
        return this.fetchJson(`/api/targets/${id}/enrich`, { method: 'POST' });
    }
}

// Initialize global API instance
console.log('Creating API client instance...');
window.api = new HyperBlendAPI();

// Start initialization
window.api.initialize().catch(error => {
    console.error('Failed to initialize API client:', error);
}); 