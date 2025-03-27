// molecules.js - Molecule page functionality

/**
 * MoleculePage class - Manages molecule listing, details, and interactions
 */
class MoleculePage extends ListPage {
    /**
     * Initialize the molecule page
     * @param {Object} config - Configuration options
     */
    constructor(config = {}) {
        // Call parent constructor with type 'molecules'
        super('molecules', config);
        
        this.currentMolecule = null;
        this.api = window.api || new HyperBlendAPI();
        
        // Initialize page elements
        this.initializePage();
        
        // Setup navigation event listener
        this.setupNavigationHandler();
    }
    
    /**
     * Set up handlers for back/forward navigation
     */
    setupNavigationHandler() {
        window.addEventListener('pageshow', (event) => {
            if (event.persisted) {
                console.log('MoleculePage detected page restored from cache, refreshing data...');
                this.fetchItems().catch(error => {
                    console.error('Error refreshing data after navigation:', error);
                });
                
                // Refresh details if we have a current item
                if (this.currentItemId) {
                    this.fetchItemDetails(this.currentItemId, false).catch(error => {
                        console.error('Error refreshing details after navigation:', error);
                    });
                }
            }
        });
    }
    
    /**
     * Initialize page-specific elements and event listeners
     */
    initializePage() {
        // Set up event listeners for add molecule form
        this.setupAddMoleculeForm();
        
        // Set up migrate IDs button
        const migrateButton = document.getElementById('migrateIdsButton');
        if (migrateButton) {
            migrateButton.addEventListener('click', () => this.migrateIds());
        }
        
        // Add any other initialization needed
        console.log('Molecule page initialized');
    }
    
    /**
     * Set up the add molecule form functionality
     */
    setupAddMoleculeForm() {
        const addButton = document.getElementById('addMoleculeButton');
        const resultDiv = document.getElementById('addMoleculeResult');
        
        // Add/Update molecule button click
        if (addButton) {
            addButton.addEventListener('click', () => this.addOrUpdateMolecule());
        }
    }
    
    /**
     * Add or update a molecule based on form data
     */
    async addOrUpdateMolecule() {
        // Get form data and clean it
        const molecule = {
            name: document.getElementById('moleculeName').value.trim(),
            cas_number: document.getElementById('moleculeCAS').value.trim(),
            pubchem_cid: document.getElementById('moleculePubChemCID').value.trim(),
            inchikey: document.getElementById('moleculeInChIKey').value.trim(),
            smiles: document.getElementById('moleculeSMILES').value.trim(),
            chembl_id: document.getElementById('moleculeChEMBL').value.trim()
        };
        
        console.log('Raw form data:', {...molecule});
        
        // Remove empty values
        Object.keys(molecule).forEach(key => {
            if (molecule[key] === '') {
                delete molecule[key];
            }
        });
        
        console.log('Cleaned molecule data:', molecule);
        console.log('Number of properties:', Object.keys(molecule).length);
        
        // Validate - ensure at least one field is filled
        if (Object.keys(molecule).length === 0) {
            this.showFormResult('Please fill at least one identifier field', 'error');
            return;
        }
        
        try {
            // Disable button during submit
            const addButton = document.getElementById('addMoleculeButton');
            if (addButton) addButton.disabled = true;
            
            // Log the API call
            console.log('Calling createOrUpdateMolecule with data:', molecule);
            
            // Call API
            const result = await this.api.createOrUpdateMolecule(molecule);
            
            console.log('API response:', result);
            
            // Show result
            const message = result.created 
                ? `Molecule ${result.name || 'Unknown'} was successfully created` 
                : `Molecule ${result.name || 'Unknown'} was successfully updated`;
            this.showFormResult(message, 'success');
            
            // Reload the list
            await this.fetchItems();
            
            // Clear form fields
            this.clearAddMoleculeForm();
            
        } catch (error) {
            console.error('Error in addOrUpdateMolecule:', error);
            this.showFormResult(`Error: ${error.message}`, 'error');
        } finally {
            // Re-enable button
            const addButton = document.getElementById('addMoleculeButton');
            if (addButton) addButton.disabled = false;
        }
    }
    
    /**
     * Show a result message for the add/update form
     * @param {string} message - Message to display
     * @param {string} type - 'success' or 'error'
     */
    showFormResult(message, type = 'success') {
        const resultDiv = document.getElementById('addMoleculeResult');
        if (resultDiv) {
            resultDiv.textContent = message;
            resultDiv.className = `result-message ${type === 'success' ? 'success-message' : 'error-message'}`;
            resultDiv.classList.remove('hidden');
            
            // Hide after 5 seconds
            setTimeout(() => {
                resultDiv.classList.add('hidden');
            }, 5000);
        }
    }
    
    /**
     * Clear all fields in the add molecule form
     */
    clearAddMoleculeForm() {
        document.getElementById('moleculeName').value = '';
        document.getElementById('moleculeCAS').value = '';
        document.getElementById('moleculePubChemCID').value = '';
        document.getElementById('moleculeInChIKey').value = '';
        document.getElementById('moleculeSMILES').value = '';
        document.getElementById('moleculeChEMBL').value = '';
    }
    
