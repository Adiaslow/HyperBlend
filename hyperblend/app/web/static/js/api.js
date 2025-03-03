// hyperblend/app/web/static/js/api.js

class APIClient {
    constructor() {
        this.baseUrl = 'http://127.0.0.1:5001/api';
        console.log('API Client initialized with base URL:', this.baseUrl);
    }
    
    async search(query) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error('Search failed');
            }
            return await response.json();
        } catch (error) {
            console.error('Search error:', error);
            throw error;
        }
    }
    
    async getCompound(compoundId) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds/${compoundId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch compound');
            }
            return await response.json();
        } catch (error) {
            console.error('Get compound error:', error);
            throw error;
        }
    }
    
    async getCompoundTargets(compoundId) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds/${compoundId}/targets`);
            if (!response.ok) {
                throw new Error('Failed to fetch compound targets');
            }
            return await response.json();
        } catch (error) {
            console.error('Get compound targets error:', error);
            throw error;
        }
    }
    
    async getCompoundSources(compoundId) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds/${compoundId}/sources`);
            if (!response.ok) {
                throw new Error('Failed to fetch compound sources');
            }
            return await response.json();
        } catch (error) {
            console.error('Get compound sources error:', error);
            throw error;
        }
    }
    
    async createCompound(compoundData) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(compoundData),
            });
            if (!response.ok) {
                throw new Error('Failed to create compound');
            }
            return await response.json();
        } catch (error) {
            console.error('Create compound error:', error);
            throw error;
        }
    }
    
    async updateCompound(compoundId, compoundData) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds/${compoundId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(compoundData),
            });
            if (!response.ok) {
                throw new Error('Failed to update compound');
            }
            return await response.json();
        } catch (error) {
            console.error('Update compound error:', error);
            throw error;
        }
    }
    
    async deleteCompound(compoundId) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds/${compoundId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                throw new Error('Failed to delete compound');
            }
            return true;
        } catch (error) {
            console.error('Delete compound error:', error);
            throw error;
        }
    }

    async getGraphData(query = '') {
        try {
            console.log('Fetching graph data with query:', query);
            const response = await fetch(`${this.baseUrl}/graph?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Received graph data:', data);
            return data;
        } catch (error) {
            console.error('Error fetching graph data:', error);
            throw error;
        }
    }

    async getNodeDetails(nodeId) {
        try {
            console.log('Fetching node details for ID:', nodeId);
            const response = await fetch(`${this.baseUrl}/compounds/${nodeId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Received node details:', data);
            return data;
        } catch (error) {
            console.error('Error fetching node details:', error);
            throw error;
        }
    }

    async getRelatedNodes(nodeId) {
        try {
            const response = await fetch(`${this.baseUrl}/nodes/${nodeId}/related`);
            if (!response.ok) throw new Error('Failed to fetch related nodes');
            return await response.json();
        } catch (error) {
            console.error('Error fetching related nodes:', error);
            throw error;
        }
    }

    async getStatistics() {
        try {
            console.log('Fetching statistics...');
            const response = await fetch(`${this.baseUrl}/statistics`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Received statistics:', data);
            return data;
        } catch (error) {
            console.error('Error fetching statistics:', error);
            throw error;
        }
    }

    async getCompounds(query = '') {
        try {
            console.log('Fetching compounds with query:', query);
            const response = await fetch(`${this.baseUrl}/compounds?q=${encodeURIComponent(query)}`);
            console.log('Compounds response status:', response.status);
            if (!response.ok) {
                throw new Error('Failed to fetch compounds');
            }
            const data = await response.json();
            console.log('Compounds received:', data);
            return data;
        } catch (error) {
            console.error('Get compounds error:', error);
            throw error;
        }
    }

    async getCompoundRelated(compoundId) {
        try {
            const response = await fetch(`${this.baseUrl}/compounds/${compoundId}/related`);
            if (!response.ok) {
                throw new Error('Failed to fetch related compounds');
            }
            return await response.json();
        } catch (error) {
            console.error('Get compound related error:', error);
            throw error;
        }
    }

    async addCompound(database, identifier) {
        try {
            console.log('Adding compound from database:', database, 'identifier:', identifier);
            const response = await fetch(`${this.baseUrl}/compounds/add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ database, identifier }),
            });
            console.log('Add compound response status:', response.status);
            if (!response.ok) {
                throw new Error('Failed to add compound');
            }
            const data = await response.json();
            console.log('Compound added:', data);
            return data;
        } catch (error) {
            console.error('Add compound error:', error);
            throw error;
        }
    }
}

// Create global API client instance
const api = new APIClient(); 