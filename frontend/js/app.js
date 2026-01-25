/**
 * Main Application - Geospatial RAG
 * Handles: Settings, Panel Resizing, View Switching, Health Checks
 */

window.appSettings = {
    apiEndpoint: 'http://localhost:8000',
    mapboxToken: '',
    maxResults: 500,
    clusterDistanceKm: 5  // Default cluster distance in km
};

// ============================================
// SETTINGS MANAGEMENT
// ============================================

function loadSettings() {
    const saved = localStorage.getItem('geospatial-rag-settings');
    if (saved) {
        try {
            Object.assign(window.appSettings, JSON.parse(saved));
        } catch (e) {
            console.error('Error loading settings:', e);
        }
    }
    
    if (api) api.setBaseUrl(window.appSettings.apiEndpoint);
    
    // Populate settings form
    const apiInput = document.getElementById('api-endpoint');
    const tokenInput = document.getElementById('mapbox-token');
    const maxInput = document.getElementById('max-results');
    
    if (apiInput) apiInput.value = window.appSettings.apiEndpoint;
    if (tokenInput) tokenInput.value = window.appSettings.mapboxToken;
    if (maxInput) maxInput.value = window.appSettings.maxResults;
    
    // Load cluster distance setting (ensure it's a number)
    const clusterDistanceInput = document.getElementById('cluster-distance');
    const clusterDistanceVal = document.getElementById('cluster-distance-val');
    if (clusterDistanceInput) {
        const clusterDist = parseFloat(window.appSettings.clusterDistanceKm) || 5;
        window.appSettings.clusterDistanceKm = clusterDist; // Ensure it's stored as number
        clusterDistanceInput.value = clusterDist;
        if (clusterDistanceVal) {
            clusterDistanceVal.textContent = clusterDist;
        }
    }
    
    // Show config banner if no token
    const banner = document.getElementById('config-banner');
    if (banner && !window.appSettings.mapboxToken) {
        banner.classList.remove('hidden');
    }
}

function saveSettings() {
    const apiInput = document.getElementById('api-endpoint');
    const tokenInput = document.getElementById('mapbox-token');
    const maxInput = document.getElementById('max-results');
    
    window.appSettings.apiEndpoint = apiInput?.value || window.appSettings.apiEndpoint;
    window.appSettings.mapboxToken = tokenInput?.value || window.appSettings.mapboxToken;
    window.appSettings.maxResults = parseInt(maxInput?.value) || 500;
    
    // Cluster distance is saved automatically when changed (no need to reload)

    localStorage.setItem('geospatial-rag-settings', JSON.stringify(window.appSettings));
    document.getElementById('settings-modal')?.classList.add('hidden');
    location.reload();
}

// ============================================
// PANEL RESIZING
// ============================================

function setupPanelResizing() {
    const panelLeft = document.getElementById('panel-layers');
    const panelRight = document.getElementById('panel-chat');
    const tableSection = document.getElementById('table-section');
    const mapSection = document.getElementById('map-section');
    
    const resizeLeft = document.getElementById('resize-left');
    const resizeRight = document.getElementById('resize-right');
    const resizeVertical = document.getElementById('resize-vertical');
    
    let isResizing = false;
    let currentHandle = null;
    
    function startResize(e, handle) {
        isResizing = true;
        currentHandle = handle;
        document.body.style.cursor = handle === 'vertical' ? 'row-resize' : 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    }
    
    function doResize(e) {
        if (!isResizing) return;
        
        if (currentHandle === 'left' && panelLeft) {
            const newWidth = Math.max(200, Math.min(400, e.clientX));
            panelLeft.style.width = newWidth + 'px';
        }
        
        if (currentHandle === 'right' && panelRight) {
            const containerWidth = window.innerWidth;
            const newWidth = Math.max(250, Math.min(500, containerWidth - e.clientX));
            panelRight.style.width = newWidth + 'px';
        }
        
        if (currentHandle === 'vertical' && tableSection && mapSection) {
            const container = mapSection.parentElement;
            const containerRect = container.getBoundingClientRect();
            const relativeY = e.clientY - containerRect.top;
            const containerHeight = containerRect.height;
            
            const mapHeight = Math.max(200, Math.min(containerHeight - 150, relativeY));
            const tableHeight = containerHeight - mapHeight - 6; // 6px for resize handle
            
            mapSection.style.flex = 'none';
            mapSection.style.height = mapHeight + 'px';
            tableSection.style.flex = 'none';
            tableSection.style.height = tableHeight + 'px';
        }
        
        // Trigger map resize
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 10);
    }
    
    function stopResize() {
        isResizing = false;
        currentHandle = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    }
    
    resizeLeft?.addEventListener('mousedown', (e) => startResize(e, 'left'));
    resizeRight?.addEventListener('mousedown', (e) => startResize(e, 'right'));
    resizeVertical?.addEventListener('mousedown', (e) => startResize(e, 'vertical'));
    
    document.addEventListener('mousemove', doResize);
    document.addEventListener('mouseup', stopResize);
    
    // Handle window resize
    window.addEventListener('resize', () => {
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 100);
    });
}