    /**
     * Migrate molecule IDs to the new format
     */
    async migrateIds() {
        try {
            const migrateButton = document.getElementById('migrateIdsButton');
            if (migrateButton) {
                migrateButton.disabled = true;
                migrateButton.textContent = 'Migrating...';
            }
            
            const result = await this.api.migrateMoleculeIds();
            
            // Show success message
            const message = `Migration complete: ${result.statistics.migrated} molecules migrated`;
            this.showFormResult(message, 'success');
            
            // Reload the list
            await this.fetchItems();
            
        } catch (error) {
            this.showFormResult(`Migration error: ${error.message}`, 'error');
        } finally {
            const migrateButton = document.getElementById('migrateIdsButton');
            if (migrateButton) {
                migrateButton.disabled = false;
                migrateButton.textContent = 'Migrate IDs';
            }
        }
    }
    
    /**
     * Override parent method for custom item formatting
     * @param {Object} item - Molecule data
     * @returns {string} HTML for the list item
     */
    getItemHtml(item) {
        // Create clickable card for the molecule (no action buttons)
        const isSelected = this.currentItemId === item.id ? 'selected' : '';
        
        return `
            <div class="list-item-card ${isSelected}" data-id="${item.id}">
                <div class="list-item-header">
                    <h3 class="list-item-title">${item.name || 'Unnamed Molecule'}</h3>
                </div>
                <div class="list-item-details">
                    ${item.formula ? `<div class="list-item-property"><span>Formula:</span> <span>${item.formula}</span></div>` : ''}
                    ${item.molecular_weight ? `<div class="list-item-property"><span>Mol. Weight:</span> <span>${item.molecular_weight}</span></div>` : ''}
                    ${item.smiles ? `<div class="list-item-property"><span>SMILES:</span> <span class="truncate-text">${this.truncateText(item.smiles, 30)}</span></div>` : ''}
                </div>
            </div>
        `;
    }
    
    /**
     * Get the HTML for detailed item view
     * @param {Object} item - Molecule data
     * @returns {string} HTML for the detailed view
     */
    getItemDetailHtml(item) {
        return `
            <div class="details-container">
                <div class="molecule-header">
                    <h2 class="details-title">${item.name || 'Unnamed Molecule'}</h2>
                    ${item.smiles ? `
                    <div class="molecule-structure-small" id="molecule-structure-${item.id}">
                        <div class="loading-spinner-small">Loading...</div>
                    </div>` : ''}
                </div>
                
                <!-- Identifiers section -->
                ${this.renderIdentifiersSection(item)}
                
                <!-- Basic information section -->
                <div class="details-section">
                    <h3 class="section-title">Basic Information</h3>
                    <div class="details-properties">
                        ${this.getAdditionalPropertiesHtml(item)}
                    </div>
                </div>
                
                <!-- Additional sections -->
                ${this.getAdditionalSectionsHtml(item)}
            </div>
        `;
    }
    
    /**
     * Render identifiers section with all available IDs
     * @param {Object} item - Molecule data
     * @returns {string} HTML for identifiers section
     */
    renderIdentifiersSection(item) {
        // Define all possible identifiers with labels and tags
        const identifiers = [
            { key: 'id', label: 'HyperBlend ID', tag: 'internal' },
            { key: 'original_id', label: 'Original ID', tag: 'internal' },
            { key: 'cas', label: 'CAS Number', tag: 'external' },
            { key: 'pubchem_cid', label: 'PubChem CID', tag: 'external', 
              link: val => `https://pubchem.ncbi.nlm.nih.gov/compound/${val}` },
            { key: 'chembl_id', label: 'ChEMBL ID', tag: 'external',
              link: val => `https://www.ebi.ac.uk/chembl/compound_report_card/${val}/` },
            { key: 'inchi_key', label: 'InChI Key', tag: 'chemical' },
            { key: 'drugbank_id', label: 'DrugBank ID', tag: 'external',
              link: val => `https://go.drugbank.com/drugs/${val}` }
        ];
        
        // Filter to only include identifiers that have values
        const availableIdentifiers = identifiers.filter(id => item[id.key]);
        
        if (availableIdentifiers.length === 0) {
            return '';
        }
        
        let html = `
            <div class="details-section">
                <h3 class="section-title">Identifiers</h3>
                <div class="identifiers-section">`;
        
        // Generate HTML for each available identifier
        availableIdentifiers.forEach(id => {
            const value = item[id.key];
            if (!value) return;
            
            html += `
                <div class="identifier-item">
                    <div class="identifier-label">${id.label}</div>
                    <div class="identifier-value">${value}</div>
                    <span class="identifier-tag tag-${id.tag}">${id.tag}</span>
                    ${id.link ? `<a href="${id.link(value)}" target="_blank" class="identifier-link">View External</a>` : ''}
                </div>`;
        });
        
        html += `
                </div>
            </div>`;
        
        return html;
    }
    
