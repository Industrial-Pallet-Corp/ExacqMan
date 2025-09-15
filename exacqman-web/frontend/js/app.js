/**
 * ExacqMan Web Application
 * 
 * Main application entry point and orchestration.
 * Coordinates between UI components, state management, and API client.
 */

import { ExacqManAPI, APIError } from './api.js';
import AppState from './utils/state.js';
import CameraSelector from './components/camera-selector.js';
import DateTimePicker from './components/datetime-picker.js';
import MultiplierSelector from './components/multiplier-selector.js';
import JobStatus from './components/job-status.js';
import FileBrowser from './components/file-browser.js';

class ExacqManApp {
    constructor() {
        this.api = new ExacqManAPI();
        this.state = new AppState();
        this.jobPoller = null;
        this.isInitialized = false;
        
        // Initialize components
        this.cameraSelector = null;
        this.dateTimePicker = null;
        this.multiplierSelector = null;
        this.jobStatus = null;
        this.fileBrowser = null;
        
        // Bind methods to preserve context
        this.handleConfigChange = this.handleConfigChange.bind(this);
        this.handleExtractionSubmit = this.handleExtractionSubmit.bind(this);
        this.handleFileRefresh = this.handleFileRefresh.bind(this);
        this.handleFileDownload = this.handleFileDownload.bind(this);
        this.handleFileDelete = this.handleFileDelete.bind(this);
        this.removeJob = this.removeJob.bind(this);
        
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            console.log('Initializing ExacqMan Web Application...');
            
            // Initialize components
            this.initializeComponents();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Set up state listeners
            this.setupStateListeners();
            
            // Test API connection
            await this.testConnection();
            
            // Load initial data
            await this.loadInitialData();
            
            this.isInitialized = true;
            console.log('Application initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.showError('Failed to initialize application. Please refresh the page.');
        }
    }

    /**
     * Initialize UI components
     */
    initializeComponents() {
        this.cameraSelector = new CameraSelector(this.api, this.state);
        this.dateTimePicker = new DateTimePicker(this.state);
        this.multiplierSelector = new MultiplierSelector(this.state);
        this.jobStatus = new JobStatus(this.api, this.state);
        this.fileBrowser = new FileBrowser(this.api, this.state);
    }

    /**
     * Set up DOM event listeners
     */
    setupEventListeners() {
        // Configuration change
        const configSelect = document.getElementById('config-select');
        if (configSelect) {
            configSelect.addEventListener('change', this.handleConfigChange);
        }

        // Extraction form submission
        const extractionForm = document.getElementById('extraction-form');
        if (extractionForm) {
            extractionForm.addEventListener('submit', this.handleExtractionSubmit);
        }

        // File refresh button
        const refreshFilesBtn = document.getElementById('refresh-files');
        if (refreshFilesBtn) {
            refreshFilesBtn.addEventListener('click', this.handleFileRefresh);
        }

        // Set default datetime values
        this.setDefaultDateTimeValues();
    }

    /**
     * Set up state change listeners
     */
    setupStateListeners() {
        // Connection status
        this.state.subscribe('isConnected', (isConnected) => {
            this.updateConnectionStatus(isConnected);
        });

        // Loading state
        this.state.subscribe('isLoading', (isLoading) => {
            this.updateLoadingState(isLoading);
        });

        // Error state
        this.state.subscribe('currentError', (error) => {
            if (error) {
                this.showError(error.getUserMessage ? error.getUserMessage() : error.message);
            }
        });

        // Active jobs
        this.state.subscribe('activeJobs', (jobs) => {
            this.updateJobDisplay();
        });

        // Processed videos
        this.state.subscribe('processedVideos', (videos) => {
            this.updateFileDisplay();
        });
    }