// ============================================
// CHAT COLLAPSE/EXPAND
// ============================================

function setupChatCollapse() {
    const panelChat = document.getElementById('panel-chat');
    const collapseBtn = document.getElementById('collapse-chat');
    const expandBtn = document.getElementById('expand-chat');
    const resizeRight = document.getElementById('resize-right');
    
    collapseBtn?.addEventListener('click', () => {
        panelChat?.classList.add('hidden');
        resizeRight?.classList.add('hidden');
        expandBtn?.classList.remove('hidden');
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 100);
    });
    
    expandBtn?.addEventListener('click', () => {
        panelChat?.classList.remove('hidden');
        resizeRight?.classList.remove('hidden');
        expandBtn?.classList.add('hidden');
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 100);
    });
}

// ============================================
// LAYERS COLLAPSE/EXPAND
// ============================================

function setupLayersCollapse() {
    const panelLayers = document.getElementById('panel-layers');
    const collapseBtn = document.getElementById('collapse-layers');
    const expandBtn = document.getElementById('expand-layers');
    const resizeLeft = document.getElementById('resize-left');
    
    collapseBtn?.addEventListener('click', () => {
        panelLayers?.classList.add('hidden');
        resizeLeft?.classList.add('hidden');
        expandBtn?.classList.remove('hidden');
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 100);
    });
    
    expandBtn?.addEventListener('click', () => {
        panelLayers?.classList.remove('hidden');
        resizeLeft?.classList.remove('hidden');
        expandBtn?.classList.add('hidden');
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 100);
    });
}

// ============================================
// TABLE COLLAPSE/EXPAND
// ============================================

function setupTableCollapse() {
    const tableSection = document.getElementById('table-section');
    const collapseBtn = document.getElementById('collapse-table');
    const expandBtn = document.getElementById('expand-table');
    const resizeVertical = document.getElementById('resize-vertical');
    const mapSection = document.getElementById('map-section');
    
    collapseBtn?.addEventListener('click', () => {
        tableSection?.classList.add('hidden');
        resizeVertical?.classList.add('hidden');
        expandBtn?.classList.remove('hidden');
        
        // Make map take full height
        if (mapSection) {
            mapSection.style.flex = '1';
            mapSection.style.height = 'auto';
        }
        
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 100);
    });
    
    expandBtn?.addEventListener('click', () => {
        tableSection?.classList.remove('hidden');
        resizeVertical?.classList.remove('hidden');
        expandBtn?.classList.add('hidden');
        
        // Reset map height
        if (mapSection) {
            mapSection.style.flex = '1';
        }
        
        setTimeout(() => {
            map2d?.map?.resize();
            map3d?.map?.resize();
        }, 100);
    });
}

// ============================================
// VIEW MODE SWITCHING (2D/3D)
// ============================================

function setupViewMode() {
    const viewModeSelect = document.getElementById('view-mode');
    const map2dContainer = document.getElementById('map2d');
    const map3dContainer = document.getElementById('map3d');
    
    viewModeSelect?.addEventListener('change', () => {
        const mode = viewModeSelect.value;
        
        if (mode === '3d') {
            map2dContainer?.classList.add('hidden');
            map3dContainer?.classList.remove('hidden');
            setTimeout(() => {
                map3d?.map?.resize();
                if (chat?.lastVisualization) {
                    map3d?.updateVisualization(chat.lastVisualization);
                }
            }, 100);
        } else {
            map3dContainer?.classList.add('hidden');
            map2dContainer?.classList.remove('hidden');
            setTimeout(() => {
                map2d?.map?.resize();
                if (chat?.lastVisualization) {
                    map2d?.updateVisualization(chat.lastVisualization);
                }
            }, 100);
        }
    });
}

// ============================================
// MAP SURFACE SWITCHING
// ============================================

