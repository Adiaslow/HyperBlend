// hyperblend/app/web/static/js/graph.js

class GraphVisualization {
    constructor(containerId) {
        console.log('Initializing graph visualization for container:', containerId);
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id '${containerId}' not found`);
            return;
        }

        this.initialized = false;
        this.initialize();
    }

    initialize() {
        if (!this.container) {
            return;
        }

        // Initialize layout
        this.width = this.container.clientWidth || 800;
        this.height = this.container.clientHeight || 600;
        console.log('Graph dimensions:', this.width, 'x', this.height);

        // Create SVG container
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);

        // Create a group for zooming
        this.g = this.svg.append('g');

        // Initialize event emitter
        this.eventEmitter = new EventEmitter();

        // Initialize layout based on available libraries
        console.log('Using D3 force simulation');
        this.layout = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id)
                .distance(d => {
                    // Adjust link distance based on node types
                    const sourceType = d.source.type;
                    const targetType = d.target.type;
                    if (sourceType === 'Molecule' && targetType === 'Target') {
                        return 100;  // Longer distance for molecule-target interactions
                    }
                    if (sourceType === 'Target' && targetType === 'Target') {
                        return 75;  // Medium distance for target-target relationships
                    }
                    return 50;  // Default distance for other relationships
                })
                .strength(0.5))  // Reduced link strength for more flexibility
            .force('charge', d3.forceManyBody()
                .strength(d => {
                    // Adjust repulsion force based on node type
                    switch(d.type) {
                        case 'Molecule':
                            return -1000;  // Strong repulsion for molecules
                        case 'Target':
                            return -800;   // Medium repulsion for targets
                        default:
                            return -500;   // Default repulsion
                    }
                })
                .distanceMax(500))
            .force('collide', d3.forceCollide()
                .radius(d => this.getNodeSize(d.type) * 1.5)  // Increased padding around nodes
                .strength(0.8))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2).strength(0.1))
            .force('x', d3.forceX(this.width / 2).strength(0.05))
            .force('y', d3.forceY(this.height / 2).strength(0.05))
            .alphaDecay(0.02)  // Slightly faster decay for quicker stabilization
            .velocityDecay(0.4);  // More friction to prevent excessive movement

        // Bind methods
        this.handleNodeClick = this.handleNodeClick.bind(this);
        this.handleZoom = this.handleZoom.bind(this);
        this.handleDragStart = this.handleDragStart.bind(this);
        this.handleDrag = this.handleDrag.bind(this);
        this.handleDragEnd = this.handleDragEnd.bind(this);

        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 8])  // Allow more zoom range
            .on('zoom', this.handleZoom);

        // Initialize with identity transform to prevent initial jump
        this.svg.call(zoom)
            .call(zoom.transform, d3.zoomIdentity);

        // Store zoom function for later use
        this.zoom = zoom;

        this.initialized = true;
        console.log('Graph visualization initialized successfully');
    }

    updateData(data) {
        if (!this.svg) {
            console.error('SVG container not found');
            return;
        }

        if (!data || !data.nodes || !data.links) {
            console.error('Invalid data format:', data);
            return;
        }

        console.log('Raw data received:', JSON.stringify(data, null, 2));
        console.log('Number of nodes:', data.nodes.length);
        console.log('Number of links:', data.links.length);

        // Format data for D3
        const nodes = data.nodes.map(node => ({
            ...node,
            // Initialize position if not set
            x: node.x || Math.random() * this.width,
            y: node.y || Math.random() * this.height,
            // Set node size based on type
            width: this.getNodeSize(node.type)
        }));

        const links = data.links.map(link => {
            console.log('Processing link:', link);
            const source = typeof link.source === 'object' ? link.source.id : link.source;
            const target = typeof link.target === 'object' ? link.target.id : link.target;
            
            return {
                ...link,
                source: source,
                target: target,
                weight: link.weight || 1
            };
        });

        console.log('Processed nodes:', nodes);
        console.log('Processed links:', links);

        // Clear existing elements
        this.g.selectAll('*').remove();

        // Create arrow marker for each activity type
        const markerColors = {
            'agonist': '#22C55E',
            'antagonist': '#DC2626',
            'partial_agonist': '#84CC16',
            'inverse_agonist': '#EA580C',
            'inhibitor': '#7C3AED',  // Violet color for inhibitors
            'activator': '#2563EB',  // Blue color for activators
            'default': '#94A3B8'
        };

        // Create markers for each color
        const defs = this.g.append('defs');
        Object.entries(markerColors).forEach(([type, color]) => {
            defs.append('marker')
                .attr('id', `arrow-${type}`)
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 25)
                .attr('refY', 0)
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .attr('orient', 'auto')
                .append('path')
                .attr('d', 'M0,-5L10,0L0,5')
                .attr('fill', color);
        });

        // Create link elements with tooltips
        const linkGroup = this.g.append('g')
            .attr('class', 'links');

        const linkElements = linkGroup.selectAll('g')
            .data(links)
            .enter()
            .append('g')
            .attr('class', 'link-group');

        // Add the actual line elements
        linkElements.append('line')
            .attr('class', 'link')
            .attr('stroke', d => this.getEdgeColor(d))
            .attr('stroke-opacity', 0.8)
            .attr('stroke-width', d => this.getEdgeWidth(d))
            .attr('stroke-dasharray', d => this.getEdgeDashArray(d))
            .attr('marker-end', d => {
                const type = d.activity_type ? d.activity_type.toLowerCase() : 'default';
                return `url(#arrow-${type})`;
            });

