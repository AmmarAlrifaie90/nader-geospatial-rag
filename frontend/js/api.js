/**
 * API Client for Geospatial RAG
 */
class ApiClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    setBaseUrl(url) {
        this.baseUrl = url.replace(/\/$/, '');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            const response = await fetch(url, {
                headers: { 'Content-Type': 'application/json' },
                ...options
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    async healthCheck() {
        return this.request('/api/health');
    }

    async query(queryText, options = {}) {
        // Use the new agent endpoint that supports spatial analysis
        const payload = {
            query: queryText,
            max_results: options.maxResults || 500,
        };
        
        // Include current data if provided (for analysis on filtered data)
        if (options.currentData) {
            payload.data = options.currentData;
        }
        
        return this.request('/api/agent', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }
    
    async runAnalysisOnData(analysisKey, data, clusterDistanceKm = null) {
        // Run analysis on provided data (from current filtered table)
        const payload = {
            analysis_key: analysisKey,
            data: data
        };
        
        if (clusterDistanceKm !== null) {
            payload.cluster_distance_km = clusterDistanceKm;
        }
        
        return this.request('/api/analysis/run', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    // Legacy query endpoint (without analysis suggestions)
    async queryLegacy(queryText, options = {}) {
        return this.request('/api/query', {
            method: 'POST',
            body: JSON.stringify({
                query: queryText,
                include_visualization: true,
                max_results: options.maxResults || 500,
            }),
        });
    }

    async exportData(queryText, format = 'geojson') {
        return this.request('/api/export', {
            method: 'POST',
            body: JSON.stringify({ query: queryText, format }),
        });
    }

    getDownloadUrl(filename) {
        return `${this.baseUrl}/api/export/download/${filename}`;
    }

    // ML Prediction endpoints
    async mlStatus() {
        return this.request('/api/ml/status');
    }

    async mlPredict(queryText) {
        return this.request('/api/ml/predict', {
            method: 'POST',
            body: JSON.stringify({ query: queryText }),
        });
    }

    async mlPredictData(data) {
        return this.request('/api/ml/predict-data', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // Prospectivity Prediction endpoints
    async prospectivityStatus() {
        return this.request('/api/prospectivity/status');
    }

    async prospectivityFormFields() {
        return this.request('/api/prospectivity/form-fields');
    }

    async prospectivityGeologyAtPoint(lng, lat) {
        return this.request(`/api/prospectivity/geology-at-point?lng=${lng}&lat=${lat}`);
    }

    async prospectivityDistancesAtPoint(lng, lat) {
        return this.request(`/api/prospectivity/distances-at-point?lng=${lng}&lat=${lat}`);
    }

    async prospectivityGeologyPolygons() {
        return this.request('/api/prospectivity/geology-polygons');
    }

    async prospectivityPredict(data) {
        return this.request('/api/prospectivity/predict', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // Voice Processing endpoints
    async voiceStatus() {
        return this.request('/api/voice/status');
    }

    async voiceArabic(audioBase64, audioFormat = 'wav', voice = 'ar-XA-Wavenet-B') {
        return this.request('/api/voice/arabic', {
            method: 'POST',
            body: JSON.stringify({
                audio_base64: audioBase64,
                audio_format: audioFormat,
                voice: voice,
                return_audio: true
            }),
        });
    }

    async voiceTranscribe(audioBase64, audioFormat = 'wav') {
        return this.request('/api/voice/arabic/transcribe', {
            method: 'POST',
            body: JSON.stringify({
                audio_base64: audioBase64,
                audio_format: audioFormat
            }),
        });
    }

    async voiceRespond(englishText, voice = 'ar-XA-Wavenet-B') {
        return this.request(`/api/voice/arabic/respond?english_text=${encodeURIComponent(englishText)}&voice=${voice}`, {
            method: 'POST'
        });
    }
}

// Global instance
const api = new ApiClient();
