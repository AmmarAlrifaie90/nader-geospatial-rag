/**
 * 2D Map with Deck.gl + Mapbox
 * Points: ScatterplotLayer, HeatmapLayer, HexagonLayer
 * Polygons: GeoJsonLayer
 * Lines: PathLayer
 */
class Map2D {
    constructor(containerId = 'map2d') {
        this.containerId = containerId;
        this.map = null;
        this.overlay = null;
        this.currentData = [];
        this.currentGeojson = null;
        this.currentLayerType = 'point';
        this.currentRenderMode = 'scatter'; // scatter, heatmap, hexagon
        this.originalBounds = null;
        this.originalPointData = null; // Store original points for spatial join filtering
        this.filteredPointData = null; // Currently filtered points
        this.selectedPolygon = null; // Currently selected polygon for filtering (deprecated - use selectedPolygons)
        this.selectedPolygons = new Map(); // Map of selected polygons: gid -> {feature, geometry, properties}
        this.pointsVisible = true; // Track point visibility state
        this.polygonsVisible = true; // Track polygon visibility state
        this.popupCloseHandler = null; // Handler for closing custom popup
        this.isFiltering = false; // Flag to prevent double-processing
        this.lastPolygonClick = null; // Track last polygon click to prevent double-processing
        this.lastPolygonClickTime = 0; // Timestamp of last click
    }

    async initialize(token) {
        if (!token) {
            console.error('No Mapbox token provided');
            return;
        }

        mapboxgl.accessToken = token;

        this.map = new mapboxgl.Map({
            container: this.containerId,
            style: 'mapbox://styles/mapbox/dark-v11',
            center: [44, 24],
            zoom: 5,
            pitch: 0,
            bearing: 0,
            antialias: true
        });

        this.map.addControl(new mapboxgl.NavigationControl());

        await new Promise(resolve => this.map.on('load', resolve));

        this.overlay = new deck.MapboxOverlay({ layers: [] });
        this.map.addControl(this.overlay);

        this.setupControls();
        console.log('2D Map initialized');
    }

    setupControls() {
        // Controls are now handled by app.js via the Layers panel
        // This method is kept for compatibility but controls are set up elsewhere
        console.log('Map2D controls ready');
    }

    updateControlsVisibility() {
        // Handled by app.js
    }

    updateVisualization(visualization) {
        if (!visualization || !visualization.geojson) return;
        if (!this.overlay) {
            console.warn('2D Map not ready');
            return;
        }

        this.currentGeojson = visualization.geojson;
        this.currentLayerType = visualization.layer_type || 'point';
        this.originalBounds = visualization.bounds;
        this.isAnalysisMode = false;
        
        // Store polygon overlay if present (for spatial joins)
        this.polygonOverlay = visualization.polygon_overlay || null;

        // Convert features to data array for point layers
        if (this.currentLayerType === 'point') {
            this.currentData = visualization.geojson.features.map(f => ({
                position: f.geometry.coordinates,
                longitude: f.geometry.coordinates[0],
                latitude: f.geometry.coordinates[1],
                properties: f.properties
            }));
            // Store original point data for spatial join filtering
            this.originalPointData = [...this.currentData];
            this.filteredPointData = null;
            this.selectedPolygon = null;
            this.selectedPolygons.clear(); // Clear polygon selections when new data loads
        }

        // Update UI - feature count is now in map-info
        const countEl = document.getElementById('feature-count');
        if (countEl) {
            const count = visualization.geojson.features.length;
            countEl.textContent = `${count} ${this.currentLayerType}${count !== 1 ? 's' : ''}`;
        }

        // Remove any existing Mapbox cluster source/layers and polygon overlay
        this.removeClusterLayers();
        this.removePolygonOverlay();

        this.renderLayers();
        
        // If there's a polygon overlay (spatial join), render it
        if (this.polygonOverlay) {
            this.renderPolygonOverlay(this.polygonOverlay);
            this.setupSpatialJoinControls();
            // Default: polygons visible, points hidden
            this.polygonsVisible = true;
            this.pointsVisible = false; // Hide points by default for spatial joins
            const togglePolygons = document.getElementById('toggle-polygons');
            const togglePoints = document.getElementById('toggle-points');
            if (togglePolygons) togglePolygons.checked = true;
            if (togglePoints) togglePoints.checked = false;
            this.togglePolygonVisibility(true);
            this.togglePointVisibility(false);
        } else {
            // Hide controls if no polygon overlay
            const controls = document.getElementById('spatial-join-controls');
            if (controls) {
                controls.classList.add('hidden');
            }
            // Reset visibility flags
            this.pointsVisible = true;
            this.polygonsVisible = true;
        }

        if (visualization.bounds) {
            this.fitBounds(visualization.bounds);
            // Show zoom out button
            const zoomOutBtn = document.getElementById('zoom-out-btn');
            if (zoomOutBtn) {
                zoomOutBtn.classList.remove('hidden');
            }
        } else if (this.currentGeojson && this.currentGeojson.features) {
            // Calculate bounds from features if not provided
            this.fitToFeatures(this.currentGeojson.features);
        }
    }
    
    removePolygonOverlay() {
        // Remove Mapbox layers and source for polygon overlay
        if (this.map) {
            try {
                if (this.map.getLayer('polygon-overlay-fill')) {
                    this.map.removeLayer('polygon-overlay-fill');
                }
                if (this.map.getLayer('polygon-overlay-outline')) {
                    this.map.removeLayer('polygon-overlay-outline');
                }
                if (this.map.getLayer('polygon-overlay-labels')) {
                    this.map.removeLayer('polygon-overlay-labels');
                }
                if (this.map.getSource('polygon-overlay')) {
                    this.map.removeSource('polygon-overlay');
                }
            } catch (e) {
                // Ignore errors if layers don't exist
            }
        }
    }
    