        // Add tooltips for links
        linkElements.append('title')
            .text(d => {
                let tooltip = d.type || 'Relationship';
                if (d.activity_type) tooltip += `\nActivity: ${d.activity_type}`;
                if (d.activity_value) tooltip += `\nValue: ${d.activity_value}`;
                if (d.activity_unit) tooltip += ` ${d.activity_unit}`;
                if (d.confidence_score) tooltip += `\nConfidence: ${d.confidence_score}`;
                return tooltip;
            });

        // Create node elements with tooltips
        const nodeGroup = this.g.append('g')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .call(d3.drag()
                .on('start', this.handleDragStart)
                .on('drag', this.handleDrag)
                .on('end', this.handleDragEnd))
            .on('click', this.handleNodeClick);

        // Add circle to each node group
        const nodeElements = nodeGroup.append('circle')
            .attr('r', d => d.width / 2)
            .attr('fill', d => this.getNodeColor(d.type));

        // Add tooltips for nodes
        nodeGroup.append('title')
            .text(d => {
                let tooltip = `${d.name} (${d.type})`;
                if (d.smiles) tooltip += `\nSMILES: ${d.smiles}`;
                if (d.molecular_weight) tooltip += `\nMW: ${d.molecular_weight}`;
                if (d.formula) tooltip += `\nFormula: ${d.formula}`;
                if (d.description) tooltip += `\nDescription: ${d.description}`;
                return tooltip;
            });

        // Add node labels with background
        const labels = nodeGroup.append('g')
            .attr('class', 'label');

        // Calculate text width for centering
        const tempText = labels.append('text')
            .text(d => d.name || 'Unknown')
            .attr('font-size', '12px')
            .style('visibility', 'hidden');

        // Add white background for better readability
        labels.append('text')
            .text(d => d.name || 'Unknown')
            .attr('font-size', '12px')
            .attr('text-anchor', 'middle')
            .attr('dy', d => d.width / 2 + 16)  // Position below node with padding
            .attr('stroke', 'white')
            .attr('stroke-width', 3)
            .attr('stroke-opacity', 0.8);

        // Add actual text
        labels.append('text')
            .text(d => d.name || 'Unknown')
            .attr('font-size', '12px')
            .attr('text-anchor', 'middle')  // Center the text
            .attr('dy', d => d.width / 2 + 16);  // Position below node with padding

        // Remove the temporary text element
        tempText.remove();

        // Update the simulation
        this.layout
            .nodes(nodes)
            .force('link')
            .links(links);

