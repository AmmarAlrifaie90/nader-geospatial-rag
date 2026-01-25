/**
 * 3D Map with Deck.gl + Mapbox
 * Points: ScatterplotLayer, ColumnLayer
 * Polygons: GeoJsonLayer (extruded)
 * Lines: PathLayer (elevated)
 */
class Map3D {
    constructor(containerId = 'map3d') {
        this.containerId = containerId;
        this.map = null;
        this.overlay = null;
        this.currentData = [];
        this.currentGeojson = null;
        this.currentLayerType = 'point';
        this.originalBounds = null;
        this.extrusionScale = 1000;
    }

    async initialize(token) {
        if (!token) {
            console.error('No Mapbox token provided for 3D map');
            return;
        }

        mapboxgl.accessToken = token;

        this.map = new mapboxgl.Map({
            container: this.containerId,
            style: 'mapbox://styles/mapbox/satellite-streets-v12',
            center: [44, 24],
            zoom: 6,
            pitch: 60,
            bearing: -20,
            antialias: true
        });

        this.map.addControl(new mapboxgl.NavigationControl());

        await new Promise(resolve => this.map.on('load', resolve));

        // Add terrain
        this.map.addSource('mapbox-dem', {
            type: 'raster-dem',
            url: 'mapbox://mapbox.mapbox-terrain-dem-v1',
            tileSize: 512,
            maxzoom: 14
        });
        this.map.setTerrain({ source: 'mapbox-dem', exaggeration: 1.5 });

        // Add sky
        this.map.addLayer({
            id: 'sky',
            type: 'sky',
            paint: {
                'sky-type': 'atmosphere',
                'sky-atmosphere-sun': [0.0, 90.0],
                'sky-atmosphere-sun-intensity': 15
            }
        });

        this.overlay = new deck.MapboxOverlay({ layers: [] });
        this.map.addControl(this.overlay);

        // Resize handling
        this.map.resize();

        console.log('3D Map initialized');
    }

    updateVisualization(visualization) {
        if (!visualization || !visualization.geojson) return;
        if (!this.overlay) {
            console.warn('3D Map not ready');
            return;
        }

        this.currentGeojson = visualization.geojson;
        this.currentLayerType = visualization.layer_type || 'point';
        this.originalBounds = visualization.bounds;

        // Convert for points
        if (this.currentLayerType === 'point') {
            this.currentData = visualization.geojson.features.map(f => ({
                position: f.geometry.coordinates,
                longitude: f.geometry.coordinates[0],
                latitude: f.geometry.coordinates[1],
                properties: f.properties
            }));
        }

        // Update UI - feature count is now in map-info (shared with 2D)
        const countEl = document.getElementById('feature-count');
        if (countEl) {
            const count = visualization.geojson.features.length;
            countEl.textContent = `${count} ${this.currentLayerType}${count !== 1 ? 's' : ''}`;
        }

        this.renderLayers();

        if (visualization.bounds) {
            this.fitBounds(visualization.bounds);
        } else if (this.currentGeojson && this.currentGeojson.features) {
            // Calculate bounds from features if not provided
            const bounds = this._calculateBounds(this.currentGeojson.features);
            if (bounds) {
                this.fitBounds(bounds);
            }
        }

        // Ensure map is properly sized
        setTimeout(() => this.map?.resize(), 100);
    }

    renderLayers() {
        if (!this.overlay) return;

        let layers = [];

        if (this.currentLayerType === 'polygon') {
            layers = this.createPolygonLayers();
        } else if (this.currentLayerType === 'line') {
            layers = this.createLineLayers();
        } else {
            layers = this.createPointLayers();
        }

        this.overlay.setProps({ layers });
    }

    // === POINT LAYERS ===

    createPointLayers() {
        // Flat points only - no 3D columns
        return [
            new deck.ScatterplotLayer({
                id: 'points-3d',
                data: this.currentData,
                getPosition: d => d.position,
                getRadius: 800,
                getFillColor: d => this.getPointColor(d.properties),
                pickable: true,
                onHover: info => this.showTooltip(info),
                onClick: info => this.handlePointClick(info),
                radiusMinPixels: 4,
                radiusMaxPixels: 20,
                stroked: true,
                getLineColor: [255, 255, 255, 200],
                lineWidthMinPixels: 1
            })
        ];
    }