function setupMapSurface() {
    const surfaceSelect = document.getElementById('map-surface');
    
    surfaceSelect?.addEventListener('change', () => {
        const surface = surfaceSelect.value;
        let style;
        
        switch (surface) {
            case 'satellite':
                style = 'mapbox://styles/mapbox/satellite-streets-v12';
                break;
            case 'street':
                style = 'mapbox://styles/mapbox/streets-v12';
                break;
            default:
                style = 'mapbox://styles/mapbox/dark-v11';
        }
        
        if (map2d?.map) {
            map2d.map.setStyle(style);
        }
        if (map3d?.map) {
            map3d.map.setStyle(style);
        }
    });
}

// ============================================
// POINT MODE CONTROLS
// ============================================

function setupClusterDistance() {
    const clusterDistanceInput = document.getElementById('cluster-distance');
    const clusterDistanceVal = document.getElementById('cluster-distance-val');
    
    if (clusterDistanceInput && clusterDistanceVal) {
        // Update display value
        clusterDistanceInput.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            clusterDistanceVal.textContent = value;
            window.appSettings.clusterDistanceKm = value;
            // Save to localStorage
            localStorage.setItem('geospatial-rag-settings', JSON.stringify(window.appSettings));
        });
    }
}

function setupPointModeControls() {
    const pointModeSelect = document.getElementById('point-mode');
    const scatterControls = document.getElementById('scatter-controls');
    const heatmapControls = document.getElementById('heatmap-controls');
    const hexagonControls = document.getElementById('hexagon-controls');
    
    function updateControlsVisibility() {
        const mode = pointModeSelect?.value || 'scatter';
        
        scatterControls?.classList.toggle('hidden', mode !== 'scatter');
        heatmapControls?.classList.toggle('hidden', mode !== 'heatmap');
        hexagonControls?.classList.toggle('hidden', mode !== 'hexagon');
        
        // Update map render mode
        if (map2d) {
            map2d.currentRenderMode = mode;
            map2d.renderLayers();
        }
    }
    
    pointModeSelect?.addEventListener('change', updateControlsVisibility);
    
    // Scatter controls
    document.getElementById('scatter-radius')?.addEventListener('input', (e) => {
        document.getElementById('scatter-radius-val').textContent = e.target.value;
        map2d?.renderLayers();
    });
    
    document.getElementById('scatter-opacity')?.addEventListener('input', (e) => {
        document.getElementById('scatter-opacity-val').textContent = e.target.value;
        map2d?.renderLayers();
    });
    
    // Heatmap controls
    document.getElementById('heat-radius')?.addEventListener('input', (e) => {
        document.getElementById('heat-radius-val').textContent = e.target.value;
        map2d?.renderLayers();
    });
    
    document.getElementById('heat-intensity')?.addEventListener('input', (e) => {
        document.getElementById('heat-intensity-val').textContent = e.target.value;
        map2d?.renderLayers();
    });
    
    // Hexagon controls
    document.getElementById('hex-radius')?.addEventListener('input', (e) => {
        document.getElementById('hex-radius-val').textContent = Math.round(e.target.value / 1000);
        map2d?.renderLayers();
    });
    
    document.getElementById('hex-elevation')?.addEventListener('input', (e) => {
        document.getElementById('hex-elevation-val').textContent = e.target.value;
        map2d?.renderLayers();
    });
}

// ============================================
// EXPORT FUNCTIONALITY
// ============================================

