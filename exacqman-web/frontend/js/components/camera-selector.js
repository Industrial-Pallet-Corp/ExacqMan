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
        console.log('CameraSelector init - selectElement:', this.selectElement);
        if (!this.selectElement) {
            console.warn('Camera selector element not found');
            return;
        }

        this.setupEventListeners();
        this.setupStateListeners();
        console.log('CameraSelector initialized successfully');
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
        console.log('[DEBUG] CameraSelector handleConfigChange called with:', configFile);
        if (!configFile) {
            this.clearCameras();
            return;
        }

        try {
            this.state.setLoading(true);
            const cameras = await this.api.getCameras(configFile);
            console.log('[DEBUG] CameraSelector handleConfigChange - loaded cameras:', cameras);
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
            
            // Save preference to localStorage
            window.LocalStorageService.savePreference('camera', cameraAlias);
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

        // Preserve current selection
        const currentValue = this.selectElement.value;
        console.log('[DEBUG] CameraSelector updateCameraList - preserving value:', currentValue);
        console.log('[DEBUG] CameraSelector updateCameraList - cameras received:', cameras);

        // Clear existing options
        this.selectElement.innerHTML = '<option value="">Select camera...</option>';
        
        if (!cameras || cameras.length === 0) {
            console.log('[DEBUG] CameraSelector updateCameraList - no cameras available');
            this.selectElement.innerHTML = '<option value="">No cameras available</option>';
            this.selectElement.disabled = true;
            return;
        }

        console.log('[DEBUG] CameraSelector updateCameraList - adding', cameras.length, 'camera options');
        console.log('[DEBUG] CameraSelector updateCameraList - cameras array:', cameras);

        // Add camera options
        cameras.forEach((camera, index) => {
            console.log(`[DEBUG] CameraSelector updateCameraList - adding camera ${index}:`, camera);
            const option = document.createElement('option');
            option.value = camera.alias;
            option.textContent = camera.description || camera.alias;
            option.dataset.cameraId = camera.id;
            this.selectElement.appendChild(option);
            console.log(`[DEBUG] CameraSelector updateCameraList - added option:`, option);
        });

        this.selectElement.disabled = false;
        this.selectElement.required = true;
        
        console.log('[DEBUG] CameraSelector updateCameraList - final dropdown options:', this.selectElement.options.length);
        console.log('[DEBUG] CameraSelector updateCameraList - dropdown HTML:', this.selectElement.innerHTML);
        
        // Try to load saved preference first
        const savedCamera = window.LocalStorageService.loadPreference('camera', null);
        const preferredCamera = savedCamera && cameras.some(camera => camera.alias === savedCamera) ? savedCamera : null;
        
        // Auto-select if only one camera
        if (cameras.length === 1) {
            this.selectElement.value = cameras[0].alias;
            this.handleCameraChange(cameras[0].alias);
            console.log('Auto-selected camera:', cameras[0].alias);
        }
        // Use saved preference if available and valid
        else if (preferredCamera) {
            this.selectElement.value = preferredCamera;
            this.handleCameraChange(preferredCamera);
            console.log('Restored saved camera preference:', preferredCamera);
        }
        // Restore current selection if it was valid (fallback)
        else if (currentValue && cameras.some(camera => camera.alias === currentValue)) {
            this.selectElement.value = currentValue;
            console.log('CameraSelector updateCameraList - restored value:', currentValue);
        }
        
        this.clearError();
    }

    /**
     * Clear camera list
     */
    clearCameras() {
        if (!this.selectElement) return;

        this.selectElement.innerHTML = '<option value="">Waiting for configuration...</option>';
        this.selectElement.disabled = true;
        this.selectElement.required = false;
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
        
        return configSelected && cameraSelected;
    }

    /**
     * Update loading state
     */
    updateLoadingState(isLoading) {
        if (!this.selectElement) return;

        this.selectElement.disabled = isLoading || !this.state.get('cameras').length;
        
        if (isLoading) {
            // Preserve current selection when showing loading state
            const currentValue = this.selectElement.value;
            this.selectElement.innerHTML = '<option value="">Waiting for configuration...</option>';
            if (currentValue) {
                // Add the current selection back as a temporary option
                const option = document.createElement('option');
                option.value = currentValue;
                option.textContent = currentValue;
                option.selected = true;
                this.selectElement.appendChild(option);
            }
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
        console.log('CameraSelector getSelectedCamera - selectElement:', this.selectElement);
        if (!this.selectElement) {
            console.log('CameraSelector getSelectedCamera - no selectElement');
            return null;
        }
        
        const selectedValue = this.selectElement.value;
        console.log('CameraSelector getSelectedCamera - selectedValue:', selectedValue);
        if (!selectedValue) {
            console.log('CameraSelector getSelectedCamera - no selectedValue');
            return null;
        }

        const selectedOption = this.selectElement.querySelector(`option[value="${selectedValue}"]`);
        console.log('CameraSelector getSelectedCamera - selectedOption:', selectedOption);
        if (!selectedOption) {
            console.log('CameraSelector getSelectedCamera - no selectedOption');
            return null;
        }

        const result = {
            alias: selectedValue,
            id: selectedOption.dataset.cameraId,
            description: selectedOption.textContent
        };
        console.log('CameraSelector getSelectedCamera - result:', result);
        return result;
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

// Export for ES6 module usage
export default CameraSelector;
