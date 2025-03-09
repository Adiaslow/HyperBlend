// hyperblend/app/web/static/js/app.js

// Main application module
class App {
    constructor() {
        this.initialized = false;
        this.initializationAttempts = 0;
        this.maxAttempts = 10;
        this.currentNodeId = null;

        // Wait for DOM to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    initialize() {
        // Ensure API client is available and has required methods
        if (!window.api || !window.api.getGraphData) {
            this.initializationAttempts++;
            if (this.initializationAttempts < this.maxAttempts) {
                console.log('API client not ready, retrying...');
                setTimeout(() => this.initialize(), 200);
                return;
            } else {
                throw new Error('API client initialization failed after multiple attempts');
            }
        }
        
        // Ensure graph container exists if on home page
        const container = document.getElementById('graph-container');
        if (!container && window.location.pathname === '/') {
            console.error('Graph container not found. Waiting for it to be available...');
            setTimeout(() => this.initialize(), 200);
            return;
        }
        
        if (!this.initialized) {
            // Only initialize graph visualization on the home page
            if (window.location.pathname === '/') {
                this.graph = new GraphVisualization('graph-container');
            }
            
            this.api = window.api;
            this.searchInput = document.getElementById('searchInput');
            this.loadingSpinner = document.getElementById('loadingSpinner');
            this.sidebar = document.getElementById('sidebar');
            
            // Initialize event listeners only if elements exist
            this.initializeEventListeners();
            
            // Load initial data
            if (window.location.pathname === '/') {
                this.loadData();
            } else {
                // Update statistics on other pages
                this.updateStatistics();
            }
            
            this.initialized = true;
            console.log('Application initialized successfully');
        }
    }