function setupExport() {
    const exportCsvBtn = document.getElementById('export-csv');
    const exportGeojsonBtn = document.getElementById('export-geojson');
    
    exportCsvBtn?.addEventListener('click', () => {
        if (!chat?.lastData?.length) return;
        
        const data = chat.lastData;
        const cols = Object.keys(data[0]).filter(c => c !== 'geojson_geom');
        
        let csv = cols.join(',') + '\n';
        data.forEach(row => {
            csv += cols.map(c => {
                const val = row[c] ?? '';
                // Escape quotes and wrap in quotes if contains comma
                const str = String(val).replace(/"/g, '""');
                return str.includes(',') ? `"${str}"` : str;
            }).join(',') + '\n';
        });
        
        downloadFile(`export_${data.length}.csv`, csv, 'text/csv');
    });
    
    exportGeojsonBtn?.addEventListener('click', () => {
        if (!chat?.lastVisualization?.geojson) return;
        
        const geojson = JSON.stringify(chat.lastVisualization.geojson, null, 2);
        downloadFile(`export_${chat.lastVisualization.geojson.features.length}.geojson`, geojson, 'application/geo+json');
    });
}

function downloadFile(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================
// SETTINGS MODAL
// ============================================

function setupSettingsModal() {
    const settingsBtn = document.getElementById('settings-btn');
    const modal = document.getElementById('settings-modal');
    const closeBtn = modal?.querySelector('.close-btn');
    const saveBtn = document.getElementById('save-settings');
    
    settingsBtn?.addEventListener('click', () => {
        modal?.classList.remove('hidden');
    });
    
    closeBtn?.addEventListener('click', () => {
        modal?.classList.add('hidden');
    });
    
    saveBtn?.addEventListener('click', saveSettings);
    
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
}

// ============================================
// ZOOM OUT BUTTON
// ============================================

function setupZoomOut() {
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    
    zoomOutBtn?.addEventListener('click', () => {
        const viewMode = document.getElementById('view-mode')?.value || '2d';
        
        if (viewMode === '3d') {
            map3d?.zoomOutToAll();
        } else {
            map2d?.zoomOutToAll();
        }
        
        zoomOutBtn.classList.add('hidden');
    });
}

// ============================================
// ML PREDICTION
// ============================================

function setupMLPrediction() {
    const mlBtn = document.getElementById('run-ml-prediction');
    const mlResults = document.getElementById('ml-results');
    const mlHighCount = document.getElementById('ml-high-count');
    const mlBgCount = document.getElementById('ml-bg-count');
    
    // Check ML status on load
    checkMLStatus();
    
    mlBtn?.addEventListener('click', async () => {
        if (!chat?.lastQuery) {
            alert('Please run a query first to get data for prediction.');
            return;
        }
        
        mlBtn.disabled = true;
        mlBtn.textContent = 'Running...';
        
        try {
            const response = await api.mlPredict(chat.lastQuery);
            
            if (response.success) {
                // Show results
                mlResults?.classList.remove('hidden');
                
                const summary = response.predictions_summary || {};
                if (mlHighCount) mlHighCount.textContent = summary.high_value || 0;
                if (mlBgCount) mlBgCount.textContent = summary.background || 0;
                
                // Update map with ML visualization
                if (response.visualization && map2d) {
                    map2d.updateAnalysisVisualization(response.visualization);
                }
                
                // Update table with predictions
                if (response.data && chat) {
                    chat.updateTable(response.data);
                    chat.lastData = response.data;
                }
                
                // Add message to chat
                chat?.addMessage('assistant', 
                    `🤖 **ML Prediction Complete**\n\n` +
                    `Found **${summary.high_value || 0}** High Value sites and **${summary.background || 0}** Background sites.\n\n` +
                    `Green points = High Value (predicted important deposits)\n` +
                    `Red points = Background (lower importance)`
                );
                
            } else {
                alert('Prediction failed: ' + (response.error || 'Unknown error'));
            }
        } catch (e) {
            console.error('ML prediction error:', e);
            alert('ML prediction failed: ' + e.message);
        } finally {
            mlBtn.disabled = false;
            mlBtn.textContent = 'Run Prediction on Current Data';
        }
    });
}

async function checkMLStatus() {
    const mlBtn = document.getElementById('run-ml-prediction');
    
    try {
        const status = await api.mlStatus();
        
        if (status.available && status.model_loaded) {
            console.log('ML model available');
        } else {
            console.warn('ML model not available:', status.message || status.error);
            if (mlBtn) {
                mlBtn.title = status.message || 'ML model not loaded';
            }
        }
    } catch (e) {
        console.warn('Could not check ML status:', e.message);
    }
}

// Enable ML button when data is loaded
window.enableMLButton = function() {
    const mlBtn = document.getElementById('run-ml-prediction');
    if (mlBtn) mlBtn.disabled = false;
};

// ============================================
// PROSPECTIVITY PREDICTION
// ============================================

let prospectivityMap = null;
let prospectivityMarker = null;
let selectedProspectivityLocation = null;
let autoFetchedData = {};

function setupProspectivityPrediction() {
    const openBtn = document.getElementById('open-prospectivity-modal');
    const modal = document.getElementById('prospectivity-modal');
    const closeBtn = document.getElementById('close-prospectivity-modal');
    const predictBtn = document.getElementById('run-prospectivity-prediction');
    
    // Open modal
    openBtn?.addEventListener('click', async () => {
        modal?.classList.remove('hidden');
        await initProspectivityMap();
    });
    
    // Close modal
    closeBtn?.addEventListener('click', () => {
        modal?.classList.add('hidden');
        resetProspectivityForm();
    });
    
    // Close on backdrop click
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
            resetProspectivityForm();
        }
    });
    
    // Run prediction
    predictBtn?.addEventListener('click', runProspectivityPrediction);
}

