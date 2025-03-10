// hyperblend/app/web/static/js/app.js

// Main application module
class App {
    constructor() {
        this.initialized = false;
        this.initializationAttempts = 0;
        this.maxAttempts = 10;
        this.currentNodeId = null;
        this.initializationInterval = 100; // ms between retries

        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    initialize() {
        // First ensure the API client exists
        if (!window.api) {
            return this.retryInitialization('API client not available');
        }

        // Then check if it has the required methods
        if (!this.validateAPIClient()) {
            return this.retryInitialization('API client missing required methods');
        }

        // Check for graph container only if we're on the home page
        if (window.location.pathname === '/' && !document.getElementById('graph-container')) {
            return this.retryInitialization('Graph container not found');
        }

        try {
            if (!this.initialized) {
                console.log('Initializing application components...');
                
                // Store API reference
                this.api = window.api;

                // Initialize UI elements
                this.initializeUIElements();

                // Initialize components based on current page
                if (window.location.pathname === '/') {
                    this.initializeHomePage();
                } else {
                    this.initializeSubPage();
                }

                // Set up event listeners
                this.initializeEventListeners();

                this.initialized = true;
                console.log('Application initialized successfully');
            }
        } catch (error) {
            console.error('Error during initialization:', error);
            this.handleInitializationError(error);
        }
    }

    validateAPIClient() {
        const requiredMethods = ['getGraphData', 'getStatistics', 'listMolecules', 'listTargets', 'listOrganisms', 'listEffects'];
        return requiredMethods.every(method => typeof window.api[method] === 'function');
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
        // Show user-friendly error message
        this.showError('Unable to initialize application. Please refresh the page or contact support if the problem persists.');
    }

    initializeUIElements() {
        this.searchInput = document.getElementById('searchInput');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.sidebar = document.getElementById('sidebar');
        
        // Hide loading spinner initially
        if (this.loadingSpinner) {
            this.hideLoading();
        }
    }

    initializeHomePage() {
        console.log('Initializing home page...');
        this.graph = new GraphVisualization('graph-container');
        this.loadData();
    }

    initializeSubPage() {
        console.log('Initializing sub page...');
        this.updateStatistics();
    }

    initializeEventListeners() {
        // Search input handler with debounce
        if (this.searchInput) {
            this.searchInput.addEventListener('input', debounce((event) => {
                this.handleSearch(event.target.value);
            }, 300));
        }

        // Graph event listeners
        if (this.graph) {
            this.graph.on('nodeClick', (node) => this.showNodeDetails(node));
            
            // Handle click-away from sidebar
            document.addEventListener('click', (event) => {
                if (event.target.closest('#graph-container') && 
                    !event.target.closest('circle') && 
                    !event.target.closest('.graph-legend')) {
                    this.hideSidebar();
                }
            });

            // Handle window resize
            window.addEventListener('resize', () => this.graph.resize());
        }
    }

    async loadData(query = '') {
        try {
            this.showLoading();
            const data = await this.api.getGraphData(query);
            if (this.graph) {
                this.graph.updateData(data);
            }
            await this.updateStatistics();
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Error loading graph data. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    async handleSearch(query) {
        try {
            this.showLoading();
            const [graphData, targets] = await Promise.all([
                this.api.getGraphData(query),
                this.api.listTargets(query)
            ]);

            if (this.graph) {
                const combinedData = this.combineGraphData(graphData, targets);
                this.graph.updateData(combinedData);
            }
            
            await this.updateStatistics();
        } catch (error) {
            console.error('Error during search:', error);
            this.showError('Error searching data. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    combineGraphData(graphData, targets) {
        if (!targets.length || !graphData.nodes) {
            return graphData;
        }

        const existingNodeIds = new Set(graphData.nodes.map(n => n.id));
        
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

    async updateStatistics() {
        try {
            const stats = await this.api.getStatistics();
            
            const elements = {
                molecules: document.getElementById('moleculeCount'),
                organisms: document.getElementById('organismCount'),
                targets: document.getElementById('targetCount'),
                effects: document.getElementById('effectCount')
            };

            Object.entries(elements).forEach(([key, element]) => {
                if (element && stats[key]) {
                    element.textContent = stats[key];
                }
            });
        } catch (error) {
            console.error('Error updating statistics:', error);
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

    showSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.remove('hidden');
        }
    }

    hideSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.add('hidden');
        }
    }

    toggleSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.toggle('visible');
        }
    }

    async showNodeDetails(node) {
        if (!node || !node.id) return;
        
        try {
            const details = await this.api.getNodeDetails(node.id);
            if (this.sidebar) {
                this.sidebar.innerHTML = this.getNodeDetailsHtml(details);
                this.showSidebar();
            }
        } catch (error) {
            console.error('Error fetching node details:', error);
            this.showError('Error loading node details');
        }
    }

    getNodeDetailsHtml(details) {
        return `
            <div class="p-4">
                <h2 class="text-xl font-bold mb-4">${details.name}</h2>
                ${details.description ? `<p class="text-gray-600 mb-4">${details.description}</p>` : ''}
                ${this.getRelatedNodesHtml(details.related_nodes || [])}
            </div>
        `;
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
}

// Make App class available globally
window.App = App;

// Initialize the application
console.log('Setting up application initialization...');

// Create app instance with proper error handling
async function createApp() {
    console.log('Creating app instance...');
    try {
        if (!window.api) {
            throw new Error('API client not found');
        }

        // Wait for API client to be initialized
        await window.api.waitForInitialization();
        
        window.app = new App();
    } catch (error) {
        console.error('Error creating app:', error);
        // If API client exists but isn't ready, retry
        if (window.api && !window.api.initialized) {
            setTimeout(createApp, 100);
        } else {
            // Show error to user
            const errorContainer = document.createElement('div');
            errorContainer.className = 'error-message fixed top-4 right-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg';
            errorContainer.textContent = 'Unable to initialize application. Please refresh the page or contact support if the problem persists.';
            document.body.appendChild(errorContainer);
        }
    }
}

// Ensure proper initialization sequence
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createApp);
} else {
    createApp();
}; 