    /**
     * Override parent method for getting additional properties in the basic info section
     * @param {Object} item - Molecule data
     * @returns {string} HTML for additional properties
     */
    getAdditionalPropertiesHtml(item) {
        // List of properties to display in the basic info section
        const propertyMap = [
            { key: 'formula', label: 'Formula' },
            { key: 'molecular_weight', label: 'Molecular Weight' },
            { key: 'exact_mass', label: 'Exact Mass' },
            { key: 'smiles', label: 'SMILES' },
            { key: 'canonical_smiles', label: 'Canonical SMILES' },
            { key: 'inchi', label: 'InChI' },
            { key: 'logp', label: 'LogP' },
            { key: 'logs', label: 'LogS' },
            { key: 'polar_surface_area', label: 'Polar Surface Area' },
            { key: 'hbond_donor_count', label: 'H-Bond Donor Count' },
            { key: 'hbond_acceptor_count', label: 'H-Bond Acceptor Count' },
            { key: 'rotatable_bond_count', label: 'Rotatable Bond Count' },
            { key: 'heavy_atom_count', label: 'Heavy Atom Count' },
            { key: 'complexity', label: 'Complexity' },
            { key: 'charge', label: 'Charge' },
            { key: 'description', label: 'Description' }
        ];
        
        // Generate HTML for each property that has a value
        let html = '';
        
        propertyMap.forEach(prop => {
            const value = item[prop.key];
            if (value !== undefined && value !== null && value !== '') {
                // Special formatting for certain property types
                let formattedValue = value;
                
                // Format numerical values
                if (typeof value === 'number') {
                    if (['molecular_weight', 'exact_mass', 'logp', 'logs', 'polar_surface_area'].includes(prop.key)) {
                        formattedValue = value.toFixed(2);
                    }
                }
                
                // For long text (like SMILES or InChI), use a container with scrolling
                if (typeof value === 'string' && value.length > 50 && 
                    ['smiles', 'canonical_smiles', 'inchi', 'inchi_key'].includes(prop.key)) {
                    html += `
                        <div class="property-row">
                            <span class="property-name">${prop.label}</span>
                            <span class="property-value">
                                <div class="smiles-container">${formattedValue}</div>
                            </span>
                        </div>`;
                } else {
                    html += `
                        <div class="property-row">
                            <span class="property-name">${prop.label}</span>
                            <span class="property-value">${formattedValue}</span>
                        </div>`;
                }
            }
        });
        
        return html;
    }
    
    /**
     * Override parent method for getting additional sections beyond basic info
     * @param {Object} item - Molecule data
     * @returns {string} HTML for additional sections
     */
    getAdditionalSectionsHtml(item) {
        let html = '';
        
        // Add physical properties section if any physical properties exist
        const physicalProps = this.getPhysicalPropertiesHtml(item);
        if (physicalProps) {
            html += `
                <div class="details-section">
                    <h3 class="section-title">Physical Properties</h3>
                    <div class="details-properties">
                        ${physicalProps}
                    </div>
                </div>`;
        }
        
        // Add chemical properties section if any chemical properties exist
        const chemicalProps = this.getChemicalPropertiesHtml(item);
        if (chemicalProps) {
            html += `
                <div class="details-section">
                    <h3 class="section-title">Chemical Properties</h3>
                    <div class="details-properties">
                        ${chemicalProps}
                    </div>
                </div>`;
        }
        
        // Add pharmacological properties if they exist
        const pharmacoProps = this.getPharmacologicalPropertiesHtml(item);
        if (pharmacoProps) {
            html += `
                <div class="details-section">
                    <h3 class="section-title">Pharmacological Properties</h3>
                    <div class="details-properties">
                        ${pharmacoProps}
                    </div>
                </div>`;
        }
        
        // Add targets section if available
        if (item.targets && item.targets.length > 0) {
            html += this.renderTargetsSection(item);
        }
        
        // Add effects section if available
        if (item.effects && item.effects.length > 0) {
            html += this.renderEffectsSection(item);
        }
        
        // Add enrichment section
        html += `
            <div class="details-section">
                <h3 class="section-title">Data Enrichment</h3>
                <div class="enrichment-container">
                    <button id="enrichment-button-${item.id}" class="enrichment-button" 
                            data-id="${item.id}" 
                            onclick="window.moleculePage.enrichMolecule(event, '${item.id}')" ${item.enriched ? 'disabled' : ''}>
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        ${item.enriched ? 'Already Enriched' : 'Enrich with External Data'}
                    </button>
                    <div id="enrichment-message-${item.id}" class="animate-fade-in-out opacity-0 mt-2 text-sm text-green-600"></div>
                </div>
            </div>`;
        
        return html;
    }
    
    /**
     * Get HTML for physical properties
     * @param {Object} item - Molecule data
     * @returns {string} HTML for physical properties
     */
    getPhysicalPropertiesHtml(item) {
        // Define physical properties to display
        const physicalProps = [
            { key: 'molecular_weight', label: 'Molecular Weight' },
            { key: 'exact_mass', label: 'Exact Mass' },
            { key: 'monoisotopic_mass', label: 'Monoisotopic Mass' },
            { key: 'heavy_atom_count', label: 'Heavy Atom Count' },
            { key: 'charge', label: 'Charge' },
            { key: 'density', label: 'Density' },
            { key: 'melting_point', label: 'Melting Point' },
            { key: 'boiling_point', label: 'Boiling Point' },
            { key: 'state', label: 'Physical State' }
        ];
        
        return this.generatePropertiesHtml(item, physicalProps);
    }
    