async function initProspectivityMap() {
    const container = document.getElementById('prospectivity-map');
    if (!container || prospectivityMap) return;
    
    const token = window.appSettings.mapboxToken;
    if (!token) {
        container.innerHTML = '<p class="muted" style="padding: 20px;">Please set Mapbox token in Settings</p>';
        return;
    }
    
    mapboxgl.accessToken = token;
    
    // Create map
    prospectivityMap = new mapboxgl.Map({
        container: 'prospectivity-map',
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [44, 24],  // Saudi Arabia
        zoom: 5
    });
    
    prospectivityMap.on('load', async () => {
        // Load geology polygons
        try {
            const geojson = await api.prospectivityGeologyPolygons();
            
            // Add geology source
            prospectivityMap.addSource('geology-zones', {
                type: 'geojson',
                data: geojson
            });
            
            // Valid zones (green)
            prospectivityMap.addLayer({
                id: 'geology-valid-fill',
                type: 'fill',
                source: 'geology-zones',
                paint: {
                    'fill-color': '#22c55e',
                    'fill-opacity': 0.3
                }
            });
            
            prospectivityMap.addLayer({
                id: 'geology-valid-outline',
                type: 'line',
                source: 'geology-zones',
                paint: {
                    'line-color': '#22c55e',
                    'line-width': 1,
                    'line-opacity': 0.6
                }
            });
            
            // Fit to geology extent
            const bounds = new mapboxgl.LngLatBounds();
            geojson.features.forEach(f => {
                if (f.geometry?.coordinates) {
                    const coords = f.geometry.type === 'MultiPolygon' 
                        ? f.geometry.coordinates.flat(2)
                        : f.geometry.coordinates.flat(1);
                    coords.forEach(c => {
                        if (Array.isArray(c) && c.length >= 2) {
                            bounds.extend(c);
                        }
                    });
                }
            });
            
            if (!bounds.isEmpty()) {
                prospectivityMap.fitBounds(bounds, { padding: 50 });
            }
            
        } catch (e) {
            console.error('Failed to load geology polygons:', e);
        }
        
        // Click handler
        prospectivityMap.on('click', handleProspectivityMapClick);
    });
}

async function handleProspectivityMapClick(e) {
    const lng = e.lngLat.lng;
    const lat = e.lngLat.lat;
    
    // Check if inside a geology polygon
    const features = prospectivityMap.queryRenderedFeatures(e.point, {
        layers: ['geology-valid-fill']
    });
    
    if (features.length === 0) {
        // Invalid zone - show warning
        document.getElementById('selected-coords').innerHTML = 
            '<span class="invalid-zone">⚠️ Outside geology zone - select a green area</span>';
        document.getElementById('run-prospectivity-prediction').disabled = true;
        return;
    }
    
    // Valid selection
    selectedProspectivityLocation = { longitude: lng, latitude: lat };
    
    // Update marker
    if (prospectivityMarker) {
        prospectivityMarker.setLngLat([lng, lat]);
    } else {
        prospectivityMarker = new mapboxgl.Marker({ color: '#22c55e' })
            .setLngLat([lng, lat])
            .addTo(prospectivityMap);
    }
    
    // Update display
    document.getElementById('selected-coords').innerHTML = 
        `<span class="valid-zone">✓</span> ${lng.toFixed(5)}, ${lat.toFixed(5)}`;
    
    // Enable predict button
    document.getElementById('run-prospectivity-prediction').disabled = false;
    
    // Fetch auto data
    await fetchAutoData(lng, lat);
}

async function fetchAutoData(lng, lat) {
    try {
        // Fetch geology and distances in parallel (silently)
        const [geologyRes, distRes] = await Promise.all([
            api.prospectivityGeologyAtPoint(lng, lat),
            api.prospectivityDistancesAtPoint(lng, lat)
        ]);
        
        autoFetchedData = {};
        
        // Geology data
        if (geologyRes.inside_polygon && geologyRes.geology) {
            autoFetchedData = { ...autoFetchedData, ...geologyRes.geology };
        }
        
        // Distance data
        if (distRes.success && distRes.distances) {
            autoFetchedData = { ...autoFetchedData, ...distRes.distances };
        }
        
    } catch (e) {
        console.error('Failed to fetch auto data:', e);
    }
}

