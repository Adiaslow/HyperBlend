// hyperblend/app/web/static/js/api.js

class HyperBlendAPI {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    async getStatistics() {
        const response = await fetch(`${this.baseURL}/api/statistics`);
        if (!response.ok) {
            throw new Error('Failed to fetch statistics');
        }
        return await response.json();
    }

    async getGraphData(query = '') {
        const response = await fetch(`${this.baseURL}/api/graph?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Failed to fetch graph data');
        }
        return await response.json();
    }

    async getNodeDetails(nodeId) {
        const response = await fetch(`${this.baseURL}/api/nodes/${nodeId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch node details');
        }
        return await response.json();
    }

    async getMoleculeDetails(moleculeId) {
        const response = await fetch(`${this.baseURL}/api/molecules/${moleculeId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch molecule details');
        }
        return await response.json();
    }

    async getOrganismDetails(organismId) {
        const response = await fetch(`${this.baseURL}/api/organisms/${organismId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch organism details');
        }
        return await response.json();
    }

    async getTargetDetails(targetId) {
        const response = await fetch(`${this.baseURL}/api/targets/${targetId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch target details');
        }
        return await response.json();
    }

    async searchMolecules(query) {
        const response = await fetch(`${this.baseURL}/api/molecules/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Failed to search molecules');
        }
        return await response.json();
    }

    async searchOrganisms(query) {
        const response = await fetch(`${this.baseURL}/api/organisms/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Failed to search organisms');
        }
        return await response.json();
    }

    async searchTargets(query) {
        const response = await fetch(`${this.baseURL}/api/targets/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Failed to search targets');
        }
        return await response.json();
    }
}

// Create global API client instance and ensure it's properly initialized
(function() {
    try {
        window.api = new HyperBlendAPI();
        console.log('API client successfully initialized and attached to window');
    } catch (error) {
        console.error('Failed to initialize API client:', error);
        throw error;
    }
})(); 