/**
 * Camera Selector Component
 * 
 * Handles camera selection dropdown with real-time validation and updates.
 */

class CameraSelector {
    constructor(apiClient, stateManager) {
        this.api = apiClient;
        this.state = stateManager;
        this.selectElement = document.getElementById('camera-select');
        this.configSelect = document.getElementById('config-select');
        
        this.init();
    }

    /**
     * Initialize the camera selector
     */
    init() {
        if (!this.selectElement) {
            console.warn('Camera selector element not found');
            return;
        }

        this.setupEventListeners();
        this.setupStateListeners();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Listen for config changes
        if (this.configSelect) {
            this.configSelect.addEventListener('change', (e) => {
                this.handleConfigChange(e.target.value);
            });
        }

        // Listen for camera selection changes
        this.selectElement.addEventListener('change', (e) => {
            this.handleCameraChange(e.target.value);
        });

        // Real-time validation
        this.selectElement.addEventListener('blur', () => {
            this.validateSelection();
        });
    }

    /**
     * Set up state listeners
     */
    setupStateListeners() {
        // Listen for camera updates
        this.state.subscribe('cameras', (cameras) => {
            this.updateCameraList(cameras);
        });

        // Listen for loading state
        this.state.subscribe('isLoading', (isLoading) => {
            this.updateLoadingState(isLoading);
        });
    }

    /**
     * Handle configuration change
     */
    async handleConfigChange(configFile) {
        if (!configFile) {
            this.clearCameras();
            return;
        }

        try {
            this.state.setLoading(true);
            const cameras = await this.api.getCameras(configFile);
            this.state.updateCameras(cameras);
        } catch (error) {
            console.error('Failed to load cameras:', error);
            this.showError('Failed to load cameras for selected configuration');
            this.clearCameras();
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Handle camera selection change
     */
    handleCameraChange(cameraAlias) {
        if (cameraAlias) {
            this.state.set('selectedCamera', cameraAlias);
            this.clearError();
        } else {
            this.state.set('selectedCamera', null);
        }
        
        this.validateSelection();
        this.updateExtractionButton();
    }

    /**
     * Update camera list in dropdown
     */
    updateCameraList(cameras) {
        if (!this.selectElement) return;

        // Clear existing options
        this.selectElement.innerHTML = '<option value="">Select camera...</option>';
        
        if (!cameras || cameras.length === 0) {
            this.selectElement.innerHTML = '<option value="">No cameras available</option>';
            this.selectElement.disabled = true;
            return;
        }

        // Add camera options
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.alias;
            option.textContent = camera.description || camera.alias;
            option.dataset.cameraId = camera.id;
            this.selectElement.appendChild(option);
        });

        this.selectElement.disabled = false;
        this.clearError();
    }

    /**
     * Clear camera list
     */
    clearCameras() {
        if (!this.selectElement) return;

        this.selectElement.innerHTML = '<option value="">Select configuration first</option>';
        this.selectElement.disabled = true;
        this.state.set('selectedCamera', null);
    }

    /**
     * Validate current selection
     */
    validateSelection() {
        const selectedCamera = this.selectElement.value;
        const isValid = selectedCamera && selectedCamera !== '';
        
        if (!isValid && this.selectElement.value === '') {
            this.showError('Please select a camera');
        } else {
            this.clearError();
        }

        return isValid;
    }

    /**
     * Update extraction button state
     */
    updateExtractionButton() {
        const extractButton = document.getElementById('extract-button');
        if (!extractButton) return;

        const isFormValid = this.isFormReady();
        extractButton.disabled = !isFormValid;
    }

    /**
     * Check if form is ready for extraction
     */
    isFormReady() {
        const configSelected = this.configSelect && this.configSelect.value;
        const cameraSelected = this.selectElement && this.selectElement.value;
        const isConnected = this.state.get('isConnected');
        
        return configSelected && cameraSelected && isConnected;
    }

    /**
     * Update loading state
     */
    updateLoadingState(isLoading) {
        if (!this.selectElement) return;

        this.selectElement.disabled = isLoading || !this.state.get('cameras').length;
        
        if (isLoading) {
            this.selectElement.innerHTML = '<option value="">Loading cameras...</option>';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        this.clearError();
        
        const errorElement = document.createElement('div');
        errorElement.className = 'field-error';
        errorElement.textContent = message;
        errorElement.style.color = 'var(--error-color)';
        errorElement.style.fontSize = 'var(--font-size-sm)';
        errorElement.style.marginTop = 'var(--spacing-1)';
        
        this.selectElement.parentNode.appendChild(errorElement);
        this.selectElement.classList.add('error');
    }

    /**
     * Clear error message
     */
    clearError() {
        const existingError = this.selectElement.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        this.selectElement.classList.remove('error');
    }

    /**
     * Get selected camera information
     */
    getSelectedCamera() {
        const selectedValue = this.selectElement.value;
        if (!selectedValue) return null;

        const selectedOption = this.selectElement.querySelector(`option[value="${selectedValue}"]`);
        if (!selectedOption) return null;

        return {
            alias: selectedValue,
            id: selectedOption.dataset.cameraId,
            description: selectedOption.textContent
        };
    }

    /**
     * Reset to default state
     */
    reset() {
        this.selectElement.value = '';
        this.clearError();
        this.state.set('selectedCamera', null);
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CameraSelector;
}
