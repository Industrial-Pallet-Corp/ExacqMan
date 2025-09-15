/**
 * ExacqMan API Client
 * 
 * Handles all REST API communication with the ExacqMan backend server.
 * Provides a clean interface for the frontend application.
 */

class ExacqManAPI {
    constructor(baseURL = 'http://localhost:8000/api') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
    }

    /**
     * Make an HTTP request to the API
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} Response data
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new APIError(
                    errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
                    response.status,
                    errorData
                );
            }

            // Handle empty responses
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return { success: true };
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            
            // Network or other errors
            throw new APIError(
                `Network error: ${error.message}`,
                0,
                { originalError: error }
            );
        }
    }

    /**
     * Test API connection
     * @returns {Promise<boolean>} Connection status
     */
    async testConnection() {
        try {
            await this.request('/health');
            return true;
        } catch (error) {
            console.error('API connection test failed:', error);
            return false;
        }
    }

    // Configuration endpoints

    /**
     * Get available configuration files
     * @returns {Promise<Array<string>>} List of configuration file names
     */
    async getAvailableConfigs() {
        return await this.request('/configs');
    }

    /**
     * Get configuration information
     * @param {string} configFile - Configuration file path
     * @returns {Promise<Object>} Configuration info
     */
    async getConfigInfo(configFile) {
        return await this.request(`/config/${encodeURIComponent(configFile)}`);
    }

    /**
     * Get available cameras for a configuration
     * @param {string} configFile - Configuration file path
     * @returns {Promise<Array>} List of cameras
     */
    async getCameras(configFile) {
        return await this.request(`/cameras/${encodeURIComponent(configFile)}`);
    }

    // Extraction workflow

    /**
     * Start video extraction
     * @param {Object} extractRequest - Extraction parameters
     * @returns {Promise<Object>} Job information
     */
    async extractVideo(extractRequest) {
        return await this.request('/extract', {
            method: 'POST',
            body: JSON.stringify(extractRequest)
        });
    }

    /**
     * Get job status
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>} Job status
     */
    async getJobStatus(jobId) {
        return await this.request(`/status/${encodeURIComponent(jobId)}`);
    }

    // File management

    /**
     * Get list of processed videos
     * @returns {Promise<Array>} List of video files
     */
    async getProcessedVideos() {
        return await this.request('/files');
    }

    /**
     * Download a video file
     * @param {string} filename - File name
     * @returns {Promise<Blob>} File blob
     */
    async downloadVideo(filename) {
        const response = await fetch(`${this.baseURL}/download/${encodeURIComponent(filename)}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new APIError(
                errorData.detail || `Download failed: ${response.statusText}`,
                response.status,
                errorData
            );
        }

        return await response.blob();
    }

    /**
     * Delete a video file
     * @param {string} filename - File name
     * @returns {Promise<Object>} Deletion result
     */
    async deleteVideo(filename) {
        return await this.request(`/files/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
    }

    // Utility methods

    /**
     * Get download URL for a file
     * @param {string} filename - File name
     * @returns {string} Download URL
     */
    getDownloadURL(filename) {
        return `${this.baseURL}/download/${encodeURIComponent(filename)}`;
    }

    /**
     * Format file size for display
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(message, status = 0, data = {}) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }

    /**
     * Check if error is a network error
     * @returns {boolean} True if network error
     */
    isNetworkError() {
        return this.status === 0;
    }

    /**
     * Check if error is a client error (4xx)
     * @returns {boolean} True if client error
     */
    isClientError() {
        return this.status >= 400 && this.status < 500;
    }

    /**
     * Check if error is a server error (5xx)
     * @returns {boolean} True if server error
     */
    isServerError() {
        return this.status >= 500;
    }

    /**
     * Get user-friendly error message
     * @returns {string} User-friendly message
     */
    getUserMessage() {
        if (this.isNetworkError()) {
            return 'Unable to connect to server. Please check your connection and try again.';
        }
        
        if (this.isClientError()) {
            if (this.status === 404) {
                return 'The requested resource was not found.';
            }
            if (this.status === 400) {
                return 'Invalid request. Please check your input and try again.';
            }
            return 'There was an error with your request. Please try again.';
        }
        
        if (this.isServerError()) {
            return 'Server error occurred. Please try again later.';
        }
        
        return this.message || 'An unexpected error occurred.';
    }
}

// Export for ES6 module usage
export { ExacqManAPI, APIError };