    /**
     * Get HTML for chemical properties
     * @param {Object} item - Molecule data
     * @returns {string} HTML for chemical properties
     */
    getChemicalPropertiesHtml(item) {
        // Define chemical properties to display
        const chemicalProps = [
            { key: 'logp', label: 'LogP' },
            { key: 'logs', label: 'LogS' },
            { key: 'polar_surface_area', label: 'Polar Surface Area' },
            { key: 'hbond_donor_count', label: 'H-Bond Donor Count' },
            { key: 'hbond_acceptor_count', label: 'H-Bond Acceptor Count' },
            { key: 'rotatable_bond_count', label: 'Rotatable Bond Count' },
            { key: 'complexity', label: 'Complexity' },
            { key: 'solubility', label: 'Solubility' },
            { key: 'reactivity', label: 'Reactivity' }
        ];
        
        return this.generatePropertiesHtml(item, chemicalProps);
    }
    
    /**
     * Get HTML for pharmacological properties
     * @param {Object} item - Molecule data
     * @returns {string} HTML for pharmacological properties
     */
    getPharmacologicalPropertiesHtml(item) {
        // Define pharmacological properties to display
        const pharmacoProps = [
            { key: 'bioavailability', label: 'Bioavailability' },
            { key: 'half_life', label: 'Half-Life' },
            { key: 'clearance', label: 'Clearance' },
            { key: 'toxicity', label: 'Toxicity' },
            { key: 'mechanism_of_action', label: 'Mechanism of Action' },
            { key: 'indication', label: 'Indication' },
            { key: 'contraindication', label: 'Contraindication' },
            { key: 'side_effects', label: 'Side Effects' }
        ];
        
        return this.generatePropertiesHtml(item, pharmacoProps);
    }
    
    /**
     * Generate HTML for a list of properties
     * @param {Object} item - Molecule data
     * @param {Array} propList - List of property definitions
     * @returns {string} HTML for properties
     */
    generatePropertiesHtml(item, propList) {
        let html = '';
        let hasProps = false;
        
        propList.forEach(prop => {
            const value = item[prop.key];
            if (value !== undefined && value !== null && value !== '') {
                hasProps = true;
                
                // Format numerical values
                let formattedValue = value;
                if (typeof value === 'number') {
                    if (['molecular_weight', 'exact_mass', 'monoisotopic_mass', 'logp', 'logs', 'polar_surface_area'].includes(prop.key)) {
                        formattedValue = value.toFixed(2);
                    }
                }
                
                html += `
                    <div class="property-row">
                        <span class="property-name">${prop.label}</span>
                        <span class="property-value">${formattedValue}</span>
                    </div>`;
            }
        });
        
        return hasProps ? html : '';
    }
    
    /**
     * Render targets section
     * @param {Object} item - Molecule data with targets
     * @returns {string} HTML for targets section
     */
    renderTargetsSection(item) {
        if (!item.targets || item.targets.length === 0) {
            return '';
        }
        
        let html = `
            <div class="details-section">
                <h3 class="section-title">Associated Targets</h3>
                <div class="targets-list">`;
        
        item.targets.forEach(target => {
            html += `
                <div class="target-item">
                    <strong>${target.name || 'Unnamed Target'}</strong>
                    ${target.type ? `<div><span>Type:</span> ${target.type}</div>` : ''}
                    ${target.organism ? `<div><span>Organism:</span> ${target.organism}</div>` : ''}
                    ${target.relationship_type ? `<div><span>Interaction:</span> ${this.formatRelationshipType(target.relationship_type)}</div>` : ''}
                    ${target.activity_value ? `
                        <div><span>Activity:</span> ${target.activity_value} ${target.activity_unit || ''}
                        ${target.activity_type ? `(${target.activity_type})` : ''}</div>` : ''}
                </div>`;
        });
        
        html += `
                </div>
            </div>`;
        
        return html;
    }
    
    /**
     * Render effects section
     * @param {Object} item - Molecule data with effects
     * @returns {string} HTML for effects section
     */
    renderEffectsSection(item) {
        if (!item.effects || item.effects.length === 0) {
            return '';
        }
        
        let html = `
            <div class="details-section">
                <h3 class="section-title">Known Effects</h3>
                <div class="targets-list">`;
        
        item.effects.forEach(effect => {
            html += `
                <div class="target-item">
                    <strong>${effect.name || 'Unnamed Effect'}</strong>
                    ${effect.description ? `<div>${effect.description}</div>` : ''}
                    ${effect.category ? `<div><span>Category:</span> ${effect.category}</div>` : ''}
                    ${effect.mechanism ? `<div><span>Mechanism:</span> ${effect.mechanism}</div>` : ''}
                </div>`;
        });
        
        html += `
                </div>
            </div>`;
        
        return html;
    }
    
    /**
     * Format relationship type for display
     * @param {string} relType - The relationship type
     * @returns {string} - Formatted relationship type
     */
    formatRelationshipType(relType) {
        if (!relType) return '';
        
        // Convert UPPERCASE_WITH_UNDERSCORES to readable text
        return relType
            .replace(/_/g, ' ')
            .toLowerCase()
            .replace(/\b\w/g, l => l.toUpperCase());
    }
    