    // === POLYGON LAYERS ===

    createPolygonLayers() {
        return [
            new deck.GeoJsonLayer({
                id: 'polygon-3d',
                data: this.currentGeojson,
                filled: true,
                stroked: true,
                extruded: true,
                wireframe: true,
                getElevation: f => this.getPolygonElevation(f.properties) * this.extrusionScale,
                getFillColor: f => this.getPolygonColor(f.properties),
                getLineColor: [255, 255, 255, 150],
                getLineWidth: 2,
                lineWidthMinPixels: 1,
                pickable: true,
                onHover: info => this.showPolygonTooltip(info),
                onClick: info => this.handlePolygonClick(info),
                autoHighlight: true,
                highlightColor: [255, 255, 0, 100],
                material: {
                    ambient: 0.5,
                    diffuse: 0.6,
                    shininess: 32,
                    specularColor: [60, 64, 70]
                }
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
                const path3d = geom.coordinates.map(c => [c[0], c[1], 500]);
                paths.push({ path: path3d, properties: props });
            } else if (geom.type === 'MultiLineString') {
                geom.coordinates.forEach(line => {
                    const path3d = line.map(c => [c[0], c[1], 500]);
                    paths.push({ path: path3d, properties: props });
                });
            }
        });

        return [
            new deck.PathLayer({
                id: 'line-3d',
                data: paths,
                getPath: d => d.path,
                getColor: d => this.getLineColor(d.properties),
                getWidth: 80,
                widthMinPixels: 3,
                widthMaxPixels: 15,
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
        const commodity = (props?.major_comm || '').toLowerCase();
        if (commodity.includes('gold')) return [255, 215, 0, 255];
        if (commodity.includes('copper')) return [184, 115, 51, 255];
        if (commodity.includes('silver')) return [192, 192, 192, 255];
        if (commodity.includes('iron')) return [139, 69, 19, 255];
        return [231, 76, 60, 255];
    }

    getPolygonColor(props) {
        const litho = (props?.litho_fmly || props?.main_litho || '').toLowerCase();
        if (litho.includes('volcanic')) return [192, 57, 43, 200];
        if (litho.includes('igneous')) return [231, 76, 60, 200];
        if (litho.includes('plutonic') || litho.includes('granite')) return [219, 112, 147, 200];
        if (litho.includes('sedimentary')) return [210, 180, 140, 200];
        if (litho.includes('metamorphic')) return [128, 0, 128, 200];
        return [100, 149, 237, 200];
    }

    getPolygonElevation(props) {
        const age = parseFloat(props?.age_ma) || 0;
        if (age > 1000) return 3;
        if (age > 500) return 2;
        if (age > 100) return 1;
        return 0.5;
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
        const tooltip = document.getElementById('tooltip-3d');
        if (!info.object) {
            if (tooltip) tooltip.style.display = 'none';
            return;
        }

        const d = info.object;
        const p = d.properties || {};
        
        let html = `<div class="tooltip-header">${p.eng_name || 'Site'}</div>`;
        if (p.major_comm) html += `<div class="tooltip-row"><span>Commodity:</span> ${p.major_comm}</div>`;
        if (p.region) html += `<div class="tooltip-row"><span>Region:</span> ${p.region}</div>`;
        html += `<div class="tooltip-coords">📍 ${d.latitude?.toFixed(4)}, ${d.longitude?.toFixed(4)}</div>`;

        this._showTooltipElement(html, info.x, info.y);
    }

    showPolygonTooltip(info) {
        const tooltip = document.getElementById('tooltip-3d');
        if (!info.object) {
            if (tooltip) tooltip.style.display = 'none';
            return;
        }

        const p = info.object.properties || {};
        let html = `<div class="tooltip-header">${p.unit_name || 'Area'}</div>`;
        if (p.main_litho) html += `<div class="tooltip-row"><span>Lithology:</span> ${p.main_litho}</div>`;
        if (p.era) html += `<div class="tooltip-row"><span>Era:</span> ${p.era}</div>`;

        this._showTooltipElement(html, info.x, info.y);
    }

    showLineTooltip(info) {
        const tooltip = document.getElementById('tooltip-3d');
        if (!info.object) {
            if (tooltip) tooltip.style.display = 'none';
            return;
        }

        const p = info.object.properties || {};
        let html = `<div class="tooltip-header">${p.newtype || 'Feature'}</div>`;

        this._showTooltipElement(html, info.x, info.y);
    }

    _showTooltipElement(html, x, y) {
        let tooltip = document.getElementById('tooltip-3d');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'tooltip-3d';
            tooltip.className = 'map-tooltip';
            document.getElementById('view-map3d')?.appendChild(tooltip);
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
        this.map.flyTo({ center: [d.longitude, d.latitude], zoom: 14, pitch: 70, duration: 2000 });
        document.getElementById('zoom-out-btn')?.classList.remove('hidden');
    }

    handlePolygonClick(info) {
        if (!info.coordinate) return;
        this.map.flyTo({ center: info.coordinate, zoom: 12, pitch: 60, duration: 2000 });
        document.getElementById('zoom-out-btn')?.classList.remove('hidden');
    }

    handleLineClick(info) {
        if (!info.coordinate) return;
        this.map.flyTo({ center: info.coordinate, zoom: 13, pitch: 60, duration: 2000 });
        document.getElementById('zoom-out-btn')?.classList.remove('hidden');
    }

    zoomOutToAll() {
        if (this.originalBounds) {
            this.fitBounds(this.originalBounds);
        } else if (this.currentGeojson && this.currentGeojson.features) {
            // Fallback: Calculate bounds from current features
            const bounds = this._calculateBounds(this.currentGeojson.features);
            if (bounds) {
                this.fitBounds(bounds);
            }
        } else {
            // Final fallback: Zoom to default view (Saudi Arabia)
            if (this.map) {
                this.map.flyTo({
                    center: [44, 24],
                    zoom: 6,
                    pitch: 60,
                    bearing: -20,
                    duration: 1500
                });
            }
        }
        // Hide button after zooming
        document.getElementById('zoom-out-btn')?.classList.add('hidden');
    }

    _calculateBounds(features) {
        if (!features || features.length === 0) return null;
        
        let minLon = Infinity, minLat = Infinity;
        let maxLon = -Infinity, maxLat = -Infinity;
        
        features.forEach(f => {
            if (f.geometry) {
                if (f.geometry.type === 'Point' && f.geometry.coordinates) {
                    const [lon, lat] = f.geometry.coordinates;
                    minLon = Math.min(minLon, lon);
                    minLat = Math.min(minLat, lat);
                    maxLon = Math.max(maxLon, lon);
                    maxLat = Math.max(maxLat, lat);
                } else if (f.geometry.type === 'Polygon' && f.geometry.coordinates) {
                    f.geometry.coordinates[0].forEach(([lon, lat]) => {
                        minLon = Math.min(minLon, lon);
                        minLat = Math.min(minLat, lat);
                        maxLon = Math.max(maxLon, lon);
                        maxLat = Math.max(maxLat, lat);
                    });
                }
            }
        });
        
        if (minLon === Infinity) return null;
        
        return {
            min_lon: minLon,
            min_lat: minLat,
            max_lon: maxLon,
            max_lat: maxLat
        };
    }

    fitBounds(bounds) {
        if (!bounds || !this.map) return;
        
        // Save bounds for zoom out
        this.originalBounds = bounds;
        
        this.map.flyTo({
            center: [(bounds.min_lon + bounds.max_lon) / 2, (bounds.min_lat + bounds.max_lat) / 2],
            zoom: 7,
            pitch: 60,
            bearing: -20,
            duration: 1500
        });
        
        // Show zoom out button
        const zoomOutBtn = document.getElementById('zoom-out-btn');
        if (zoomOutBtn) {
            zoomOutBtn.classList.remove('hidden');
        }
    }

    updateExtrusion(value) {
        this.extrusionScale = value * 500;
        if (this.currentLayerType === 'polygon') this.renderLayers();
    }
}

let map3d = null;