async function runProspectivityPrediction() {
    if (!selectedProspectivityLocation) {
        alert('Please select a location on the map first');
        return;
    }
    
    const predictBtn = document.getElementById('run-prospectivity-prediction');
    predictBtn.disabled = true;
    predictBtn.textContent = 'Predicting...';
    
    try {
        // Gather form data
        const formData = {
            ...selectedProspectivityLocation,
            elevation: parseFloat(document.getElementById('prosp-elevation')?.value) || 0,
            reg_struct: document.getElementById('prosp-reg-struct')?.value || null,
            host_rocks: document.getElementById('prosp-host-rocks')?.value || null,
            country_ro: document.getElementById('prosp-country-ro')?.value || null,
            gitology: document.getElementById('prosp-gitology')?.value || null,
            alteration: document.getElementById('prosp-alteration')?.value || null,
            min_morpho: document.getElementById('prosp-min-morpho')?.value || null,
            ...autoFetchedData
        };
        
        // Run prediction
        const result = await api.prospectivityPredict(formData);
        
        if (result.success) {
            displayProspectivityResult(result);
        } else {
            alert('Prediction failed: ' + (result.error || 'Unknown error'));
        }
        
    } catch (e) {
        console.error('Prediction error:', e);
        alert('Prediction failed: ' + e.message);
    } finally {
        predictBtn.disabled = false;
        predictBtn.textContent = 'Run Prediction';
    }
}

function displayProspectivityResult(result) {
    // Modal result
    const modalResult = document.getElementById('modal-prediction-result');
    const modalValue = document.getElementById('modal-result-value');
    
    modalResult?.classList.remove('hidden');
    
    const prediction = result.prediction;
    modalValue.textContent = prediction;
    modalValue.className = 'result-value ' + prediction.toLowerCase();
    
    // Sidebar result
    const sidebarResult = document.getElementById('prospectivity-result');
    const sidebarValue = document.getElementById('prosp-prediction');
    
    sidebarResult?.classList.remove('hidden');
    
    sidebarValue.textContent = prediction;
    sidebarValue.className = 'prediction-value ' + prediction.toLowerCase();
    
    // Update marker color
    if (prospectivityMarker) {
        const colors = { Low: '#ef4444', Medium: '#f59e0b', High: '#22c55e' };
        prospectivityMarker.remove();
        prospectivityMarker = new mapboxgl.Marker({ color: colors[prediction] || '#6b7280' })
            .setLngLat([selectedProspectivityLocation.longitude, selectedProspectivityLocation.latitude])
            .addTo(prospectivityMap);
    }
}

function resetProspectivityForm() {
    selectedProspectivityLocation = null;
    autoFetchedData = {};
    
    // Reset marker
    if (prospectivityMarker) {
        prospectivityMarker.remove();
        prospectivityMarker = null;
    }
    
    // Reset display
    document.getElementById('selected-coords').textContent = 'Click on map to select';
    document.getElementById('modal-prediction-result')?.classList.add('hidden');
    document.getElementById('run-prospectivity-prediction').disabled = true;
    
    // Reset form fields
    document.getElementById('prosp-elevation').value = '';
    document.getElementById('prosp-reg-struct').value = '';
    document.getElementById('prosp-host-rocks').value = '';
    document.getElementById('prosp-country-ro').value = '';
    document.getElementById('prosp-gitology').value = '';
    document.getElementById('prosp-alteration').value = '';
    document.getElementById('prosp-min-morpho').value = '';
}

// ============================================
// HEALTH CHECK
// ============================================

async function checkHealth() {
    try {
        const health = await api.healthCheck();
        console.log('Backend health:', health.status);
    } catch (e) {
        console.warn('Backend not reachable:', e.message);
    }
}

// ============================================
// UPDATE UI AFTER QUERY
// ============================================