    renderPolygonOverlay(overlayData) {
        if (!this.map || !overlayData || !overlayData.geojson) return;
        
        try {
            // Add the polygon source
            this.map.addSource('polygon-overlay', {
                type: 'geojson',
                data: overlayData.geojson
            });
            
            // Add filled polygons (semi-transparent)
            // Color will be updated dynamically based on selection
            this.map.addLayer({
                id: 'polygon-overlay-fill',
                type: 'fill',
                source: 'polygon-overlay',
                paint: {
                    'fill-color': '#3b82f6', // Default blue
                    'fill-opacity': 0.15
                }
            }, 'points' in this.map.style._layers ? 'points' : undefined);
            
            // Add polygon outlines (visible borders)
            this.map.addLayer({
                id: 'polygon-overlay-outline',
                type: 'line',
                source: 'polygon-overlay',
                paint: {
                    'line-color': '#3b82f6',
                    'line-width': 2,
                    'line-opacity': 0.8
                }
            });
            
            // Add labels showing point count (number only)
            this.map.addLayer({
                id: 'polygon-overlay-labels',
                type: 'symbol',
                source: 'polygon-overlay',
                layout: {
                    'text-field': ['to-string', ['get', 'point_count']],
                    'text-size': 12,
                    'text-anchor': 'center',
                    'text-allow-overlap': true
                },
                paint: {
                    'text-color': '#ffffff',
                    'text-halo-color': '#000000',
                    'text-halo-width': 1
                }
            });
            
            // Remove existing click handler if any
            this.map.off('click', 'polygon-overlay-fill');
            
            // Add click handler for polygons - toggle polygon selection
            this.map.on('click', 'polygon-overlay-fill', (e) => {
                // Stop event propagation to prevent map click handler from interfering
                if (e.originalEvent) {
                    e.originalEvent.stopPropagation();
                    e.originalEvent.stopImmediatePropagation();
                }
                
                if (e.features && e.features.length > 0) {
                    const clickedFeature = e.features[0];
                    const props = clickedFeature.properties;
                    const polygonGeom = clickedFeature.geometry;
                    
                    // Use gid as unique identifier (more reliable than unit_name)
                    // If gid doesn't exist, create a unique key from unit_name + geometry hash
                    let polygonGid = props.gid;
                    if (!polygonGid) {
                        // Fallback: create unique ID from unit_name and a hash of coordinates
                        const coords = JSON.stringify(polygonGeom.coordinates);
                        const hash = coords.split('').reduce((a, b) => {
                            a = ((a << 5) - a) + b.charCodeAt(0);
                            return a & a;
                        }, 0);
                        polygonGid = `${props.unit_name || 'polygon'}-${Math.abs(hash)}`;
                    }
                    polygonGid = String(polygonGid); // Ensure it's a string
                    const unitName = props.unit_name || 'Unknown';
                    
                    // Prevent double-processing of the same click
                    if (this.lastPolygonClick === polygonGid && Date.now() - (this.lastPolygonClickTime || 0) < 300) {
                        console.log('Duplicate click on same polygon ignored');
                        return;
                    }
                    
                    this.lastPolygonClick = polygonGid;
                    this.lastPolygonClickTime = Date.now();
                    
                    // Toggle polygon selection using gid
                    const wasSelected = this.selectedPolygons.has(polygonGid);
                    const beforeCount = this.selectedPolygons.size;
                    
                    if (wasSelected) {
                        // Deselect polygon - remove it from selection
                        console.log('Deselecting polygon:', unitName, 'gid:', polygonGid, '(was selected)');
                        this.selectedPolygons.delete(polygonGid);
                    } else {
                        // Select polygon - add it to selection
                        console.log('Selecting polygon:', unitName, 'gid:', polygonGid, '(was not selected)');
                        this.selectedPolygons.set(polygonGid, {
                            feature: clickedFeature,
                            geometry: polygonGeom,
                            properties: props,
                            gid: polygonGid,
                            unit_name: unitName
                        });
                    }
                    
                    const afterCount = this.selectedPolygons.size;
                    console.log(`Selection changed: ${beforeCount} -> ${afterCount} polygons`);
                    console.log('Selected polygon GIDs:', Array.from(this.selectedPolygons.keys()));
                    
                    // Update point filter based on all selected polygons
                    this.updateFilteredPoints();
                    
                    // Make sure points are visible
                    this.pointsVisible = true;
                    const togglePoints = document.getElementById('toggle-points');
                    if (togglePoints) togglePoints.checked = true;
                    
                    // Show custom popup with polygon info
                    const isNowSelected = this.selectedPolygons.has(polygonGid);
                    this.showPolygonPopup(e.lngLat, props, isNowSelected);
                }
            });
            
            // Change cursor on hover
            this.map.on('mouseenter', 'polygon-overlay-fill', () => {
                this.map.getCanvas().style.cursor = 'pointer';
            });
            this.map.on('mouseleave', 'polygon-overlay-fill', () => {
                this.map.getCanvas().style.cursor = '';
            });
            
        } catch (e) {
            console.error('Failed to render polygon overlay:', e);
        }
    }

    // Special update for analysis results with clustering support
    updateAnalysisVisualization(visualization) {
        if (!visualization || !visualization.geojson) return;
        if (!this.map) {
            console.warn('Map not ready');
            return;
        }

        this.currentGeojson = visualization.geojson;
        this.currentLayerType = 'point';
        this.isAnalysisMode = true;

        // Update feature count
        const countEl = document.getElementById('feature-count');
        if (countEl) {
            const count = visualization.geojson.features.length;
            countEl.textContent = `${count} point${count !== 1 ? 's' : ''}`;
        }

        // Clear deck.gl layers
        if (this.overlay) {
            this.overlay.setProps({ layers: [] });
        }

        // Use Mapbox native clustering for analysis results
        this.renderClusteredAnalysisLayer(visualization.geojson);

        // Fit bounds to data
        this.fitToFeatures(visualization.geojson.features);
    }