    initializeEventListeners() {
        // Search input handler with debounce
        if (this.searchInput) {
            let searchTimeout;
            this.searchInput.addEventListener('input', (event) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.handleSearch(event.target.value);
                }, 300);
            });
        }

        // Handle node clicks for showing details
        if (this.graph) {
            this.graph.on('nodeClick', (node) => {
                this.showNodeDetails(node);
            });
        }

        // Handle click-away from sidebar
        if (this.sidebar) {
            document.addEventListener('click', (event) => {
                // Check if click is on the graph container and not on a node
                if (event.target.closest('#graph-container') && 
                    !event.target.closest('circle') && 
                    !event.target.closest('.graph-legend')) {
                    this.hideSidebar();
                }
            });
        }

        // Handle window resize
        if (this.graph) {
            window.addEventListener('resize', () => {
                this.graph.resize();
            });
        }
    }

    async loadData(query = '') {
        try {
            this.showLoading();
            const data = await this.api.getGraphData(query);  // Use getGraphData instead of searchGraph
            this.graph.updateData(data);
            await this.updateStatistics();
            this.hideLoading();
        } catch (error) {
            console.error('Error loading data:', error);
            this.hideLoading();
            this.showError('Error loading graph data');
        }
    }

    async handleSearch(query) {
        try {
            this.showLoading();
            const [graphData, targets] = await Promise.all([
                this.api.getGraphData(query),  // Use getGraphData instead of searchGraph
                this.api.searchTargets(query)
            ]);

            // Update the graph with the combined data
            const combinedData = this.combineGraphData(graphData, targets);
            this.graph.updateData(combinedData);
            
            await this.updateStatistics();
            this.hideLoading();
        } catch (error) {
            console.error('Error during search:', error);
            this.hideLoading();
            this.showError('Error searching data');
        }
    }

    combineGraphData(graphData, targets) {
        // If there are no targets or the graph data is empty, return the original data
        if (!targets.length || !graphData.nodes) {
            return graphData;
        }

        // Create a map of existing node IDs to avoid duplicates
        const existingNodeIds = new Set(graphData.nodes.map(n => n.id));
        
        // Add new target nodes if they don't exist
        targets.forEach(target => {
            if (!existingNodeIds.has(target.id)) {
                graphData.nodes.push({
                    id: target.id,
                    name: target.name,
                    type: 'Target',
                    description: target.description,
                    width: 30,
                    height: 30,
                    fixed: false,
                    x: 0,
                    y: 0
                });
            }
        });

        return graphData;
    }

    async showNodeDetails(node) {
        try {
            // If clicking the same node, just toggle the sidebar
            if (this.currentNodeId === node.id) {
                this.toggleSidebar();
                return;
            }

            // If clicking a different node, show its details
            this.currentNodeId = node.id;
            console.log('Fetching details for node:', node);
            const details = await this.api.getNodeDetails(node.id);
            console.log('Received node details:', details);

            let content = `
                <div class="p-4">
                    <h2 class="text-xl font-bold mb-4">${details.name}</h2>
                    <div class="mb-4">
                        <span class="inline-block px-2 py-1 rounded bg-${this.getNodeTypeColor(details.type)} text-white text-sm">
                            ${details.type}
                        </span>
                    </div>
                    ${details.description ? `<p class="mb-4">${details.description}</p>` : ''}
                    
                    ${this.getNodeProperties(details)}
                    
                    <h3 class="text-lg font-semibold mb-2">Related Nodes (${details.related_nodes.length})</h3>
                    <div class="space-y-2">
                        ${this.getRelatedNodesHtml(details.related_nodes)}
                    </div>
                </div>
            `;

            this.sidebar.innerHTML = content;
            this.showSidebar();
        } catch (error) {
            console.error('Error showing node details:', error);
            this.showError('Error loading node details');
        }
    }

    getNodeTypeColor(type) {
        const colors = {
            'Molecule': 'green-600',
            'Organism': 'blue-600',
            'Target': 'red-600',
            'default': 'gray-600'
        };
        return colors[type] || colors.default;
    }

    getNodeProperties(details) {
        const properties = [];

        if (details.smiles) {
            properties.push(`
                <div class="mb-2">
                    <span class="font-medium">SMILES:</span>
                    <span class="font-mono text-sm break-all">${details.smiles}</span>
                </div>
            `);
        }

        if (details.molecular_weight) {
            properties.push(`
                <div class="mb-2">
                    <span class="font-medium">Molecular Weight:</span>
                    <span>${details.molecular_weight}</span>
                </div>
            `);
        }

        if (details.formula) {
            properties.push(`
                <div class="mb-2">
                    <span class="font-medium">Formula:</span>
                    <span class="font-mono">${details.formula}</span>
                </div>
            `);
        }

        if (details.organism) {
            properties.push(`
                <div class="mb-2">
                    <span class="font-medium">Organism:</span>
                    <span>${details.organism}</span>
                </div>
            `);
        }

        if (details.confidence_score) {
            properties.push(`
                <div class="mb-2">
                    <span class="font-medium">Confidence Score:</span>
                    <span>${details.confidence_score}</span>
                </div>
            `);
        }

        if (details.pubchem_cid) {
            properties.push(`
                <div class="mb-2">
                    <span class="font-medium">PubChem CID:</span>
                    <a href="https://pubchem.ncbi.nlm.nih.gov/compound/${details.pubchem_cid}" 
                       target="_blank" 
                       class="text-blue-600 hover:underline">
                        ${details.pubchem_cid}
                    </a>
                </div>
            `);
        }

        if (details.chembl_id) {
            properties.push(`
                <div class="mb-2">
                    <span class="font-medium">ChEMBL ID:</span>
                    <a href="https://www.ebi.ac.uk/chembl/compound_report_card/${details.chembl_id}" 
                       target="_blank"
                       class="text-blue-600 hover:underline">
                        ${details.chembl_id}
                    </a>
                </div>
            `);
        }

        return properties.length ? `
            <div class="mb-4 p-3 bg-gray-50 rounded">
                ${properties.join('')}
            </div>
        ` : '';
    }

    getRelatedNodesHtml(relatedNodes) {
        if (!relatedNodes.length) {
            return '<p class="text-gray-500">No related nodes found</p>';
        }

        return relatedNodes.map(node => `
            <div class="p-2 bg-gray-50 rounded flex items-center justify-between">
                <div>
                    <span class="font-medium">${node.name}</span>
                    <span class="text-sm text-gray-600 ml-2">(${node.type})</span>
                    ${node.relationship ? `
                        <div class="text-sm text-gray-600">
                            ${node.relationship}
                            ${node.activity ? `: ${node.activity}` : ''}
                        </div>
                    ` : ''}
                </div>
                <button onclick="app.graph.focusNode('${node.id}')" 
                        class="px-2 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600">
                    Show
                </button>
            </div>
        `).join('');
    }

    async updateStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const data = await response.json();

            const moleculeCountElement = document.getElementById('moleculeCount');
            const organismCountElement = document.getElementById('organismCount');
            const targetCountElement = document.getElementById('targetCount');
            const effectCountElement = document.getElementById('effectCount');

            if (moleculeCountElement) {
                moleculeCountElement.textContent = data.molecules;
            }
            if (organismCountElement) {
                organismCountElement.textContent = data.organisms;
            }
            if (targetCountElement) {
                targetCountElement.textContent = data.targets;
            }
            if (effectCountElement) {
                effectCountElement.textContent = data.effects;
            }
        } catch (error) {
            console.error('Error updating statistics:', error);
        }
    }

    showLoading() {
        this.loadingSpinner.classList.remove('hidden');
    }

    hideLoading() {
        this.loadingSpinner.classList.add('hidden');
    }

    showError(message) {
        // You can implement a more sophisticated error display here
        alert(message);
    }

    showSidebar() {
        this.sidebar.classList.add('visible');
    }

    hideSidebar() {
        this.sidebar.classList.remove('visible');
        this.currentNodeId = null;
    }

    toggleSidebar() {
        if (this.sidebar.classList.contains('visible')) {
            this.hideSidebar();
        } else {
            this.showSidebar();
        }
    }
}

// Initialize the application
console.log('Setting up application initialization...');

// Function to create app instance
function createApp() {
    console.log('Creating app instance...');
    try {
        window.app = new App();
    } catch (error) {
        console.error('Error creating app:', error);
        // Try again if API client isn't ready
        if (error.message === 'API client not initialized') {
            setTimeout(createApp, 100);
        }
    }
}

// Start initialization when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createApp);
} else {
    createApp();
} 