window.updateUIAfterQuery = function(response) {
    // Update feature count
    const featureCount = document.getElementById('feature-count');
    if (featureCount && response.visualization?.geojson) {
        const count = response.visualization.geojson.features.length;
        const type = response.visualization.layer_type || 'feature';
        featureCount.textContent = `${count} ${type}${count !== 1 ? 's' : ''}`;
    }
    
    // Update result count
    const resultCount = document.getElementById('result-count');
    if (resultCount && response.data) {
        resultCount.textContent = `${response.data.length} rows`;
    }
    
    // Enable export buttons
    const exportCsv = document.getElementById('export-csv');
    const exportGeojson = document.getElementById('export-geojson');
    
    if (exportCsv) exportCsv.disabled = !response.data?.length;
    if (exportGeojson) exportGeojson.disabled = !response.visualization?.geojson;
    
    // Enable ML prediction button if we have point data from mods table
    const mlBtn = document.getElementById('run-ml-prediction');
    const isPointData = response.query_type === 'point' || response.visualization?.layer_type === 'point';
    if (mlBtn && isPointData && response.data?.length) {
        mlBtn.disabled = false;
        // Hide previous ML results
        document.getElementById('ml-results')?.classList.add('hidden');
    }
    
    // Update dataset count
    const datasetCount = document.getElementById('dataset-count');
    if (datasetCount && response.visualization?.geojson) {
        datasetCount.textContent = '1';
    }
};

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Geospatial RAG...');

    loadSettings();
    
    // Setup UI interactions
    setupPanelResizing();
    setupChatCollapse();
    setupLayersCollapse();
    setupTableCollapse();
    setupViewMode();
    setupMapSurface();
    setupPointModeControls();
    setupClusterDistance();
    setupExport();
    setupSettingsModal();
    setupZoomOut();
    setupMLPrediction();
    setupProspectivityPrediction();
    setupVoiceRecording();

    const token = window.appSettings.mapboxToken;
    
    if (token) {
        // Hide config banner
        document.getElementById('config-banner')?.classList.add('hidden');
        
        try {
            map2d = new Map2D('map2d');
            await map2d.initialize(token);
        } catch (e) {
            console.error('Failed to init 2D map:', e);
        }

        try {
            map3d = new Map3D('map3d');
            await map3d.initialize(token);
        } catch (e) {
            console.error('Failed to init 3D map:', e);
        }
    } else {
        console.warn('No Mapbox token - please configure in Settings');
    }

    // Initialize chat
    chat = new Chat();

    // Health check
    checkHealth();
    setInterval(checkHealth, 60000);

    console.log('Geospatial RAG ready!');
});

// ============================================
// VOICE RECORDING (Arabic Speech)
// ============================================