    /**
     * Process the enrichment of a molecule with external data
     * @param {Event} event - Click event
     * @param {string} itemId - ID of the molecule to enrich
     */
    async enrichMolecule(event, itemId) {
        console.log(`Enrichment button or child clicked: ${event.target}`);
        
        // Determine if we clicked the button itself or a child
        let button = event.target;
        if (!button.classList.contains('enrichment-button')) {
            button = button.closest('.enrichment-button');
        }
        
        if (!button) {
            console.error('Could not find enrichment button');
            return;
        }
        
        // Disable button and show loading state
        button.disabled = true;
        const originalContent = button.innerHTML;
        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 enrichment-spinner" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Loading...
        `;
        
        try {
            // Get the molecule in loaded items
            const foundItem = this.findItemById(itemId);
            if (!foundItem) {
                throw new Error(`Molecule with ID ${itemId} not found in loaded items`);
            }
            
            // Prepare identifiers for enrichment
            const identifiers = {};
            
            // Add all available identifiers
            if (foundItem.inchikey) identifiers.inchikey = foundItem.inchikey;
            if (foundItem.inchi_key) identifiers.inchikey = foundItem.inchi_key;
            if (foundItem.smiles) identifiers.smiles = foundItem.smiles;
            if (foundItem.name) identifiers.name = foundItem.name;
            if (foundItem.cas_number) identifiers.cas_number = foundItem.cas_number;
            if (foundItem.pubchem_cid) identifiers.pubchem_cid = foundItem.pubchem_cid;
            
            // Send enrichment request - this now returns job info
            const jobResponse = await this.api.enrichMolecule(itemId, identifiers);
            console.log('Enrichment job queued:', jobResponse);
            
            // Show waiting message
            const messageContainer = document.getElementById(`enrichment-message-${itemId}`);
            if (messageContainer) {
                messageContainer.textContent = '⏳ Enriching molecule... This may take a few moments.';
                messageContainer.classList.remove('opacity-0');
            }
            
            // Update button to show progress
            button.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 enrichment-spinner animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Processing...
            `;
            
            // Poll for job completion (if we have a job ID)
            if (jobResponse && jobResponse.job_id) {
                const jobId = jobResponse.job_id;
                let jobComplete = false;
                let attempts = 0;
                const maxAttempts = 30; // Max 30 attempts (30 seconds if using 1 second interval)
                
                // Define a polling function
                const pollJobStatus = async () => {
                    try {
                        // Check job status
                        const jobStatus = await fetch(`/api/jobs/${jobId}`).then(r => r.json());
                        console.log(`Job ${jobId} status:`, jobStatus);
                        
                        if (jobStatus.job && jobStatus.job.status === 'completed') {
                            jobComplete = true;
                            // Reload the molecule data to reflect enrichment
                            await this.reloadMoleculeData(itemId);
                            
                            // Show success message
                            if (messageContainer) {
                                messageContainer.textContent = '✓ Successfully enriched! Data has been updated.';
                                setTimeout(() => {
                                    messageContainer.classList.add('opacity-0');
                                }, 3000);
                            }
                            
                            // Update button to show completed
                            button.innerHTML = `
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Already Enriched
                            `;
                            button.disabled = true;
                            
                            return true;
                        } else if (jobStatus.job && jobStatus.job.status === 'failed') {
                            jobComplete = true;
                            throw new Error(`Job failed: ${jobStatus.job.error || 'Unknown error'}`);
                        }
                        
                        // Check if we've reached max attempts
                        attempts++;
                        if (attempts >= maxAttempts) {
                            throw new Error('Enrichment timed out. Please try again later.');
                        }
                        
                        // Continue polling
                        return false;
                    } catch (error) {
                        console.error('Error polling job status:', error);
                        throw error;
                    }
                };
                
                // Start polling
                while (!jobComplete && attempts < maxAttempts) {
                    const isDone = await pollJobStatus();
                    if (isDone) break;
                    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second between polls
                }
            } else {
                // No job ID, assume direct update was done
                await this.reloadMoleculeData(itemId);
                
                // Success message
                if (messageContainer) {
                    messageContainer.textContent = '✓ Successfully enriched! Data has been updated.';
                    setTimeout(() => {
                        messageContainer.classList.add('opacity-0');
                    }, 3000);
                }
                
                // Update button to show completed
                button.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Already Enriched
                `;
                button.disabled = true;
            }
            
        } catch (error) {
            console.error('Error during enrichment:', error);
            
            // Show error in the button
            button.innerHTML = originalContent;
            button.disabled = false;
            
            // Error message
            const messageContainer = document.getElementById(`enrichment-message-${itemId}`);
            if (messageContainer) {
                messageContainer.textContent = `⚠ Error: ${error.message}`;
                messageContainer.classList.remove('opacity-0');
                messageContainer.style.color = '#b91c1c'; // Red error color
                
                // Fade out after 5 seconds
                setTimeout(() => {
                    messageContainer.classList.add('opacity-0');
                    // Reset color after fade out
                    setTimeout(() => {
                        messageContainer.style.color = '#16a34a'; // Back to green for future success messages
                    }, 1000);
                }, 5000);
            }
        }
    }
    
    /**
     * Reload a molecule's data after changes
     * @param {string} itemId - ID of the molecule to reload
     */
    async reloadMoleculeData(itemId) {
        console.log(`Reloading molecule data for ID: ${itemId}`);
        
        // Try different ID formats if needed
        const idsToTry = [itemId];
        
        // Check for original_id vs standardized ID
        const foundItem = this.findItemById(itemId);
        if (foundItem && foundItem.original_id && foundItem.original_id !== itemId) {
            idsToTry.push(foundItem.original_id);
        }
        
        console.log(`Will try these IDs in sequence: ${idsToTry.join(', ')}`);
        
        // Try each ID format
        for (const id of idsToTry) {
            try {
                console.log(`Trying to load molecule with ID: ${id}`);
                const updatedMolecule = await this.api.getMolecule(id);
                
                // Update the item in our loaded items
                this.updateLoadedItem(updatedMolecule);
                
                // Refresh the details view
                if (this.currentItemId === itemId || this.currentItemId === id) {
                    if (this.detailsContent) {
                        this.detailsContent.innerHTML = this.getItemDetailHtml(updatedMolecule);
                    }
                }
                
                console.log(`Successfully loaded updated molecule data: ${updatedMolecule}`);
                return updatedMolecule;
            } catch (error) {
                console.log(`Failed to get molecule with ID ${id}: ${error.message}`);
                continue;
            }
        }
        
        // If we got here, all ID formats failed
        console.log('Trying fetchItemDetails as fallback');
        try {
            // Use the fetchItemDetails as a fallback, as it uses already loaded data
            const updatedItem = await this.fetchItemDetails(itemId, true);
            console.log(`Successfully reloaded molecule with updated data: ${updatedItem}`);
            return updatedItem;
        } catch (error) {
            console.error(`Could not reload molecule with any ID format: ${error.message}`);
            throw error;
        }
    }

    /**
     * Create a new molecule
     * @param {Object} formData - Form data for the new molecule
     * @returns {Promise<Object>} The created molecule
     */
    async createItem(formData) {
        return this.api.createOrUpdateMolecule(formData);
    }

    /**
     * Get form data as an object
     * @returns {Object} Form data object with molecule field values
     */
    getFormData() {
        const molecule = {
            name: document.getElementById('moleculeName').value.trim(),
            cas_number: document.getElementById('moleculeCAS').value.trim(),
            pubchem_cid: document.getElementById('moleculePubChemCID').value.trim(),
            inchikey: document.getElementById('moleculeInChIKey').value.trim(),
            smiles: document.getElementById('moleculeSMILES').value.trim(),
            chembl_id: document.getElementById('moleculeChEMBL').value.trim()
        };
        
        // Remove empty values
        Object.keys(molecule).forEach(key => {
            if (molecule[key] === '') {
                delete molecule[key];
            }
        });
        
        // Validate - ensure at least one field is filled
        if (Object.keys(molecule).length === 0) {
            throw new Error('Please fill at least one identifier field');
        }
        
        return molecule;
    }

    // Override fetchItems to add retry logic specific to molecules
    async fetchItems() {
        try {
            console.log("Fetching molecules...");
            // Make up to 3 attempts
            for (let attempt = 1; attempt <= 3; attempt++) {
                try {
                    // Call the parent class fetchItems
                    await super.fetchItems();
                    
                    // If successful, break out of retry loop
                    console.log("Successfully fetched molecules on attempt", attempt);
                    return;
                } catch (error) {
                    console.error(`Attempt ${attempt} failed to fetch molecules:`, error);
                    
                    if (attempt < 3) {
                        // Wait before retrying (increasing delay with each attempt)
                        const delay = attempt * 1000; // 1s, 2s, 3s
                        console.log(`Retrying in ${delay}ms...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    } else {
                        // Last attempt failed, let the error propagate
                        throw error;
                    }
                }
            }
        } catch (error) {
            console.error("All attempts to fetch molecules failed:", error);
            
            // Display error in the items list
            if (this.itemsList) {
                this.itemsList.innerHTML = `
                    <div class="error-message">
                        <p>Error loading molecules: ${error.message}</p>
                        <p>Please check that the database is running and properly configured.</p>
                        <button class="retry-button" onclick="try { window.moleculesPage.fetchItems(); } catch(e) { location.reload(); }">Retry</button>
                    </div>
                `;
            }
        }
    }

    /**
     * Load and display the molecular structure for a molecule
     * @param {string} moleculeId - ID of the molecule
     */
    async loadMoleculeStructure(moleculeId) {
        const structureContainer = document.getElementById(`molecule-structure-${moleculeId}`);
        if (!structureContainer) return;
        
        try {
            // Show loading indicator
            structureContainer.innerHTML = '<div class="loading-spinner-small">Loading...</div>';
            
            // Fetch the structure image as base64
            const structureData = await this.api.getMoleculeStructureBase64(moleculeId);
            
            // Display the structure image
            if (structureData && structureData.image) {
                structureContainer.innerHTML = `
                    <img src="${structureData.image}" alt="Molecular structure" class="molecule-structure-img-small" />
                `;
            } else {
                throw new Error('No structure data returned');
            }
        } catch (error) {
            console.error('Error loading molecule structure:', error);
            structureContainer.innerHTML = `
                <div class="error-message-small">
                    Error loading structure
                </div>
            `;
        }
    }

    /**
     * Toggle fullscreen display of a molecular structure
     * @param {string} elementId - ID of the structure container element
     */
    toggleFullscreenStructure(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        if (!document.fullscreenElement) {
            element.requestFullscreen().catch(err => {
                console.error(`Error attempting to enable fullscreen mode: ${err.message}`);
            });
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        }
    }

    /**
     * Override parent method to fetch and display item details
     * @param {string} itemId - ID of the item to display
     * @param {boolean} skipApiCall - If true, skip API call and use loaded items
     * @returns {Object} The item details
     */
    async fetchItemDetails(itemId, skipApiCall = false) {
        const item = await super.fetchItemDetails(itemId, skipApiCall);
        
        // Load the structure image if the item has SMILES
        if (item && item.smiles) {
            setTimeout(() => {
                this.loadMoleculeStructure(item.id);
            }, 100);
        }
        
        return item;
    }
}

