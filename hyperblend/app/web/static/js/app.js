// hyperblend/app/web/static/js/app.js

// Main application module
class App {
    constructor() {
        this.api = null;
        this.graph = null;
        this.initialize();
    }

    initialize() {
        try {
            // Initialize API client
            this.api = new APIClient();
            
            // Initialize graph visualization
            const container = document.getElementById('graph-container');
            if (!container) {
                console.error('Graph container not found');
                return;
            }
            console.log('Graph container found, initializing visualization...');
            this.graph = new GraphVisualization('graph-container');
            
            // Bind event handlers
            this.bindEvents();
            
            // Load initial data
            this.loadInitialData();
            
            // Load statistics
            this.loadStatistics();
        } catch (error) {
            console.error('Error initializing application:', error);
        }
    }

    bindEvents() {
        // Search input handler
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.loadGraphData(searchInput.value);
            }, 300));
        }

        // Node click handler
        if (this.graph) {
            this.graph.on('nodeClick', (node) => {
                this.showNodeDetails(node);
            });
        }
    }

    async loadInitialData() {
        try {
            console.log('Loading initial graph data...');
            await this.loadGraphData('');
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async loadGraphData(query) {
        try {
            console.log('Loading graph data with query:', query);
            const data = await this.api.getGraphData(query);
            if (data && this.graph) {
                console.log('Received graph data:', data);
                this.graph.updateData(data);
            }
        } catch (error) {
            console.error('Error loading graph data:', error);
        }
    }

    async loadStatistics() {
        try {
            const stats = await this.api.getStatistics();
            if (stats) {
                document.getElementById('compoundCount').textContent = stats.compounds;
                document.getElementById('sourceCount').textContent = stats.sources;
                document.getElementById('targetCount').textContent = stats.targets;
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }

    showNodeDetails(node) {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        // Create details content
        let content = `
            <h3>${node.name}</h3>
            <p><strong>Type:</strong> ${node.type}</p>
        `;

        if (node.description) {
            content += `<p><strong>Description:</strong> ${node.description}</p>`;
        }

        if (node.smiles) {
            content += `<p><strong>SMILES:</strong> ${node.smiles}</p>`;
        }

        sidebar.innerHTML = content;
        sidebar.classList.remove('hidden');
    }

    // Utility function for debouncing
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, creating app instance...');
    window.app = new App();
}); 