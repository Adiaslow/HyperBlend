// hyperblend/app/web/static/js/graph.js

class GraphVisualization {
    constructor(containerId) {
        console.log('Initializing graph visualization for container:', containerId);
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id '${containerId}' not found`);
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

        // Initialize layout based on available libraries
        if (typeof cola !== 'undefined') {
            console.log('Using WebCola layout engine');
            this.layout = cola.d3adaptor()
                .size([this.width, this.height])
                .linkDistance(100)
                .avoidOverlaps(true)
                .convergenceThreshold(0.01)
                .symmetricDiffLinkLengths(5)
                .flowLayout('y', 80)
                .jaccardLinkLengths(40, 0.7);
        } else {
            console.log('WebCola not available, falling back to D3 force simulation');
            this.layout = d3.forceSimulation()
                .force('link', d3.forceLink().id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-200))
                .force('center', d3.forceCenter(this.width / 2, this.height / 2))
                .force('collision', d3.forceCollide().radius(50))
                .force('x', d3.forceX(this.width / 2).strength(0.1))
                .force('y', d3.forceY(this.height / 2).strength(0.1));
        }

        // Create event emitter
        this.eventEmitter = new EventEmitter();

        // Bind methods
        this.handleNodeClick = this.handleNodeClick.bind(this);
        this.handleZoom = this.handleZoom.bind(this);
        this.handleDragStart = this.handleDragStart.bind(this);
        this.handleDrag = this.handleDrag.bind(this);
        this.handleDragEnd = this.handleDragEnd.bind(this);

        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.2, 4])  // Increased minimum zoom level
            .on('zoom', this.handleZoom);
        
        // Initialize with identity transform to prevent initial jump
        this.svg.call(zoom)
            .call(zoom.transform, d3.zoomIdentity);

        // Store zoom function for later use
        this.zoom = zoom;

        console.log('Graph visualization initialized');
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

        console.log('Updating graph with data:', data);

        // Clear existing elements
        this.g.selectAll('*').remove();

        // Create link elements
        const links = this.g.append('g')
            .selectAll('line')
            .data(data.links)
            .enter()
            .append('line')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', 1);

        // Create node elements
        const nodes = this.g.append('g')
            .selectAll('circle')
            .data(data.nodes)
            .enter()
            .append('circle')
            .attr('r', d => d.width / 2 || 15)
            .attr('fill', d => this.getNodeColor(d.type))
            .call(d3.drag()
                .on('start', this.handleDragStart)
                .on('drag', this.handleDrag)
                .on('end', this.handleDragEnd))
            .on('click', this.handleNodeClick);

        // Add node labels
        const labels = this.g.append('g')
            .selectAll('text')
            .data(data.nodes)
            .enter()
            .append('text')
            .text(d => d.name || 'Unknown')
            .attr('font-size', '12px')
            .attr('dx', 8)
            .attr('dy', 3);

        // Update layout based on type
        if (typeof cola !== 'undefined') {
            // WebCola layout
            this.layout
                .nodes(data.nodes)
                .links(data.links)
                .start(50, 0, 50);

            // Update positions on each tick
            this.layout.on('tick', () => {
                links
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);

                nodes
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);

                labels
                    .attr('x', d => d.x)
                    .attr('y', d => d.y);
            });
        } else {
            // D3 force simulation
            this.layout
                .nodes(data.nodes)
                .on('tick', () => {
                    links
                        .attr('x1', d => d.source.x)
                        .attr('y1', d => d.source.y)
                        .attr('x2', d => d.target.x)
                        .attr('y2', d => d.target.y);

                    nodes
                        .attr('cx', d => d.x)
                        .attr('cy', d => d.y);

                    labels
                        .attr('x', d => d.x)
                        .attr('y', d => d.y);
                });

            this.layout.force('link')
                .links(data.links)
                .id(d => d.id)
                .distance(d => d.weight || 100);

            this.layout.alpha(1).restart();
        }

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

            // Adjust scale calculation to prevent too small initial view
            const scale = Math.min(2, 0.9 / Math.max(width / fullWidth, height / fullHeight));
            const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

            // Apply the initial transform with a smoother transition
            this.svg.transition()
                .duration(1000)
                .call(this.zoom.transform, d3.zoomIdentity
                    .translate(translate[0], translate[1])
                    .scale(scale));
        }, 200);  // Increased delay for better initial layout

        console.log('Graph data updated successfully');
    }

    getNodeColor(type) {
        const colors = {
            'Compound': '#4CAF50',
            'Source': '#2196F3',
            'Target': '#F44336',
            'default': '#9E9E9E'
        };
        return colors[type] || colors.default;
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
        if (typeof cola !== 'undefined') {
            d.fixed = true;
        } else {
            if (!event.active) this.layout.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
    }

    handleDrag(event, d) {
        if (typeof cola !== 'undefined') {
            d.x = event.x;
            d.y = event.y;
            this.layout.resume();
        } else {
            d.fx = event.x;
            d.fy = event.y;
        }
    }

    handleDragEnd(event, d) {
        if (typeof cola !== 'undefined') {
            d.fixed = false;
            this.layout.resume();
        } else {
            if (!event.active) this.layout.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    }

    on(event, callback) {
        this.eventEmitter.on(event, callback);
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