    /**
     * Test API connection
     */
    async testConnection() {
        try {
            this.state.setLoading(true);
            const isConnected = await this.api.testConnection();
            this.state.setConnectionStatus(isConnected);
            
            if (!isConnected) {
                throw new Error('Unable to connect to server');
            }
            
        } catch (error) {
            console.error('Connection test failed:', error);
            this.state.setConnectionStatus(false);
            throw error;
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Load initial application data
     */
    async loadInitialData() {
        try {
            this.state.setLoading(true);
            
            // Load configuration files from API
            const configFiles = await this.api.getAvailableConfigs();
            const configs = configFiles.map(file => ({
                name: file,
                path: file
            }));
            
            this.state.updateConfigs(configs);
            this.populateConfigSelect(configs);
            
            // Load processed videos
            await this.loadProcessedVideos();
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            throw error;
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Set default datetime values
     */
    setDefaultDateTimeValues() {
        const startInput = document.getElementById('start-datetime');
        const endInput = document.getElementById('end-datetime');
        
        if (startInput && endInput) {
            startInput.value = this.state.get('defaultStartTime');
            endInput.value = this.state.get('defaultEndTime');
        }
    }

    /**
     * Handle configuration file change
     */
    async handleConfigChange(event) {
        const configFile = event.target.value;
        
        if (!configFile) {
            this.state.updateCameras([]);
            this.state.updateServers({});
            this.state.setCurrentConfig(null);
            this.populateCameraSelect([]);
            this.populateServerSelect({});
            return;
        }

        try {
            this.state.setLoading(true);
            this.state.setCurrentConfig(configFile);
            
            // Load cameras and servers for selected config
            const [cameras, configInfo] = await Promise.all([
                this.api.getCameras(configFile),
                this.api.getConfigInfo(configFile)
            ]);
            
            this.state.updateCameras(cameras);
            this.state.updateServers(configInfo.servers || {});
            
            this.populateCameraSelect(cameras);
            this.populateServerSelect(configInfo.servers || {});
            
        } catch (error) {
            console.error('Failed to load configuration:', error);
            this.showError('Failed to load configuration. Please try again.');
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Handle extraction form submission
     */
    async handleExtractionSubmit(event) {
        event.preventDefault();
        
        try {
            // Validate form using components
            if (!this.validateForm()) {
                return;
            }

            this.state.setLoading(true);
            
            // Get form data from components
            const formData = this.getFormData();
            console.log('Form data being sent:', formData);
            
            // Submit extraction request
            const response = await this.api.extractVideo(formData);
            
            if (response.success && response.data?.job_id) {
                // Add job to tracking
                this.state.addJob(response.data.job_id, {
                    status: 'queued',
                    message: 'Job queued for processing',
                    progress: 0,
                    request: formData
                });
                
                // Start polling for job status
                this.jobStatus.startPolling(response.data.job_id);
                
                this.showSuccess('Video extraction started successfully');
                
                // Reset form
                this.resetExtractionForm();
                
            } else {
                throw new Error('Invalid response from server');
            }
            
        } catch (error) {
            console.error('Extraction failed:', error);
            this.showError(error.getUserMessage ? error.getUserMessage() : 'Failed to start extraction');
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Handle file refresh
     */
    async handleFileRefresh() {
        if (this.fileBrowser) {
            this.fileBrowser.loadFiles();
        } else {
            await this.loadProcessedVideos();
        }
    }

    /**
     * Handle file download
     */
    async handleFileDownload(filename) {
        try {
            const url = this.api.getDownloadURL(filename);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('Download failed:', error);
            this.showError('Failed to download file');
        }
    }

    /**
     * Handle file deletion
     */
    async handleFileDelete(filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
            return;
        }

        try {
            this.state.setLoading(true);
            await this.api.deleteVideo(filename);
            this.state.removeProcessedVideo(filename);
            this.showSuccess('File deleted successfully');
        } catch (error) {
            console.error('Delete failed:', error);
            this.showError('Failed to delete file');
        } finally {
            this.state.setLoading(false);
        }
    }

    // Helper methods

    /**
     * Validate form using components
     */
    validateForm() {
        const configValid = this.state.get('currentConfig');
        const cameraValid = this.cameraSelector?.validateSelection();
        const datetimeValid = this.dateTimePicker?.validateBoth();
        const multiplierValid = this.multiplierSelector?.validateSelection();
        
        return configValid && cameraValid && datetimeValid && multiplierValid;
    }

    /**
     * Get form data from components
     */
    getFormData() {
        const configFile = this.state.get('currentConfig');
        const cameraInfo = this.cameraSelector?.getSelectedCamera();
        const datetimeValues = this.dateTimePicker?.getValues();
        const multiplier = this.multiplierSelector?.getValue();
        const server = document.getElementById('server-select')?.value || null;

        console.log('Form data components:', {
            configFile,
            cameraInfo,
            datetimeValues,
            multiplier,
            server
        });

        return {
            camera_alias: cameraInfo?.alias,
            start_datetime: datetimeValues?.start_datetime,
            end_datetime: datetimeValues?.end_datetime,
            timelapse_multiplier: multiplier,
            config_file: configFile,
            server: server
        };
    }


    /**
     * Load processed videos
     */
    async loadProcessedVideos() {
        try {
            const videos = await this.api.getProcessedVideos();
            this.state.updateProcessedVideos(videos);
        } catch (error) {
            console.error('Failed to load videos:', error);
            this.showError('Failed to load video files');
        }
    }


    // UI update methods

    /**
     * Update connection status display
     */
    updateConnectionStatus(isConnected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = isConnected ? 'Connected' : 'Disconnected';
            statusElement.className = `status-indicator ${isConnected ? 'connected' : 'error'}`;
        }
    }

    /**
     * Update loading state
     */
    updateLoadingState(isLoading) {
        const extractButton = document.getElementById('extract-button');
        if (extractButton) {
            extractButton.disabled = isLoading;
            const btnText = extractButton.querySelector('.btn-text');
            const btnLoading = extractButton.querySelector('.btn-loading');
            
            if (btnText && btnLoading) {
                btnText.style.display = isLoading ? 'none' : 'inline';
                btnLoading.style.display = isLoading ? 'inline' : 'none';
            }
        }
    }

    /**
     * Populate configuration select
     */
    populateConfigSelect(configs) {
        const select = document.getElementById('config-select');
        if (!select) return;
        
        select.innerHTML = '<option value="">Select configuration...</option>';
        configs.forEach(config => {
            const option = document.createElement('option');
            option.value = config.path;
            option.textContent = config.name;
            select.appendChild(option);
        });
        select.disabled = false;
    }

    /**
     * Populate camera select
     */
    populateCameraSelect(cameras) {
        const select = document.getElementById('camera-select');
        if (!select) return;
        
        select.innerHTML = '<option value="">Select camera...</option>';
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.alias;
            option.textContent = camera.description || camera.alias;
            select.appendChild(option);
        });
        select.disabled = cameras.length === 0;
    }

    /**
     * Populate server select
     */
    populateServerSelect(servers) {
        const select = document.getElementById('server-select');
        if (!select) return;
        
        select.innerHTML = '<option value="">Auto-detect</option>';
        Object.entries(servers).forEach(([name, ip]) => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = `${name} (${ip})`;
            select.appendChild(option);
        });
        select.disabled = Object.keys(servers).length === 0;
    }

    /**
     * Update job display
     */
    updateJobDisplay() {
        const jobList = document.getElementById('job-list');
        if (!jobList) return;
        
        const jobs = this.state.getActiveJobs();
        
        if (jobs.length === 0) {
            jobList.innerHTML = '<div class="no-jobs">No active jobs</div>';
            return;
        }
        
        jobList.innerHTML = jobs.map(job => this.createJobElement(job)).join('');
    }

    /**
     * Create job element HTML
     */
    createJobElement(job) {
        return `
            <div class="job-item ${job.status}">
                <div class="job-header">
                    <span class="job-id">${job.id}</span>
                    <span class="job-status ${job.status}">${job.status}</span>
                </div>
                <div class="job-progress">
                    <div class="job-progress-bar" style="width: ${job.progress || 0}%"></div>
                </div>
                <div class="job-message">${job.message || ''}</div>
            </div>
        `;
    }

    /**
     * Update file display
     */
    updateFileDisplay() {
        const filesList = document.getElementById('files-list');
        if (!filesList) return;
        
        const videos = this.state.get('processedVideos');
        
        if (videos.length === 0) {
            filesList.innerHTML = '<div class="no-files">No processed videos found</div>';
            return;
        }
        
        filesList.innerHTML = videos.map(video => this.createFileElement(video)).join('');
    }

    /**
     * Create file element HTML
     */
    createFileElement(video) {
        const fileSize = this.api.formatFileSize(video.size);
        const createdDate = this.api.formatDate(video.created_at);
        
        return `
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">${video.filename}</div>
                    <div class="file-meta">${video.camera_alias || 'Unknown'}</div>
                    <div class="file-meta">${video.timelapse_multiplier || 'N/A'}x</div>
                    <div class="file-meta">${fileSize}</div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-secondary" onclick="app.handleFileDownload('${video.filename}')">
                        Download
                    </button>
                    <button class="btn btn-danger" onclick="app.handleFileDelete('${video.filename}')">
                        Delete
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Remove job from tracking
     */
    removeJob(jobId) {
        this.state.removeJob(jobId);
    }

    /**
     * Reset extraction form
     */
    resetExtractionForm() {
        // Reset components
        this.cameraSelector?.reset();
        this.dateTimePicker?.reset();
        this.multiplierSelector?.reset();
        
        // Reset form
        const form = document.getElementById('extraction-form');
        if (form) {
            form.reset();
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showToast(message, 'success');
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showToast(message, 'error');
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => container.removeChild(toast), 300);
        }, 5000);
    }
}


// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ExacqManApp();
});
