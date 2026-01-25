/**
 * Chat Interface for Geospatial RAG
 * Handles: Messages, Query Processing, Analysis Suggestions, Table Updates
 */
class Chat {
    constructor() {
        this.messagesContainer = document.getElementById('chat-messages');
        this.input = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        
        this.isProcessing = false;
        this.lastVisualization = null;
        this.lastQuery = '';
        this.lastData = null;
        
        // Analysis state
        this.analysisAvailable = false;
        this.analysisOptions = [];
        this.currentTableData = null; // Current filtered table data
        
        this.setupEventListeners();
        this.addWelcomeMessage();
    }

    addWelcomeMessage() {
        this.addMessage('assistant', 
            'Hey there! Ready to explore the mining database.\n\n' +
            'You can ask things like:\n' +
            '• Show me gold deposits in the Eastern region\n' +
            '• Where are the copper occurrences?\n' +
            '• Find mineral sites within 50km of Riyadh\n\n' +
            'Just type your question below.'
        );
    }

    setupEventListeners() {
        this.sendBtn?.addEventListener('click', () => this.sendMessage());
        
        // Auto-resize textarea
        if (this.input && this.input.tagName === 'TEXTAREA') {
            this.input.addEventListener('input', () => this.autoResizeTextarea());
            // Initial resize
            this.autoResizeTextarea();
        }
        
        this.input?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    autoResizeTextarea() {
        if (!this.input || this.input.tagName !== 'TEXTAREA') return;
        
        // Reset height to auto to get the correct scrollHeight
        this.input.style.height = 'auto';
        
        // Set height based on content, with min and max limits
        const minHeight = 44; // Minimum height (1 line)
        const maxHeight = 200; // Maximum height
        const newHeight = Math.min(Math.max(this.input.scrollHeight, minHeight), maxHeight);
        
        this.input.style.height = `${newHeight}px`;
        
        // Show scrollbar if content exceeds max height
        this.input.style.overflowY = this.input.scrollHeight > maxHeight ? 'auto' : 'hidden';
    }

    async sendMessage() {
        const query = this.input?.value.trim();
        if (!query || this.isProcessing) return;

        this.addMessage('user', query);
        this.input.value = '';
        
        // Reset textarea height after sending
        if (this.input && this.input.tagName === 'TEXTAREA') {
            this.input.style.height = 'auto';
        }
        
        this.lastQuery = query;

        await this.processQuery(query);
    }

    async processQuery(query) {
        this.isProcessing = true;
        this.showLoading(true);

        try {
            // Check if this is an analysis request
            const queryLower = query.toLowerCase().trim();
            const isAnalysisRequest = (
                queryLower.includes('cluster') ||
                queryLower.includes('regional') ||
                queryLower.includes('commodity') ||
                queryLower.includes('geology correlation') ||
                queryLower.includes('analysis') ||
                queryLower.includes('analyze')
            );
            
            // Get current table data if available
            const currentData = this.getCurrentTableData();
            
            // If it's an analysis request and we have current data, use it
            if (isAnalysisRequest && currentData && currentData.length > 0) {
                // Map query to analysis key
                let analysisKey = 'clustering'; // default
                if (queryLower.includes('cluster')) analysisKey = 'clustering';
                else if (queryLower.includes('regional')) analysisKey = 'regional';
                else if (queryLower.includes('commodity')) analysisKey = 'commodity';
                else if (queryLower.includes('geology')) analysisKey = 'geology_correlation';
                
                // Only pass cluster distance for clustering analysis
                let clusterDistance = null;
                if (analysisKey === 'clustering') {
                    clusterDistance = parseFloat(window.appSettings?.clusterDistanceKm) || 5;
                    console.log(`Running clustering with distance: ${clusterDistance} km`);
                }
                const response = await api.runAnalysisOnData(analysisKey, currentData, clusterDistance);
                this.handleResponse(response);
            } else {
                // Regular query - send with optional current data
                const response = await api.query(query, {
                    maxResults: window.appSettings?.maxResults || 500,
                    currentData: currentData // Send current data so backend can use it for analysis
                });
                this.handleResponse(response);
            }
        } catch (error) {
            this.addMessage('assistant', `Error: ${error.message}`);
        } finally {
            this.isProcessing = false;
            this.showLoading(false);
        }
    }

    handleResponse(response) {
        if (!response.success) {
            this.addMessage('assistant', `Sorry: ${response.error || 'An error occurred'}`);
            return;
        }

        // Check if this is an analysis result
        if (response.is_analysis_result) {
            this.handleAnalysisResult(response);
            return;
        }

        // Clear previous analysis UI when new query comes in
        this.clearAnalysisUI();

        this.lastData = response.data;
        this.lastVisualization = response.visualization;

        // Store analysis state
        this.analysisAvailable = response.analysis_available || false;
        this.analysisOptions = response.analysis_options || [];

        // Build response message
        let message = '';
        
        if (response.description) {
            message += response.description + '\n\n';
        }
        
        const layerType = response.visualization?.layer_type || 'feature';
        const count = response.row_count || 0;
        message += `Found **${count}** ${layerType}${count !== 1 ? 's' : ''}.`;

        this.addMessage('assistant', message);

        // Show analysis suggestions if available
        if (this.analysisAvailable && this.analysisOptions.length > 0) {
            this.showAnalysisSuggestions();
        }

        // Update maps
        if (response.visualization) {
            const viewMode = document.getElementById('view-mode')?.value || '2d';
            
            if (viewMode === '2d' && typeof map2d !== 'undefined' && map2d) {
                map2d.updateVisualization(response.visualization);
            }
            if (viewMode === '3d' && typeof map3d !== 'undefined' && map3d) {
                map3d.updateVisualization(response.visualization);
            }
            
            // Also update the other map in background
            if (typeof map2d !== 'undefined' && map2d) {
                map2d.updateVisualization(response.visualization);
            }
            if (typeof map3d !== 'undefined' && map3d) {
                map3d.updateVisualization(response.visualization);
            }
        }

        // Update table
        if (response.data) {
            this.updateTable(response.data);
        }

        // Update UI elements
        if (typeof window.updateUIAfterQuery === 'function') {
            window.updateUIAfterQuery(response);
        }
    }

    handleAnalysisResult(response) {
        // Display analysis summary
        this.addMessage('assistant', response.response || 'Analysis completed.');

        // Store analysis data for filtering
        this.lastAnalysisData = response.data || [];
        this.lastAnalysisVisualization = response.visualization;
        this.hiddenClusters = new Set(); // Track which clusters are hidden

        // Update visualization if provided
        if (response.visualization?.geojson) {
            const viz = {
                geojson: response.visualization.geojson,
                layer_type: 'point',
                legend: response.visualization.legend,
                isAnalysis: true
            };
            
            this.lastVisualization = viz;
            
            if (typeof map2d !== 'undefined' && map2d) {
                map2d.updateAnalysisVisualization(viz);
            }
        }

        // Show interactive legend (clickable to filter)
        if (response.visualization?.legend) {
            this.showInteractiveLegend(response.visualization.legend);
        }

        // Show chart if available
        if (response.visualization?.chart_data) {
            this.showChart(response.visualization.chart_data);
        }

        // Update table with analysis data
        if (response.data && response.data.length > 0) {
            this.updateTable(response.data);
        }
    }

    showInteractiveLegend(legend) {
        if (!legend) return;

        // Render legend in the Layers panel
        const legendContainer = document.getElementById('analysis-legend-container');
        if (!legendContainer) return;

        let html = `
            <div class="analysis-legend">
                <div class="legend-header">
                    <span>🎨 Filter Clusters</span>
                    <span class="legend-hint">(click to show/hide)</span>
                </div>
                <div class="legend-items">
        `;

        legend.forEach((item, idx) => {
            const clusterId = item.label.includes('Unclustered') ? 'unclustered' : item.label.replace('Cluster ', '');
            html += `
                <button class="legend-item active" data-cluster-id="${clusterId}" data-color="${item.color}">
                    <span class="legend-color" style="background: ${item.color}"></span>
                    <span class="legend-label">${item.label}</span>
                    <span class="legend-check">✓</span>
                </button>
            `;
        });

        html += `
                </div>
                <div class="legend-actions">
                    <button class="legend-action-btn" id="legend-show-all">Show All</button>
                    <button class="legend-action-btn" id="legend-hide-all">Hide All</button>
                </div>
            </div>
        `;

        legendContainer.innerHTML = html;

        // Add click handlers for legend items
        legendContainer.querySelectorAll('.legend-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const clusterId = btn.dataset.clusterId;
                btn.classList.toggle('active');
                this.toggleClusterVisibility(clusterId, btn.classList.contains('active'));
            });
        });

        // Show/Hide all buttons
        legendContainer.querySelector('#legend-show-all')?.addEventListener('click', () => {
            this.showAllClusters();
            legendContainer.querySelectorAll('.legend-item').forEach(btn => btn.classList.add('active'));
        });

        legendContainer.querySelector('#legend-hide-all')?.addEventListener('click', () => {
            this.hideAllClusters();
            legendContainer.querySelectorAll('.legend-item').forEach(btn => btn.classList.remove('active'));
        });
    }

    clearAnalysisUI() {
        // Hide analysis section and clear legend
        this.hideAnalysisSection();
        const legendContainer = document.getElementById('analysis-legend-container');
        if (legendContainer) {
            legendContainer.innerHTML = '';
        }
    }

    toggleClusterVisibility(clusterId, visible) {
        if (visible) {
            this.hiddenClusters.delete(clusterId);
        } else {
            this.hiddenClusters.add(clusterId);
        }
        this.updateFilteredView();
    }

    showAllClusters() {
        this.hiddenClusters.clear();
        this.updateFilteredView();
    }

    hideAllClusters() {
        // Get all cluster IDs from the data
        if (this.lastAnalysisData) {
            this.lastAnalysisData.forEach(item => {
                const clusterId = item.cluster_id === null ? 'unclustered' : String(item.cluster_id);
                this.hiddenClusters.add(clusterId);
            });
        }
        this.updateFilteredView();
    }

    updateFilteredView() {
        if (!this.lastAnalysisData || !this.lastAnalysisVisualization) return;

        // Filter data based on hidden clusters
        const filteredData = this.lastAnalysisData.filter(item => {
            const clusterId = item.cluster_id === null ? 'unclustered' : String(item.cluster_id);
            return !this.hiddenClusters.has(clusterId);
        });

        // Filter GeoJSON features
        const filteredFeatures = this.lastAnalysisVisualization.geojson.features.filter(f => {
            const clusterId = f.properties.cluster_id === null ? 'unclustered' : String(f.properties.cluster_id);
            return !this.hiddenClusters.has(clusterId);
        });

        // Update map
        if (typeof map2d !== 'undefined' && map2d) {
            const filteredViz = {
                geojson: {
                    type: 'FeatureCollection',
                    features: filteredFeatures
                },
                layer_type: 'point',
                isAnalysis: true
            };
            map2d.updateAnalysisVisualization(filteredViz);
        }

        // Update table
        this.updateTable(filteredData);

        // Update chart to reflect filtered data
        this.updateChartWithFilter();

        // Store filtered data for export
        this.lastFilteredData = filteredData;
    }

    updateChartWithFilter() {
        if (!this.currentChart || !this.originalChartData) return;

        const labels = this.originalChartData.data.labels;
        const originalValues = this.originalChartData.data.datasets[0].data;
        const colors = this.originalChartData.data.datasets[0].backgroundColor;

        // Filter chart data based on hidden clusters
        const filteredLabels = [];
        const filteredValues = [];
        const filteredColors = [];

        labels.forEach((label, idx) => {
            const clusterId = label.includes('Unclustered') ? 'unclustered' : label.replace('Cluster ', '');
            if (!this.hiddenClusters.has(clusterId)) {
                filteredLabels.push(label);
                filteredValues.push(originalValues[idx]);
                filteredColors.push(colors[idx]);
            }
        });

        // Update chart data
        this.currentChart.data.labels = filteredLabels;
        this.currentChart.data.datasets[0].data = filteredValues;
        this.currentChart.data.datasets[0].backgroundColor = filteredColors;
        this.currentChart.update('none'); // Update without animation for smoother toggling
    }

    // Get current filtered data for export
    getExportData() {
        return this.lastFilteredData || this.lastAnalysisData || this.lastData;
    }

    showAnalysisSuggestions() {
        if (!this.messagesContainer) return;

        const div = document.createElement('div');
        div.className = 'analysis-suggestions';
        
        let html = `
            <div class="analysis-header">
                <span class="analysis-icon">📊</span>
                <span>Spatial Analysis Available</span>
            </div>
            <div class="analysis-options">
        `;

        this.analysisOptions.forEach((opt, idx) => {
            html += `
                <button class="analysis-btn" data-analysis-id="${idx + 1}" data-analysis-name="${opt.name}">
                    <span class="analysis-btn-icon">${opt.icon || '📈'}</span>
                    <span class="analysis-btn-text">${opt.name}</span>
                </button>
            `;
        });

        html += `
            </div>
            <div class="analysis-hint">Click an option or type the number (1-${this.analysisOptions.length})</div>
        `;

        div.innerHTML = html;

        // Add click handlers
        div.querySelectorAll('.analysis-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.dataset.analysisId;
                const name = btn.dataset.analysisName;
                this.runAnalysis(id, name);
            });
        });

        this.messagesContainer.appendChild(div);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    async runAnalysis(id, name) {
        this.addMessage('user', `Run analysis: ${name}`);
        
        // Remove the suggestions panel
        const suggestions = this.messagesContainer.querySelector('.analysis-suggestions');
        if (suggestions) {
            suggestions.remove();
        }

        this.isProcessing = true;
        this.showLoading(true);

        try {
            // Map analysis ID to analysis key
            const analysisKeys = ['clustering', 'regional', 'commodity', 'geology_correlation'];
            const analysisKey = analysisKeys[id - 1] || 'clustering';
            
            // Get current table data (filtered data if polygons are selected)
            const currentData = this.getCurrentTableData();
            
            if (currentData && currentData.length > 0) {
                // Run analysis on current table data
                // Only pass cluster distance for clustering analysis
                let clusterDistance = null;
                if (analysisKey === 'clustering') {
                    clusterDistance = parseFloat(window.appSettings?.clusterDistanceKm) || 5;
                    console.log(`Running clustering with distance: ${clusterDistance} km`);
                }
                const response = await api.runAnalysisOnData(analysisKey, currentData, clusterDistance);
                this.handleResponse(response);
            } else {
                // Fallback: use analysis ID as query (for backwards compatibility)
                const response = await api.query(id, {
                    maxResults: window.appSettings?.maxResults || 500
                });
                this.handleResponse(response);
            }
        } catch (error) {
            this.addMessage('assistant', `Analysis error: ${error.message}`);
        } finally {
            this.isProcessing = false;
            this.showLoading(false);
        }
    }
    
    getCurrentTableData() {
        // Get current filtered data from map2d if available
        if (typeof map2d !== 'undefined' && map2d && map2d.currentData) {
            // Convert map2d currentData to table format
            return map2d.currentData.map(point => ({
                gid: point.properties?.gid,
                longitude: point.longitude,
                latitude: point.latitude,
                ...point.properties
            }));
        }
        
        // Fallback to stored table data
        return this.currentTableData || this.lastData;
    }

    showChart(chartData) {
        if (!chartData) return;

        // Show the analysis section in Layers panel
        const analysisSection = document.getElementById('analysis-section');
        const chartContainer = document.getElementById('analysis-chart-container');
        const canvas = document.getElementById('analysis-chart');
        
        if (!analysisSection || !canvas) return;

        // Show the section
        analysisSection.classList.remove('hidden');

        // Destroy previous chart if exists
        if (this.currentChart) {
            this.currentChart.destroy();
        }

        // Store original chart data for filtering
        this.originalChartData = JSON.parse(JSON.stringify(chartData));
        
        // Initialize Chart.js
        if (typeof Chart !== 'undefined') {
            try {
                this.currentChart = new Chart(canvas.getContext('2d'), {
                    type: chartData.type || 'doughnut',
                    data: JSON.parse(JSON.stringify(chartData.data)), // Deep copy
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    color: '#94a3b8',
                                    padding: 10,
                                    font: { size: 11 },
                                    boxWidth: 12
                                }
                            }
                        },
                        ...chartData.options
                    }
                });
            } catch (e) {
                console.error('Chart rendering failed:', e);
            }
        }
    }

    hideAnalysisSection() {
        const analysisSection = document.getElementById('analysis-section');
        if (analysisSection) {
            analysisSection.classList.add('hidden');
        }
        if (this.currentChart) {
            this.currentChart.destroy();
            this.currentChart = null;
        }
    }

    updateTable(data) {
        // Store current table data for analysis
        this.currentTableData = data;
        
        if (!data?.length) {
            this.clearTable();
            return;
        }

        const header = document.getElementById('table-header');
        const body = document.getElementById('table-body');
        
        // Get columns (exclude geojson_geom)
        const cols = Object.keys(data[0]).filter(c => c !== 'geojson_geom');
        
        // Build header
        if (header) {
            header.innerHTML = '<tr>' + cols.map(c => 
                `<th>${this.formatColumnName(c)}</th>`
            ).join('') + '</tr>';
        }
        
        // Build body (limit to 500 rows for performance)
        if (body) {
            body.innerHTML = data.slice(0, 500).map((row, idx) => 
                `<tr data-idx="${idx}">` + 
                cols.map(c => `<td title="${this.escapeHtml(row[c])}">${this.escapeHtml(row[c] ?? '')}</td>`).join('') + 
                '</tr>'
            ).join('');
            
            // Add click handlers for row selection
            body.querySelectorAll('tr').forEach(tr => {
                tr.addEventListener('click', () => {
                    const idx = parseInt(tr.dataset.idx);
                    this.selectRow(idx, data[idx]);
                });
            });
        }
    }

    clearTable() {
        const header = document.getElementById('table-header');
        const body = document.getElementById('table-body');
        if (header) header.innerHTML = '';
        if (body) body.innerHTML = '<tr><td class="muted" style="padding: 20px;">No data loaded yet.</td></tr>';
    }

    selectRow(idx, rowData) {
        // Highlight selected row
        const body = document.getElementById('table-body');
        body?.querySelectorAll('tr').forEach(tr => tr.classList.remove('selected'));
        body?.querySelector(`tr[data-idx="${idx}"]`)?.classList.add('selected');
        
        // Fly to location on map if coordinates exist
        const lat = parseFloat(rowData.latitude || rowData.lat);
        const lon = parseFloat(rowData.longitude || rowData.lon || rowData.lng);
        
        if (!isNaN(lat) && !isNaN(lon)) {
            const viewMode = document.getElementById('view-mode')?.value || '2d';
            
            if (viewMode === '2d' && map2d?.map) {
                map2d.map.flyTo({ center: [lon, lat], zoom: 12, duration: 1000 });
                document.getElementById('zoom-out-btn')?.classList.remove('hidden');
            }
            if (viewMode === '3d' && map3d?.map) {
                map3d.map.flyTo({ center: [lon, lat], zoom: 14, pitch: 70, duration: 2000 });
                document.getElementById('zoom-out-btn')?.classList.remove('hidden');
            }
        }
    }

    formatColumnName(col) {
        return col
            .replace(/_/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());
    }

    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const str = String(text);
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    addMessage(role, content) {
        if (!this.messagesContainer) return;
        
        const div = document.createElement('div');
        div.className = `message ${role}`;
        
        // Format content
        const formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        
        div.innerHTML = `<div class="message-content">${formatted}</div>`;
        
        this.messagesContainer.appendChild(div);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    // Add message with raw HTML content (for voice responses with audio)
    addMessageHtml(role, htmlContent) {
        if (!this.messagesContainer) return;
        
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerHTML = `<div class="message-content">${htmlContent}</div>`;
        
        this.messagesContainer.appendChild(div);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    // Convenience methods for external use
    addUserMessage(content) {
        this.addMessage('user', content);
    }
    
    addAssistantMessage(content) {
        this.addMessage('assistant', content);
    }
    
    addAssistantMessageHtml(htmlContent) {
        this.addMessageHtml('assistant', htmlContent);
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.toggle('hidden', !show);
        }
    }
}

// Global instance
let chat = null;