        // Set up the tick handler
        this.layout.on('tick', () => {
            // Update link positions
            linkElements.selectAll('line')
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            // Update node positions
            nodeElements
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);

            // Update label positions
            labels
                .attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // Create drag behavior
        const drag = d3.drag()
            .on('start', (event, d) => {
                if (!event.active) this.layout.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            })
            .on('drag', (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on('end', (event, d) => {
                if (!event.active) this.layout.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            });

        // Apply drag behavior to nodes
        nodeGroup.call(drag);

        // Start the simulation
        this.layout.alpha(1).restart();

        // Store the nodes and links for later use
        this.nodes = nodes;
        this.links = links;

        // Update the legend to include relationship types
        this.updateLegend();

        // Fit the graph to the viewport after a short delay
        setTimeout(() => {
            const bounds = this.g.node().getBBox();
            const fullWidth = this.width;
            const fullHeight = this.height;
            const width = bounds.width;
            const height = bounds.height;
            const midX = bounds.x + width / 2;
            const midY = bounds.y + height / 2;

            if (width === 0 || height === 0) return;

            const scale = Math.min(2, 0.9 / Math.max(width / fullWidth, height / fullHeight));
            const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

            this.svg.transition()
                .duration(1000)
                .call(this.zoom.transform, d3.zoomIdentity
                    .translate(translate[0], translate[1])
                    .scale(scale));
        }, 200);

        console.log('Graph data updated successfully');
    }

    getNodeColor(type) {
        switch(type) {
            case 'Molecule':
                return '#10B981';  // Green
            case 'Organism':
                return '#3B82F6';  // Blue
            case 'Target':
                return '#EF4444';  // Red
            default:
                return '#9CA3AF';  // Default gray
        }
    }

    getEdgeColor(relationship) {
        // First check activity type
        if (relationship.activity_type) {
            switch(relationship.activity_type.toLowerCase()) {
                case 'agonist':
                    return '#22C55E';  // Green
                case 'antagonist':
                    return '#DC2626';  // Red
                case 'inhibitor':
                    return '#7C3AED';  // Violet
                case 'activator':
                    return '#2563EB';  // Blue
                case 'substrate':
                    return '#F59E0B';  // Orange
                case 'unknown':
                    return '#94A3B8';  // Gray
                default:
                    return '#94A3B8';  // Gray
            }
        }
        return '#94A3B8';  // Default gray
    }

    getEdgeWidth(relationship) {
        // Base width on relationship type and confidence score
        let baseWidth = 2;
        
        // Adjust width based on relationship type
        switch(relationship.type) {
            case 'HAS_STRUCTURE':
            case 'ENCODED_BY':
                baseWidth = 3;
                break;
            case 'INTERACTS_WITH':
                baseWidth = relationship.activity_type ? 2.5 : 2;
                break;
            case 'ASSOCIATED_WITH':
                baseWidth = 1.5;
                break;
        }

        // Adjust width based on confidence score if available
        if (relationship.confidence_score) {
            baseWidth *= (0.5 + relationship.confidence_score * 0.5);  // Scale between 50% and 100% of base width
        }

        return baseWidth;
    }

    getEdgeDashArray(relationship) {
        // Use dashed lines for certain relationship types
        switch(relationship.type) {
            case 'ASSOCIATED_WITH':
                return '5,5';  // Dashed line
            case 'HAS_STRUCTURE':
                return '1,0';  // Solid line
            default:
                return relationship.activity_type === 'unknown' ? '3,3' : '1,0';  // Dashed for unknown activity
        }
    }

    handleZoom(event) {
        // Add smooth transition for zoom
        this.g.attr('transform', event.transform);
    }

    handleNodeClick(event, d) {
        console.log('Node clicked:', d);
        this.eventEmitter.emit('nodeClick', d);
    }

    handleDragStart(event, d) {
        if (!event.active) this.layout.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    handleDrag(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    handleDragEnd(event, d) {
        if (!event.active) this.layout.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    on(event, callback) {
        if (!this.initialized) {
            console.error('Cannot add event listener - graph not initialized');
            return;
        }
        this.eventEmitter.on(event, callback);
    }

    focusNode(nodeId) {
        // Find the node in the data
        const node = this.layout.nodes().find(n => n.id === nodeId);
        if (!node) {
            console.error('Node not found:', nodeId);
            return;
        }

        // Calculate the transform to center on the node
        const scale = 2;  // Zoom in a bit
        const x = this.width / 2 - node.x * scale;
        const y = this.height / 2 - node.y * scale;

        // Transition to the node
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity
                .translate(x, y)
                .scale(scale));

        // Highlight the node
        this.g.selectAll('circle')
            .transition()
            .duration(750)
            .attr('r', d => d.id === nodeId ? 25 : d.width / 2 || 15)
            .attr('stroke', d => d.id === nodeId ? '#FFD700' : 'none')
            .attr('stroke-width', d => d.id === nodeId ? 3 : 0);

        // Reset highlight after a delay
        setTimeout(() => {
            this.g.selectAll('circle')
                .transition()
                .duration(750)
                .attr('r', d => d.width / 2 || 15)
                .attr('stroke', 'none')
                .attr('stroke-width', 0);
        }, 2000);
    }

    updateLegend() {
        // Find the legend container
        const legend = d3.select('.graph-legend');
        if (!legend.empty()) {
            // Clear existing legend items
            legend.html('');

            // Add node type legend items
            const nodeTypes = [
                { label: 'Molecules', color: '#10B981', type: 'Molecule' },
                { label: 'Organisms', color: '#3B82F6', type: 'Organism' },
                { label: 'Targets', color: '#EF4444', type: 'Target' }
            ];

            // Only show node types that exist in the data
            const existingTypes = new Set(this.nodes.map(n => n.type));
            nodeTypes
                .filter(type => existingTypes.has(type.type))
                .forEach(type => {
                    legend.append('div')
                        .attr('class', 'legend-item')
                        .html(`
                            <span class="legend-color" style="background-color: ${type.color};"></span>
                            <span class="legend-label">${type.label}</span>
                        `);
                });

            // Add separator
            legend.append('hr')
                .attr('class', 'my-2 border-gray-200');

            // Define allowed relationship types and their colors
            const allowedRelationships = {
                'agonist': '#22C55E',
                'antagonist': '#DC2626',
                'inhibitor': '#7C3AED',
                'activator': '#2563EB',
                'substrate': '#F59E0B',
                'unknown': '#94A3B8'
            };

            // Get unique relationship types from the data
            const relationshipTypes = new Set();
            this.links.forEach(link => {
                if (link.activity_type && allowedRelationships[link.activity_type.toLowerCase()]) {
                    relationshipTypes.add(link.activity_type.toLowerCase());
                }
            });

            // Add relationship type legend items
            Array.from(relationshipTypes)
                .sort()
                .forEach(type => {
                    const color = allowedRelationships[type];
                    const label = type.charAt(0).toUpperCase() + type.slice(1);
                    legend.append('div')
                        .attr('class', 'legend-item')
                        .html(`
                            <div class="flex items-center">
                                <div class="w-8 h-0.5" style="background-color: ${color};"></div>
                                <div class="legend-color" style="background-color: ${color}; transform: rotate(45deg); width: 6px; height: 6px; margin-left: -3px;"></div>
                            </div>
                            <span class="legend-label ml-2">${label}</span>
                        `);
                });
        }
    }

    getNodeSize(type) {
        switch(type) {
            case 'Molecule':
                return 30;  // Slightly larger size for molecules
            case 'Target':
                return 25;  // Medium size for targets
            case 'Disease':
                return 35;  // Medium-large size for diseases
            case 'Gene':
                return 30;  // Medium size for genes
            case 'Protein':
                return 30;  // Medium size for proteins
            case 'Structure':
                return 25;  // Medium-small size for structures
            case 'Source':
                return 20;  // Small size for sources
            case 'Synonym':
                return 15;  // Smallest size for synonyms
            default:
                return 20;  // Default size
        }
    }
}

// Simple event emitter implementation
class EventEmitter {
    constructor() {
        this.events = {};
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }

    emit(event, data) {
        if (this.events[event]) {
            this.events[event].forEach(callback => callback(data));
        }
    }
}

// Node icons by type
const nodeIcons = {
    'Molecule': 'fas fa-atom',
    'Target': 'fas fa-bullseye',
    'Organism': 'fas fa-leaf'
}; 