    renderClusteredAnalysisLayer(geojson) {
        // Remove existing cluster layers first
        this.removeClusterLayers();

        // Group features by their analysis cluster (so red only clusters with red, white with white, etc.)
        const featuresByCluster = {};
        geojson.features.forEach(f => {
            const clusterId = f.properties.cluster_id === null ? 'unclustered' : String(f.properties.cluster_id);
            if (!featuresByCluster[clusterId]) {
                featuresByCluster[clusterId] = {
                    color: f.properties.color,
                    features: []
                };
            }
            featuresByCluster[clusterId].features.push(f);
        });

        // Create a separate source and layer for each analysis cluster
        Object.entries(featuresByCluster).forEach(([clusterId, data], idx) => {
            const sourceId = `analysis-cluster-${clusterId}`;
            const clusterLayerId = `cluster-circles-${clusterId}`;
            const countLayerId = `cluster-count-${clusterId}`;
            const pointLayerId = `cluster-points-${clusterId}`;

            // Add source with clustering - each analysis cluster clusters separately
            this.map.addSource(sourceId, {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: data.features
                },
                cluster: true,
                clusterMaxZoom: 14,
                clusterRadius: 40,
                clusterMinPoints: 2
            });

            // Clustered circles - use the analysis cluster's color
            this.map.addLayer({
                id: clusterLayerId,
                type: 'circle',
                source: sourceId,
                filter: ['has', 'point_count'],
                paint: {
                    'circle-color': data.color,
                    'circle-radius': [
                        'step',
                        ['get', 'point_count'],
                        14,    // 2-9 points
                        10, 18, // 10-29 points
                        30, 22  // 30+ points
                    ],
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#000',
                    'circle-opacity': 0.9
                }
            });

            // Cluster count labels
            this.map.addLayer({
                id: countLayerId,
                type: 'symbol',
                source: sourceId,
                filter: ['has', 'point_count'],
                layout: {
                    'text-field': '{point_count_abbreviated}',
                    'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
                    'text-size': 11
                },
                paint: {
                    'text-color': data.color === '#ffffff' ? '#000' : '#fff'
                }
            });

            // Individual points - use their assigned color
            this.map.addLayer({
                id: pointLayerId,
                type: 'circle',
                source: sourceId,
                filter: ['!', ['has', 'point_count']],
                paint: {
                    'circle-color': data.color,
                    'circle-radius': 7,
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#000'
                }
            });

            // Click on cluster to zoom in
            this.map.on('click', clusterLayerId, (e) => {
                const features = this.map.queryRenderedFeatures(e.point, { layers: [clusterLayerId] });
                if (!features.length) return;
                const mapboxClusterId = features[0].properties.cluster_id;
                this.map.getSource(sourceId).getClusterExpansionZoom(mapboxClusterId, (err, zoom) => {
                    if (err) return;
                    this.map.easeTo({
                        center: features[0].geometry.coordinates,
                        zoom: zoom
                    });
                });
            });

            // Click on individual point
            this.map.on('click', pointLayerId, (e) => {
                const coords = e.features[0].geometry.coordinates.slice();
                const props = e.features[0].properties;
                
                new mapboxgl.Popup()
                    .setLngLat(coords)
                    .setHTML(`
                        <div class="popup-content">
                            <strong>${props.name || 'Point'}</strong><br>
                            ${props.cluster_name || ''}<br>
                            ${props.commodity || ''}<br>
                            ${props.region || ''}
                        </div>
                    `)
                    .addTo(this.map);
            });

            // Cursor changes
            this.map.on('mouseenter', clusterLayerId, () => {
                this.map.getCanvas().style.cursor = 'pointer';
            });
            this.map.on('mouseleave', clusterLayerId, () => {
                this.map.getCanvas().style.cursor = '';
            });
            this.map.on('mouseenter', pointLayerId, () => {
                this.map.getCanvas().style.cursor = 'pointer';
            });
            this.map.on('mouseleave', pointLayerId, () => {
                this.map.getCanvas().style.cursor = '';
            });
        });
    }

    removeClusterLayers() {
        // Remove old single-source layers (backwards compatibility)
        const oldLayers = ['analysis-clusters', 'analysis-clusters-count', 'analysis-unclustered'];
        const oldSources = ['analysis-points'];

        oldLayers.forEach(id => {
            if (this.map.getLayer(id)) {
                this.map.removeLayer(id);
            }
        });

        oldSources.forEach(id => {
            if (this.map.getSource(id)) {
                this.map.removeSource(id);
            }
        });

        // Remove all cluster-specific layers and sources
        const style = this.map.getStyle();
        if (style && style.layers) {
            const layersToRemove = style.layers
                .filter(l => l.id.startsWith('cluster-'))
                .map(l => l.id);
            
            layersToRemove.forEach(id => {
                if (this.map.getLayer(id)) {
                    this.map.removeLayer(id);
                }
            });
        }

        if (style && style.sources) {
            const sourcesToRemove = Object.keys(style.sources)
                .filter(s => s.startsWith('analysis-cluster-'));
            
            sourcesToRemove.forEach(id => {
                if (this.map.getSource(id)) {
                    this.map.removeSource(id);
                }
            });
        }
    }

    fitToFeatures(features) {
        if (!features || features.length === 0) return;

        const bounds = new mapboxgl.LngLatBounds();
        features.forEach(f => {
            if (f.geometry) {
                if (f.geometry.type === 'Point' && f.geometry.coordinates) {
                    bounds.extend(f.geometry.coordinates);
                } else if (f.geometry.type === 'Polygon' && f.geometry.coordinates) {
                    // For polygons, extend to all coordinates
                    f.geometry.coordinates[0].forEach(coord => bounds.extend(coord));
                } else if (f.geometry.type === 'LineString' && f.geometry.coordinates) {
                    f.geometry.coordinates.forEach(coord => bounds.extend(coord));
                }
            }
        });

        if (!bounds.isEmpty()) {
            // Save bounds for zoom out
            const bbox = bounds.toArray();
            this.originalBounds = {
                min_lon: bbox[0][0],
                min_lat: bbox[0][1],
                max_lon: bbox[1][0],
                max_lat: bbox[1][1]
            };
            
            this.map.fitBounds(bounds, { padding: 50, duration: 1000 });
            
            // Show zoom out button
            const zoomOutBtn = document.getElementById('zoom-out-btn');
            if (zoomOutBtn) {
                zoomOutBtn.classList.remove('hidden');
            }
        }
    }

    renderLayers() {
        if (!this.overlay) return;

        let layers = [];

        if (this.currentLayerType === 'polygon') {
            layers = this.createPolygonLayers();
        } else if (this.currentLayerType === 'line') {
            layers = this.createLineLayers();
        } else {
            // Point layers based on render mode
            switch (this.currentRenderMode) {
                case 'heatmap':
                    layers = this.createHeatmapLayers();
                    break;
                case 'hexagon':
                    layers = this.createHexagonLayers();
                    break;
                default:
                    layers = this.createScatterLayers();
            }
        }

        this.overlay.setProps({ layers });
    }

    // === POINT LAYERS ===

    createScatterLayers() {
        const radius = parseInt(document.getElementById('scatter-radius')?.value || 8);
        const opacity = parseInt(document.getElementById('scatter-opacity')?.value || 80) / 100;

        // Update display values
        const radiusVal = document.getElementById('scatter-radius-val');
        const opacityVal = document.getElementById('scatter-opacity-val');
        if (radiusVal) radiusVal.textContent = radius;
        if (opacityVal) opacityVal.textContent = Math.round(opacity * 100);

        return [
            new deck.ScatterplotLayer({
                id: 'scatter-layer',
                data: this.currentData,
                getPosition: d => d.position,
                getRadius: radius * 100,
                getFillColor: d => [...this.getPointColor(d.properties).slice(0, 3), Math.round(opacity * 255)],
                pickable: true,
                onHover: info => this.showTooltip(info),
                onClick: info => this.handlePointClick(info),
                radiusMinPixels: radius,
                radiusMaxPixels: radius * 3,
                visible: this.pointsVisible !== false // Default to true, respect toggle
            })
        ];
    }

    createHeatmapLayers() {
        const radius = parseInt(document.getElementById('heat-radius')?.value || 30);
        const intensity = parseInt(document.getElementById('heat-intensity')?.value || 1);

        const radiusVal = document.getElementById('heat-radius-val');
        const intensityVal = document.getElementById('heat-intensity-val');
        if (radiusVal) radiusVal.textContent = radius;
        if (intensityVal) intensityVal.textContent = intensity;

        return [
            new deck.HeatmapLayer({
                id: 'heatmap-layer',
                data: this.currentData,
                getPosition: d => d.position,
                getWeight: 1,
                radiusPixels: radius,
                intensity: intensity,
                threshold: 0.05,
                visible: this.pointsVisible !== false,
                colorRange: [
                    [65, 182, 196],
                    [127, 205, 187],
                    [199, 233, 180],
                    [237, 248, 177],
                    [255, 255, 204],
                    [255, 237, 160],
                    [254, 217, 118],
                    [254, 178, 76],
                    [253, 141, 60],
                    [252, 78, 42],
                    [227, 26, 28],
                    [189, 0, 38]
                ]
            })
        ];
    }

    createHexagonLayers() {
        const radius = parseInt(document.getElementById('hex-radius')?.value || 5000);
        const elevation = parseInt(document.getElementById('hex-elevation')?.value || 100);

        const radiusVal = document.getElementById('hex-radius-val');
        const elevationVal = document.getElementById('hex-elevation-val');
        if (radiusVal) radiusVal.textContent = Math.round(radius / 1000);
        if (elevationVal) elevationVal.textContent = elevation;

        return [
            new deck.HexagonLayer({
                id: 'hexagon-layer',
                data: this.currentData,
                getPosition: d => d.position,
                radius: radius,
                elevationScale: elevation,
                elevationRange: [0, 3000],
                extruded: true,
                pickable: true,
                visible: this.pointsVisible !== false,
                colorRange: [
                    [65, 182, 196],
                    [127, 205, 187],
                    [199, 233, 180],
                    [237, 248, 177],
                    [255, 255, 204],
                    [254, 217, 118],
                    [254, 178, 76],
                    [253, 141, 60],
                    [227, 26, 28]
                ]
            })
        ];
    }

    // === POLYGON LAYERS ===

    createPolygonLayers() {
        return [
            new deck.GeoJsonLayer({
                id: 'polygon-layer',
                data: this.currentGeojson,
                filled: true,
                stroked: true,
                extruded: false,
                getFillColor: f => this.getPolygonColor(f.properties),
                getLineColor: [255, 255, 255, 120],
                getLineWidth: 1,
                lineWidthMinPixels: 1,
                pickable: true,
                onHover: info => this.showPolygonTooltip(info),
                onClick: info => this.handlePolygonClick(info),
                autoHighlight: true,
                highlightColor: [255, 255, 0, 100]
            })
        ];
    }

    // === LINE LAYERS ===

    createLineLayers() {
        const paths = [];
        
        this.currentGeojson.features.forEach(f => {
            const geom = f.geometry;
            const props = f.properties;
            
            if (geom.type === 'LineString') {
                paths.push({ path: geom.coordinates, properties: props });
            } else if (geom.type === 'MultiLineString') {
                geom.coordinates.forEach(line => {
                    paths.push({ path: line, properties: props });
                });
            }
        });

        return [
            new deck.PathLayer({
                id: 'line-layer',
                data: paths,
                getPath: d => d.path,
                getColor: d => this.getLineColor(d.properties),
                getWidth: 3,
                widthMinPixels: 2,
                widthMaxPixels: 10,
                pickable: true,
                onHover: info => this.showLineTooltip(info),
                onClick: info => this.handleLineClick(info),
                autoHighlight: true,
                highlightColor: [255, 255, 0, 200]
            })
        ];
    }

    // === COLORS ===

    getPointColor(props) {
        // First check if color is provided (from analysis results like clustering)
        if (props?.color) {
            return this.hexToRgba(props.color, 220);
        }
        
        // Fallback to commodity-based colors
        const commodity = (props?.major_comm || '').toLowerCase();
        if (commodity.includes('gold')) return [255, 215, 0, 220];
        if (commodity.includes('copper')) return [184, 115, 51, 220];
        if (commodity.includes('silver')) return [192, 192, 192, 220];
        if (commodity.includes('iron')) return [139, 69, 19, 220];
        if (commodity.includes('zinc')) return [100, 149, 237, 220];
        return [231, 76, 60, 220];
    }

    // Convert hex color to RGBA array
    hexToRgba(hex, alpha = 255) {
        // Remove # if present
        hex = hex.replace('#', '');
        
        // Parse hex values
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        
        return [r, g, b, alpha];
    }

    getPolygonColor(props) {
        const litho = (props?.litho_fmly || props?.main_litho || '').toLowerCase();
        if (litho.includes('volcanic')) return [192, 57, 43, 180];
        if (litho.includes('igneous')) return [231, 76, 60, 180];
        if (litho.includes('plutonic') || litho.includes('granite')) return [219, 112, 147, 180];
        if (litho.includes('sedimentary')) return [210, 180, 140, 180];
        if (litho.includes('metamorphic')) return [128, 0, 128, 180];
        if (litho.includes('polylithologic')) return [46, 139, 87, 180];
        return [100, 149, 237, 180];
    }

    getLineColor(props) {
        const type = (props?.newtype || '').toLowerCase();
        if (type.includes('fault')) return [255, 0, 0, 255];
        if (type.includes('contact')) return [0, 255, 0, 255];
        if (type.includes('thrust')) return [255, 165, 0, 255];
        return [128, 128, 128, 255];
    }

    // === TOOLTIPS ===

    showTooltip(info) {
        const tooltip = document.getElementById('tooltip-2d');
        if (!info.object) {
            if (tooltip) tooltip.style.display = 'none';
            return;
        }

        const d = info.object;
        const p = d.properties || {};
        
        let html = `<div class="tooltip-header">${p.eng_name || p.sampleid || p.borehole_i || 'Site'}</div>`;
        if (p.major_comm) html += `<div class="tooltip-row"><span>Commodity:</span> ${p.major_comm}</div>`;
        if (p.region) html += `<div class="tooltip-row"><span>Region:</span> ${p.region}</div>`;
        if (p.geology) html += `<div class="tooltip-row"><span>Geology:</span> ${p.geology}</div>`;
        html += `<div class="tooltip-coords">📍 ${d.latitude?.toFixed(5)}, ${d.longitude?.toFixed(5)}</div>`;

        this._showTooltipElement(html, info.x, info.y);
    }

    showPolygonTooltip(info) {
        const tooltip = document.getElementById('tooltip-2d');
        if (!info.object) {
            if (tooltip) tooltip.style.display = 'none';
            return;
        }

        const p = info.object.properties || {};
        let html = `<div class="tooltip-header">${p.unit_name || 'Geological Area'}</div>`;
        if (p.main_litho) html += `<div class="tooltip-row"><span>Lithology:</span> ${p.main_litho}</div>`;
        if (p.litho_fmly) html += `<div class="tooltip-row"><span>Family:</span> ${p.litho_fmly}</div>`;
        if (p.era) html += `<div class="tooltip-row"><span>Era:</span> ${p.era}</div>`;
        if (p.terrane) html += `<div class="tooltip-row"><span>Terrane:</span> ${p.terrane}</div>`;

        this._showTooltipElement(html, info.x, info.y);
    }

    showLineTooltip(info) {
        const tooltip = document.getElementById('tooltip-2d');
        if (!info.object) {
            if (tooltip) tooltip.style.display = 'none';
            return;
        }

        const p = info.object.properties || {};
        let html = `<div class="tooltip-header">${p.newtype || 'Feature'}</div>`;
        if (p.shape_leng) {
            html += `<div class="tooltip-row"><span>Length:</span> ${(parseFloat(p.shape_leng) / 1000).toFixed(1)} km</div>`;
        }

        this._showTooltipElement(html, info.x, info.y);
    }

    _showTooltipElement(html, x, y) {
        let tooltip = document.getElementById('tooltip-2d');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'tooltip-2d';
            tooltip.className = 'map-tooltip';
            document.getElementById('view-map2d')?.appendChild(tooltip);
        }
        
        tooltip.innerHTML = html;
        tooltip.style.display = 'block';
        tooltip.style.left = (x + 10) + 'px';
        tooltip.style.top = (y + 10) + 'px';
    }

    // === CLICK HANDLERS ===

    handlePointClick(info) {
        if (!info.object) return;
        const d = info.object;
        this.map.flyTo({ center: [d.longitude, d.latitude], zoom: 12, duration: 1000 });
        document.getElementById('zoom-out-btn')?.classList.remove('hidden');
    }

    handlePolygonClick(info) {
        if (!info.object || !info.coordinate) return;
        this.map.flyTo({ center: info.coordinate, zoom: 10, duration: 1000 });
        document.getElementById('zoom-out-btn')?.classList.remove('hidden');
    }

    handleLineClick(info) {
        if (!info.object || !info.coordinate) return;
        this.map.flyTo({ center: info.coordinate, zoom: 11, duration: 1000 });
        document.getElementById('zoom-out-btn')?.classList.remove('hidden');
    }

    zoomOutToAll() {
        if (this.originalBounds) {
            this.fitBounds(this.originalBounds);
        } else if (this.currentGeojson && this.currentGeojson.features) {
            // Fallback: Calculate bounds from current features
            this.fitToFeatures(this.currentGeojson.features);
        } else {
            // Final fallback: Zoom to default view (Saudi Arabia)
            if (this.map) {
                this.map.fitBounds([
                    [36, 16],  // Southwest
                    [55, 32]   // Northeast
                ], { padding: 50, duration: 1000 });
            }
        }
        // Hide button after zooming
        document.getElementById('zoom-out-btn')?.classList.add('hidden');
    }

    fitBounds(bounds) {
        if (!bounds || !this.map) return;
        
        // Save bounds for zoom out
        this.originalBounds = bounds;
        
        this.map.fitBounds([
            [bounds.min_lon, bounds.min_lat],
            [bounds.max_lon, bounds.max_lat]
        ], { padding: 50, duration: 1000 });
        
        // Show zoom out button
        const zoomOutBtn = document.getElementById('zoom-out-btn');
        if (zoomOutBtn) {
            zoomOutBtn.classList.remove('hidden');
        }
    }
    
    // === SPATIAL JOIN CONTROLS ===
    
    setupSpatialJoinControls() {
        const controls = document.getElementById('spatial-join-controls');
        if (controls) {
            controls.classList.remove('hidden');
        }
        
        // Setup toggle handlers
        const togglePolygons = document.getElementById('toggle-polygons');
        const togglePoints = document.getElementById('toggle-points');
        
        if (togglePolygons) {
            togglePolygons.addEventListener('change', (e) => {
                this.togglePolygonVisibility(e.target.checked);
            });
        }
        
        if (togglePoints) {
            togglePoints.addEventListener('change', (e) => {
                this.togglePointVisibility(e.target.checked);
            });
        }
    }
    
    togglePolygonVisibility(visible) {
        if (!this.map) return;
        
        try {
            if (this.map.getLayer('polygon-overlay-fill')) {
                this.map.setLayoutProperty('polygon-overlay-fill', 'visibility', visible ? 'visible' : 'none');
            }
            if (this.map.getLayer('polygon-overlay-outline')) {
                this.map.setLayoutProperty('polygon-overlay-outline', 'visibility', visible ? 'visible' : 'none');
            }
            if (this.map.getLayer('polygon-overlay-labels')) {
                this.map.setLayoutProperty('polygon-overlay-labels', 'visibility', visible ? 'visible' : 'none');
            }
        } catch (e) {
            console.error('Error toggling polygon visibility:', e);
        }
    }
    
    togglePointVisibility(visible) {
        this.pointsVisible = visible;
        
        // Update Mapbox cluster layers if they exist (for analysis results)
        if (this.map) {
            try {
                // Find all cluster-related layers
                const style = this.map.getStyle();
                if (style && style.layers) {
                    style.layers.forEach(layer => {
                        if (layer.id && (layer.id.includes('cluster') || layer.id.includes('point'))) {
                            try {
                                this.map.setLayoutProperty(layer.id, 'visibility', visible ? 'visible' : 'none');
                            } catch (e) {
                                // Ignore if layer doesn't support visibility
                            }
                        }
                    });
                }
            } catch (e) {
                console.error('Error toggling point visibility:', e);
            }
        }
        
        // Re-render deck.gl layers with visibility flag
        if (this.overlay && this.currentLayerType === 'point') {
            this.renderLayers();
        }
    }
    
    updateFilteredPoints() {
        // Combine points from all selected polygons
        if (!this.originalPointData) {
            return;
        }
        
        if (this.selectedPolygons.size === 0) {
            // No polygons selected - show all points
            this.currentData = [...this.originalPointData];
            this.filteredPointData = null;
            console.log('No polygons selected - showing all points');
        } else {
            // Collect points from all selected polygons
            const allFilteredPoints = new Set(); // Use Set to avoid duplicates
            const pointMap = new Map(); // Map point coordinates to point data
            
            // Create a map of all points by their coordinates (for deduplication)
            this.originalPointData.forEach(point => {
                const key = `${point.longitude},${point.latitude}`;
                pointMap.set(key, point);
            });
            
            // Check each point against all selected polygons
            for (const point of this.originalPointData) {
                for (const [unitName, polygonData] of this.selectedPolygons.entries()) {
                    if (this.isPointInPolygon(
                        [point.longitude, point.latitude],
                        polygonData.geometry
                    )) {
                        const key = `${point.longitude},${point.latitude}`;
                        allFilteredPoints.add(key);
                        break; // Point found in at least one polygon, no need to check others
                    }
                }
            }
            
            // Convert Set back to array
            this.filteredPointData = Array.from(allFilteredPoints).map(key => pointMap.get(key));
            this.currentData = [...this.filteredPointData];
            
            console.log(`Filtered: ${this.filteredPointData.length} points from ${this.selectedPolygons.size} selected polygon(s)`);
        }
        
        // Update polygon colors to show selection state
        this.updatePolygonColors();
        
        // Update visualization
        this.updateFilteredVisualization();
    }
    
    updatePolygonColors() {
        if (!this.map || !this.map.getLayer('polygon-overlay-fill')) {
            return;
        }
        
        try {
            const selectedGids = Array.from(this.selectedPolygons.keys()).map(gid => String(gid));
            
            if (selectedGids.length === 0) {
                // No polygons selected - reset to default colors
                this.map.setPaintProperty('polygon-overlay-fill', 'fill-color', '#3b82f6');
                this.map.setPaintProperty('polygon-overlay-fill', 'fill-opacity', 0.15);
                if (this.map.getLayer('polygon-overlay-outline')) {
                    this.map.setPaintProperty('polygon-overlay-outline', 'line-color', '#3b82f6');
                }
                return;
            }
            
            // Update fill color based on selection (using gid)
            // Use a data-driven expression to check if gid is in selected list
            this.map.setPaintProperty('polygon-overlay-fill', 'fill-color', [
                'case',
                ['in', ['to-string', ['get', 'gid']], ['literal', selectedGids]],
                '#22c55e', // Green for selected
                '#3b82f6'  // Blue for unselected
            ]);
            
            // Update fill opacity
            this.map.setPaintProperty('polygon-overlay-fill', 'fill-opacity', [
                'case',
                ['in', ['to-string', ['get', 'gid']], ['literal', selectedGids]],
                0.25, // More opaque when selected
                0.15  // Less opaque when not selected
            ]);
            
            // Update outline color
            if (this.map.getLayer('polygon-overlay-outline')) {
                this.map.setPaintProperty('polygon-overlay-outline', 'line-color', [
                    'case',
                    ['in', ['to-string', ['get', 'gid']], ['literal', selectedGids]],
                    '#22c55e', // Green for selected
                    '#3b82f6'  // Blue for unselected
                ]);
            }
        } catch (e) {
            console.error('Error updating polygon colors:', e);
        }
    }
    
    updateFilteredVisualization() {
        // Ensure points are visible
        if (this.selectedPolygons.size > 0) {
            this.pointsVisible = true;
        }
        
        // Update currentGeojson to match filtered data
        if (this.currentGeojson) {
            this.currentGeojson.features = this.currentData.map(point => ({
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [point.longitude, point.latitude]
                },
                properties: point.properties
            }));
        }
        
        // Re-render point layers
        if (this.currentLayerType === 'point') {
            this.renderLayers();
        }
        
        // Update feature count
        const countEl = document.getElementById('feature-count');
        if (countEl) {
            const count = this.currentData.length;
            countEl.textContent = `${count} point${count !== 1 ? 's' : ''}`;
        }
        
        // Update data table
        this.updateDataTable(this.currentData);
    }
    
    updateDataTable(data) {
        if (!data || data.length === 0) {
            if (typeof chat !== 'undefined' && chat.clearTable) {
                chat.clearTable();
            }
            return;
        }
        
        // Convert point data format to table format
        // Point data has: {longitude, latitude, properties: {...}}
        // Table expects: {longitude, latitude, ...all properties}
        const tableData = data.map(point => {
            const row = {
                longitude: point.longitude,
                latitude: point.latitude,
                ...(point.properties || {})
            };
            return row;
        });
        
        // Use chat's updateTable if available
        if (typeof chat !== 'undefined' && chat.updateTable) {
            chat.updateTable(tableData);
        } else {
            // Fallback: update table directly
            const header = document.getElementById('table-header');
            const body = document.getElementById('table-body');
            
            if (!body) return;
            
            // Get columns (exclude geojson_geom)
            const cols = Object.keys(tableData[0]).filter(c => c !== 'geojson_geom' && c !== 'geom');
            
            // Build header
            if (header) {
                header.innerHTML = '<tr>' + cols.map(c => 
                    `<th>${c.charAt(0).toUpperCase() + c.slice(1).replace(/_/g, ' ')}</th>`
                ).join('') + '</tr>';
            }
            
            // Build body (limit to 500 rows for performance)
            body.innerHTML = tableData.slice(0, 500).map((row, idx) => 
                `<tr data-idx="${idx}">` + 
                cols.map(c => `<td>${row[c] ?? ''}</td>`).join('') + 
                '</tr>'
            ).join('');
        }
    }
    
    filterPointsByPolygon(polygonGeom, unitName = null) {
        if (this.isFiltering) {
            console.log('Filter already in progress, skipping...');
            return;
        }
        
        this.isFiltering = true;
        
        if (!this.originalPointData) {
            console.warn('No original point data available for filtering');
            this.isFiltering = false;
            return;
        }
        
        if (!polygonGeom && !unitName) {
            // Show all points - clear filter
            this.currentData = [...this.originalPointData];
            this.filteredPointData = null;
            console.log('Showing all points (filter cleared)');
            this.isFiltering = false;
        } else {
            // Filter points using geometry-based point-in-polygon (most accurate)
            const filtered = [];
            
            if (!polygonGeom) {
                console.warn('No polygon geometry provided for filtering');
                return;
            }
            
            for (const point of this.originalPointData) {
                // Always use geometry-based point-in-polygon test (most accurate)
                const isInside = this.isPointInPolygon(
                    [point.longitude, point.latitude],
                    polygonGeom
                );
                
                if (isInside) {
                    filtered.push(point);
                }
            }
            
            this.filteredPointData = filtered;
            this.currentData = [...this.filteredPointData];
            console.log(`Filtered: ${this.filteredPointData.length} points inside polygon "${unitName || 'unknown'}" (out of ${this.originalPointData.length} total)`);
            
            // Debug: log a few point coordinates and polygon bounds
            if (this.filteredPointData.length > 0 && polygonGeom.coordinates && polygonGeom.coordinates[0]) {
                const polyCoords = polygonGeom.coordinates[0];
                console.log('Polygon has', polyCoords.length, 'vertices');
                console.log('Sample filtered point:', this.filteredPointData[0].longitude, this.filteredPointData[0].latitude);
            }
        }
        
        // Ensure points are visible when filtering
        if (polygonGeom) {
            this.pointsVisible = true;
        }
        
        // Update currentGeojson to match filtered data
        if (this.currentGeojson) {
            this.currentGeojson.features = this.currentData.map(point => ({
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [point.longitude, point.latitude]
                },
                properties: point.properties
            }));
        }
        
        // Re-render point layers with updated data and visibility
        if (this.currentLayerType === 'point') {
            this.renderLayers();
        }
        
        // Update feature count
        const countEl = document.getElementById('feature-count');
        if (countEl) {
            const count = this.currentData.length;
            countEl.textContent = `${count} point${count !== 1 ? 's' : ''}`;
        }
        
        // Reset filtering flag
        setTimeout(() => {
            this.isFiltering = false;
        }, 100);
    }
    
    showPolygonPopup(lngLat, props, isSelected = true) {
        // Remove existing popup if any
        const existingPopup = document.getElementById('custom-polygon-popup');
        if (existingPopup) {
            existingPopup.remove();
        }
        
        // Remove existing click handler
        if (this.popupCloseHandler) {
            this.map.off('click', this.popupCloseHandler);
        }
        
        // Create custom popup element
        const selectedCount = this.selectedPolygons.size;
        const popup = document.createElement('div');
        popup.id = 'custom-polygon-popup';
        popup.className = 'custom-map-popup';
        popup.innerHTML = `
            <div class="popup-header">
                <h4>${props.unit_name || 'Unknown Area'}</h4>
                <button class="popup-close" aria-label="Close popup">×</button>
            </div>
            <div class="popup-content">
                <div><strong>Lithology:</strong> ${props.litho_fmly || '-'}</div>
                <div><strong>Main Rock:</strong> ${props.main_litho || '-'}</div>
                <div class="popup-points">
                    <strong style="color: #3b82f6;">Points inside: ${props.point_count || 0}</strong>
                </div>
                <div class="popup-status" style="margin-top: 8px; padding: 6px; border-radius: 4px; background: ${isSelected ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'};">
                    <strong style="color: ${isSelected ? '#22c55e' : '#ef4444'};">
                        ${isSelected ? '✓ Selected' : 'Not selected'}
                    </strong>
                </div>
                <div class="popup-hint">
                    ${isSelected 
                        ? 'Click again to deselect' 
                        : 'Click to select and show points'}
                </div>
                ${selectedCount > 1 ? `<div class="popup-hint" style="margin-top: 4px; font-size: 11px;">
                    ${selectedCount} polygons selected
                </div>` : ''}
            </div>
        `;
        
        // Close button handler
        const closeBtn = popup.querySelector('.popup-close');
        closeBtn.addEventListener('click', () => {
            popup.remove();
            if (this.popupCloseHandler) {
                this.map.off('click', this.popupCloseHandler);
                this.popupCloseHandler = null;
            }
        });
        
        // Position popup - handle both LngLat object and array
        let lng, lat;
        if (lngLat && typeof lngLat === 'object') {
            if (lngLat.lng !== undefined && lngLat.lat !== undefined) {
                // Mapbox LngLat object
                lng = lngLat.lng;
                lat = lngLat.lat;
            } else if (Array.isArray(lngLat)) {
                // Array [lng, lat]
                [lng, lat] = lngLat;
            } else {
                console.error('Invalid lngLat format:', lngLat);
                return;
            }
        } else {
            console.error('lngLat is not an object or array:', lngLat);
            return;
        }
        
        const point = this.map.project([lng, lat]);
        
        popup.style.position = 'absolute';
        popup.style.left = point.x + 'px';
        popup.style.top = point.y + 'px';
        popup.style.transform = 'translate(-50%, -100%)';
        popup.style.marginTop = '-10px';
        
        // Add to map container
        const mapContainer = this.map.getContainer();
        mapContainer.appendChild(popup);
        
        // Close popup when clicking map (but not on the popup itself or polygon layers)
        this.popupCloseHandler = (e) => {
            // Check if popup still exists
            if (!popup || !popup.parentNode) {
                this.map.off('click', this.popupCloseHandler);
                this.popupCloseHandler = null;
                return;
            }
            
            // Don't close if clicking on polygon layers (let polygon click handler process it)
            if (e.originalEvent && e.point) {
                try {
                    const features = this.map.queryRenderedFeatures(e.point, {
                        layers: ['polygon-overlay-fill', 'polygon-overlay-outline', 'polygon-overlay-labels']
                    });
                    if (features && features.length > 0) {
                        // Clicked on a polygon - don't close popup, let polygon handler process it
                        return;
                    }
                } catch (err) {
                    // Ignore query errors
                }
            }
            
            // Check if target is a valid Node
            if (!e.target || !(e.target instanceof Node)) {
                return;
            }
            
            // Close if clicking outside the popup (but not on polygons)
            try {
                if (!popup.contains(e.target) && e.target.closest('.custom-map-popup') !== popup) {
                    popup.remove();
                    this.map.off('click', this.popupCloseHandler);
                    this.popupCloseHandler = null;
                }
            } catch (err) {
                // If contains() fails, just remove the popup and handler
                console.warn('Error checking popup contains:', err);
                if (popup && popup.parentNode) {
                    popup.remove();
                }
                this.map.off('click', this.popupCloseHandler);
                this.popupCloseHandler = null;
            }
        };
        
        // Close after a longer delay to ensure polygon click handler processes first
        setTimeout(() => {
            this.map.on('click', this.popupCloseHandler);
        }, 300);
    }
    
    isPointInPolygon(point, polygon) {
        if (!point || !polygon) {
            return false;
        }
        
        // Handle different polygon formats
        let coordinates;
        
        if (polygon.type === 'Polygon') {
            coordinates = polygon.coordinates[0]; // First ring (exterior ring)
        } else if (polygon.type === 'MultiPolygon') {
            // Check if point is in any of the polygons
            for (const poly of polygon.coordinates) {
                if (this.isPointInPolygon(point, { type: 'Polygon', coordinates: poly })) {
                    return true;
                }
            }
            return false;
        } else if (polygon.coordinates) {
            // Fallback: assume it's coordinates array
            if (Array.isArray(polygon.coordinates[0])) {
                if (Array.isArray(polygon.coordinates[0][0])) {
                    // Nested array: [[[lon, lat], ...]]
                    coordinates = polygon.coordinates[0];
                } else {
                    // Flat array: [[lon, lat], ...]
                    coordinates = polygon.coordinates;
                }
            } else {
                return false;
            }
        } else {
            return false;
        }
        
        if (!coordinates || coordinates.length < 3) {
            return false;
        }
        
        // Remove duplicate last point if polygon is closed (first == last)
        if (coordinates.length > 3) {
            const first = coordinates[0];
            const last = coordinates[coordinates.length - 1];
            if (first[0] === last[0] && first[1] === last[1]) {
                coordinates = coordinates.slice(0, -1);
            }
        }
        
        // Point-in-polygon using ray casting algorithm
        const [x, y] = point; // [longitude, latitude]
        let inside = false;
        
        for (let i = 0, j = coordinates.length - 1; i < coordinates.length; j = i++) {
            const coordI = coordinates[i];
            const coordJ = coordinates[j];
            
            if (!Array.isArray(coordI) || coordI.length < 2) continue;
            if (!Array.isArray(coordJ) || coordJ.length < 2) continue;
            
            const [xi, yi] = coordI; // [lon, lat]
            const [xj, yj] = coordJ; // [lon, lat]
            
            // Handle edge case: point exactly on horizontal edge
            if (yi === y && yj === y) {
                // Point is on horizontal edge, check if it's between x coordinates
                if ((x >= Math.min(xi, xj) && x <= Math.max(xi, xj))) {
                    return true; // Point is on the edge
                }
                continue;
            }
            
            // Check if ray crosses edge
            const intersect = ((yi > y) !== (yj > y)) && 
                             (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if (intersect) {
                inside = !inside;
            }
        }
        
        return inside;
    }
}

let map2d = null;