// Extend HyperBlendAPI with molecule-specific methods
HyperBlendAPI.prototype.createOrUpdateMolecule = async function(molecule) {
    console.log("HyperBlendAPI.prototype.createOrUpdateMolecule called with:", molecule);
    
    // Ensure we have data
    if (!molecule || typeof molecule !== 'object' || Object.keys(molecule).length === 0) {
        throw new Error("No valid molecule data provided");
    }
    
    // Clone the data to avoid modifications to the original object
    const data = JSON.parse(JSON.stringify(molecule));
    
    console.log("Sending to server from prototype method:", data);
    
    return this.fetchJson('/molecules/create_or_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
};

HyperBlendAPI.prototype.enrichMolecule = async function(moleculeId, identifiers) {
    return this.fetchJson(`/molecules/${moleculeId}/enrich`, {
        method: 'POST',
        body: JSON.stringify({ identifiers })
    });
};

HyperBlendAPI.prototype.migrateMoleculeIds = async function() {
    return this.fetchJson('/api/molecules/migrate_ids', {
        method: 'POST'
    });
};

// Function that can be called from the global scope
function initializeMoleculePage() {
    // Only initialize if not already initialized
    if (!window.moleculePage) {
        window.moleculePage = new MoleculePage();
        console.log('Molecules page initialized via initializeMoleculePage');
    }
}

/**
 * Load molecule details into the third column when a molecule is clicked
 * @param {string} moleculeId - The ID of the molecule to load
 */
function loadMoleculeDetails(moleculeId) {
    console.log(`Loading details for molecule: ${moleculeId}`);
    
    // Show loading indicator in the details panel
    const detailsPanel = document.getElementById('itemDetailsContent');
    if (detailsPanel) {
        detailsPanel.innerHTML = '<div class="loading-spinner">Loading...</div>';
    }
    
    // Use the existing API format
    fetch(`/api/molecules/${moleculeId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(molecule => {
            displayMoleculeDetails(molecule);
        })
        .catch(error => {
            console.error('Error loading molecule details:', error);
            if (detailsPanel) {
                detailsPanel.innerHTML = `<div class="error-message">Error loading molecule details: ${error.message}</div>`;
            }
        });
}

/**
 * Display molecule details in the details panel
 * @param {Object} molecule - The molecule data to display
 */
function displayMoleculeDetails(molecule) {
    const detailsPanel = document.getElementById('itemDetailsContent');
    if (!detailsPanel) return;
    
    console.log('Displaying molecule details:', molecule);
    
    // Update the title in the header
    const detailsTitle = document.getElementById('itemDetailsTitle');
    if (detailsTitle) {
        detailsTitle.textContent = molecule.name || 'Molecule Details';
    }
    
    // Group properties by category
    const categories = categorizeProperties(molecule);
    
    // Build the HTML for the details panel
    let detailsHtml = '';
    
    // Render identifiers section
    if (categories.identifiers.length > 0) {
        detailsHtml += `
            <div class="details-section">
                <h3 class="section-title">Identifiers</h3>
                <div class="property-list">`;
        
        categories.identifiers.forEach(prop => {
            detailsHtml += `
                <div class="property-item">
                    <div class="property-label">${formatPropertyName(prop.key)}</div>
                    <div class="property-value">${formatPropertyValue(prop.value)}</div>
                </div>`;
        });
        
        detailsHtml += `
                </div>
            </div>`;
    }
    
    // Render chemical properties section
    if (categories.chemical.length > 0) {
        detailsHtml += `
            <div class="details-section">
                <h3 class="section-title">Chemical Properties</h3>
                <div class="property-list">`;
        
        categories.chemical.forEach(prop => {
            detailsHtml += `
                <div class="property-item">
                    <div class="property-label">${formatPropertyName(prop.key)}</div>
                    <div class="property-value">${formatPropertyValue(prop.value)}</div>
                </div>`;
        });
        
        detailsHtml += `
                </div>
            </div>`;
    }
    
    detailsHtml += `
        <div class="details-section">
            <h3 class="section-title">Additional Information</h3>
            <div class="property-list">`;
    
    // Render additional properties
    const additionalProperties = [
        { key: 'molecular_weight', label: 'Molecular Weight' },
        { key: 'cas_number', label: 'CAS Number' },
        { key: 'pubchem_cid', label: 'PubChem CID' },
        { key: 'inchikey', label: 'InChI Key' },
        { key: 'smiles', label: 'SMILES' },
        { key: 'chembl_id', label: 'ChEMBL ID' }
    ];
    
    additionalProperties.forEach(prop => {
        detailsHtml += `
            <div class="property-item">
                <div class="property-label">${formatPropertyName(prop.key)}</div>
                <div class="property-value">${formatPropertyValue(molecule[prop.key])}</div>
            </div>`;
    });
    
    detailsHtml += `
        </div>
    </div>`;
    
    detailsHtml += `
        <div class="details-section">
            <h3 class="section-title">Identifiers</h3>
            <div class="property-list">`;
    
    // Render identifiers
    const identifiers = [
        { key: 'HyperBlend ID', value: molecule.id },
        { key: 'Original ID', value: molecule.original_id },
        { key: 'DrugBank ID', value: molecule.drugbank_id },
        { key: 'CAS Number', value: molecule.cas_number },
        { key: 'PubChem CID', value: molecule.pubchem_cid },
        { key: 'InChI Key', value: molecule.inchikey },
        { key: 'SMILES', value: molecule.smiles },
        { key: 'ChEMBL ID', value: molecule.chembl_id }
    ];
    
    identifiers.forEach(prop => {
        detailsHtml += `
            <div class="property-item">
                <div class="property-label">${formatPropertyName(prop.key)}</div>
                <div class="property-value">${formatPropertyValue(prop.value)}</div>
            </div>`;
    });
    
    detailsHtml += `
        </div>
    </div>`;
    
    detailsHtml += `
        <div class="details-section">
            <h3 class="section-title">Structure</h3>
            <div class="structure-container">
                <div class="molecule-structure" id="molecule-structure-${molecule.id}">
                    <div class="loading-spinner">Loading structure...</div>
                </div>
                <div class="structure-actions">
                    <button class="action-button" onclick="window.moleculePage.toggleFullscreenStructure('molecule-structure-${molecule.id}')">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrows-fullscreen" viewBox="0 0 16 16">
                            <path fill-rule="evenodd" d="M5.828 10.172a.5.5 0 0 0-.707 0l-4.096 4.096V11.5a.5.5 0 0 0-1 0v3.975a.5.5 0 0 0 .5.5H4.5a.5.5 0 0 0 0-1H1.732l4.096-4.096a.5.5 0 0 0 0-.707zm4.344 0a.5.5 0 0 1 .707 0l4.096 4.096V11.5a.5.5 0 1 1 1 0v3.975a.5.5 0 0 1-.5.5H11.5a.5.5 0 0 1 0-1h2.768l-4.096-4.096a.5.5 0 0 1 0-.707zm0-4.344a.5.5 0 0 0 .707 0l4.096-4.096V4.5a.5.5 0 1 0 1 0V.525a.5.5 0 0 0-.5-.5H11.5a.5.5 0 0 0 0 1h2.768l-4.096 4.096a.5.5 0 0 0 0 .707zm-4.344 0a.5.5 0 0 1-.707 0L1.025 1.732V4.5a.5.5 0 0 1-1 0V.525a.5.5 0 0 1 .5-.5H4.5a.5.5 0 0 1 0 1H1.732l4.096 4.096a.5.5 0 0 1 0 .707z"/>
                        </svg>
                        Full Screen
                    </button>
                </div>
            </div>
        </div>`;
    
    detailsHtml += `
        <div class="details-section">
            <h3 class="section-title">Targets</h3>
            <div class="property-list">`;
    
    // Render targets
    if (molecule.targets && molecule.targets.length > 0) {
        molecule.targets.forEach(target => {
            detailsHtml += `
                <div class="property-item">
                    <div class="property-label">${formatPropertyName(target.name)}</div>
                    <div class="property-value">${formatPropertyValue(target.description)}</div>
                </div>`;
        });
    } else {
        detailsHtml += `
            <div class="property-item">
                <div class="property-label">No targets found</div>
                <div class="property-value">This molecule has no targets associated with it.</div>
            </div>`;
    }
    
    detailsHtml += `
        </div>
    </div>`;
    
    detailsHtml += `
        <div class="details-section">
            <h3 class="section-title">Effects</h3>
            <div class="property-list">`;
    
    // Render effects
    if (molecule.effects && molecule.effects.length > 0) {
        molecule.effects.forEach(effect => {
            detailsHtml += `
                <div class="property-item">
                    <div class="property-label">${formatPropertyName(effect.name)}</div>
                    <div class="property-value">${formatPropertyValue(effect.description)}</div>
                </div>`;
        });
    } else {
        detailsHtml += `
            <div class="property-item">
                <div class="property-label">No effects found</div>
                <div class="property-value">This molecule has no effects associated with it.</div>
            </div>`;
    }
    
    detailsHtml += `
        </div>
    </div>`;

    // Set the HTML content of the details panel
    detailsPanel.innerHTML = detailsHtml;

    // Load the molecule structure if it has SMILES data
    if (molecule.smiles) {
        setTimeout(() => {
            if (window.moleculePage) {
                window.moleculePage.loadMoleculeStructure(molecule.id);
            }
        }, 100);
    }
}

// Initialize when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('molecules.js: Document loaded, initializing');
    
    // Only initialize if not already initialized
    if (!window.moleculePage) {
        window.moleculePage = new MoleculePage();
        console.log('Molecules page initialized');
    }
});