function setupVoiceRecording() {
    const voiceBtn = document.getElementById('voice-btn');
    const voiceStatus = document.getElementById('voice-status');
    const voiceStatusText = document.getElementById('voice-status-text');
    
    if (!voiceBtn) return;
    
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let recordingStream = null;
    let minRecordingTime = 1000; // Minimum 1 second recording
    let recordingStartTime = 0;
    
    // Check for browser support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        voiceBtn.style.display = 'none';
        console.warn('Voice recording not supported in this browser');
        return;
    }
    
    // Determine best supported audio format
    const getMimeType = () => {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4'
        ];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                console.log('Using audio format:', type);
                return type;
            }
        }
        return 'audio/webm'; // fallback
    };
    
    // Click to toggle recording (better UX than hold)
    voiceBtn.addEventListener('click', toggleRecording);
    
    async function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
            await startRecording();
        }
    }
    
    async function startRecording() {
        if (isRecording) return;
        
        try {
            recordingStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,  // Whisper works best with 16kHz
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,  // Normalize volume
                    // Request high quality
                    sampleSize: 16,
                    latency: 0.01  // Low latency
                }
            });
            
            const mimeType = getMimeType();
            mediaRecorder = new MediaRecorder(recordingStream, { mimeType });
            
            audioChunks = [];
            recordingStartTime = Date.now();
            
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };
            
            mediaRecorder.onstop = async () => {
                // Stop all tracks
                if (recordingStream) {
                    recordingStream.getTracks().forEach(track => track.stop());
                    recordingStream = null;
                }
                
                const totalSize = audioChunks.reduce((sum, chunk) => sum + chunk.size, 0);
                console.log('Recording stopped. Chunks:', audioChunks.length, 'Total size:', totalSize, 'bytes');
                
                if (audioChunks.length > 0 && totalSize > 500) {
                    await processVoiceRecording();
                } else {
                    resetButton();
                    chat?.addAssistantMessage('Recording too short. Click the mic, speak for at least 2 seconds, then click again.');
                }
            };
            
            // Request data every 250ms
            mediaRecorder.start(250);
            isRecording = true;
            
            voiceBtn.classList.add('recording');
            voiceStatus.classList.remove('hidden');
            voiceStatusText.textContent = '🔴 Recording... Click mic to stop';
            
        } catch (err) {
            console.error('Failed to start recording:', err);
            resetButton();
            alert('Could not access microphone. Please allow microphone access.');
        }
    }
    
    function stopRecording() {
        if (!isRecording || !mediaRecorder) return;
        
        // Ensure minimum recording time
        const elapsed = Date.now() - recordingStartTime;
        
        if (elapsed < minRecordingTime) {
            voiceStatusText.textContent = `Keep speaking... (${Math.ceil((minRecordingTime - elapsed) / 1000)}s)`;
            setTimeout(() => {
                if (isRecording) {
                    actuallyStopRecording();
                }
            }, minRecordingTime - elapsed);
        } else {
            actuallyStopRecording();
        }
    }
    
    function actuallyStopRecording() {
        if (!mediaRecorder || mediaRecorder.state === 'inactive') {
            resetButton();
            return;
        }
        
        isRecording = false;
        
        try {
            mediaRecorder.stop();
        } catch (e) {
            console.error('Error stopping recorder:', e);
        }
        
        voiceBtn.classList.remove('recording');
        voiceBtn.classList.add('processing');
        voiceStatusText.textContent = 'Processing...';
    }
    
    function resetButton() {
        isRecording = false;
        voiceBtn.classList.remove('recording', 'processing');
        voiceStatus.classList.add('hidden');
    }
    
    async function processVoiceRecording() {
        try {
            // Create blob from chunks
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            console.log('Audio blob created:', audioBlob.size, 'bytes');
            
            if (audioBlob.size < 1000) {
                throw new Error('Audio recording too small. Please speak louder or longer.');
            }
            
            // Convert to base64
            const base64Audio = await blobToBase64(audioBlob);
            console.log('Base64 length:', base64Audio.length);
            
            voiceStatusText.textContent = 'Transcribing Arabic...';
            
            // Send to API
            const result = await api.voiceArabic(base64Audio, 'webm');
            
            resetButton();
            
            if (result.success) {
                // Display the result in chat
                displayVoiceResult(result);
            } else {
                chat?.addAssistantMessage(`Voice processing failed: ${result.error || 'Unknown error'}`);
            }
            
        } catch (err) {
            console.error('Voice processing error:', err);
            resetButton();
            chat?.addAssistantMessage(`Voice error: ${err.message}`);
        }
    }
    
    function blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
    
    function displayVoiceResult(result) {
        // Add user message (what they said in English)
        const englishQuery = result.input?.english_query || '(Voice query)';
        chat?.addUserMessage(`🎤 ${englishQuery}`);
        
        // Get agent result
        const agentResult = result.agent_result || {};
        
        // Build response message
        let responseHtml = '';
        
        // Add English response
        const englishResponse = result.output?.english_response || agentResult.response || '';
        if (englishResponse) {
            responseHtml += `<div class="english-response">${formatResponse(englishResponse)}</div>`;
        }
        
        // Add Arabic text
        const arabicText = result.output?.arabic_text;
        if (arabicText) {
            responseHtml += `<div class="arabic-text">${arabicText}</div>`;
        }
        
        // Add audio player
        const audioBase64 = result.output?.audio_base64;
        if (audioBase64) {
            responseHtml += `
                <div class="voice-response-audio">
                    <audio controls autoplay>
                        <source src="data:audio/mp3;base64,${audioBase64}" type="audio/mp3">
                    </audio>
                </div>
            `;
        }
        
        // Add the message with HTML
        chat?.addAssistantMessageHtml(responseHtml);
        
        // Update visualization if available
        if (agentResult.visualization) {
            const viewMode = document.getElementById('view-mode')?.value || '2d';
            
            // Update the active map view
            if (viewMode === '2d' && typeof map2d !== 'undefined' && map2d) {
                map2d.updateVisualization(agentResult.visualization);
            }
            if (viewMode === '3d' && typeof map3d !== 'undefined' && map3d) {
                map3d.updateVisualization(agentResult.visualization);
            }
            
            // Also update the other map in background
            if (typeof map2d !== 'undefined' && map2d) {
                map2d.updateVisualization(agentResult.visualization);
            }
            if (typeof map3d !== 'undefined' && map3d) {
                map3d.updateVisualization(agentResult.visualization);
            }
        }
        
        // Update data table if available
        if (agentResult.data && chat) {
            chat.updateTable(agentResult.data);
        }
        
        // Enable export buttons and update UI
        if (typeof updateUIAfterQuery === 'function') {
            updateUIAfterQuery({
                data: agentResult.data,
                visualization: agentResult.visualization,
                query_type: agentResult.query_type
            });
        }
    }
    
    function formatResponse(text) {
        // Convert markdown-like formatting to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }
}
