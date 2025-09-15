/**
 * File Browser Component
 * 
 * Handles file display, sorting, filtering, and bulk operations for processed videos.
 */

class FileBrowser {
    constructor(apiClient, stateManager) {
        this.api = apiClient;
        this.state = stateManager;
        this.filesListElement = document.getElementById('files-list');
        this.refreshButton = document.getElementById('refresh-files');
        
        // Filter elements
        this.dateFromInput = null;
        this.dateToInput = null;
        this.cameraFilterSelect = null;
        this.filenameSearchInput = null;
        this.clearFiltersButton = null;
        
        // State
        this.files = [];
        this.filteredFiles = [];
        this.selectedFiles = new Set();
        this.sortColumn = 'created_at';
        this.sortDirection = 'desc';
        
        this.init();
    }

    /**
     * Initialize the file browser
     */
    init() {
        if (!this.filesListElement) {
            console.warn('File browser element not found');
            return;
        }

        this.createFilterControls();
        this.setupEventListeners();
        this.setupStateListeners();
        this.loadFiles();
    }

    /**
     * Create filter controls
     */
    createFilterControls() {
        const filesPanel = document.getElementById('files-panel');
        if (!filesPanel) return;

        // Find the files header
        const filesHeader = filesPanel.querySelector('.files-header');
        if (!filesHeader) return;

        // Create filter container
        const filterContainer = document.createElement('div');
        filterContainer.className = 'file-filters';
        filterContainer.innerHTML = `
            <div class="filter-row">
                <div class="filter-group">
                    <label for="date-from">From Date:</label>
                    <input type="date" id="date-from" class="form-control filter-input">
                </div>
                <div class="filter-group">
                    <label for="date-to">To Date:</label>
                    <input type="date" id="date-to" class="form-control filter-input">
                </div>
                <div class="filter-group">
                    <label for="camera-filter">Camera:</label>
                    <select id="camera-filter" class="form-control filter-input">
                        <option value="">All Cameras</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="filename-search">Search:</label>
                    <input type="text" id="filename-search" class="form-control filter-input" placeholder="Search filenames...">
                </div>
                <div class="filter-group">
                    <button id="clear-filters" class="btn btn-secondary">Clear Filters</button>
                </div>
            </div>
        `;

        // Insert after files header
        filesHeader.insertAdjacentElement('afterend', filterContainer);

        // Store references to filter elements
        this.dateFromInput = document.getElementById('date-from');
        this.dateToInput = document.getElementById('date-to');
        this.cameraFilterSelect = document.getElementById('camera-filter');
        this.filenameSearchInput = document.getElementById('filename-search');
        this.clearFiltersButton = document.getElementById('clear-filters');
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Refresh button
        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', () => {
                this.loadFiles();
            });
        }

        // Filter inputs
        if (this.dateFromInput) {
            this.dateFromInput.addEventListener('change', () => this.applyFilters());
        }
        if (this.dateToInput) {
            this.dateToInput.addEventListener('change', () => this.applyFilters());
        }
        if (this.cameraFilterSelect) {
            this.cameraFilterSelect.addEventListener('change', () => this.applyFilters());
        }
        if (this.filenameSearchInput) {
            this.filenameSearchInput.addEventListener('input', () => this.applyFilters());
        }
        if (this.clearFiltersButton) {
            this.clearFiltersButton.addEventListener('click', () => this.clearFilters());
        }
    }

    /**
     * Set up state listeners
     */
    setupStateListeners() {
        // Listen for processed videos updates
        this.state.subscribe('processedVideos', (videos) => {
            this.files = videos || [];
            this.applyFilters();
            this.updateCameraFilter();
        });

        // Listen for job completion to auto-refresh
        this.state.subscribe('activeJobs', (jobs) => {
            // Check if any jobs just completed
            const completedJobs = jobs.filter(job => job.status === 'completed');
            if (completedJobs.length > 0) {
                // Auto-refresh after a short delay
                setTimeout(() => this.loadFiles(), 2000);
            }
        });
    }

    /**
     * Load files from API
     */
    async loadFiles() {
        try {
            this.state.setLoading(true);
            const files = await this.api.getProcessedVideos();
            this.state.updateProcessedVideos(files);
        } catch (error) {
            console.error('Failed to load files:', error);
            this.showError('Failed to load video files');
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Apply filters to files
     */
    applyFilters() {
        let filtered = [...this.files];

        // Date range filter
        const fromDate = this.dateFromInput?.value;
        const toDate = this.dateToInput?.value;
        
        if (fromDate) {
            const from = new Date(fromDate);
            filtered = filtered.filter(file => new Date(file.created_at) >= from);
        }
        
        if (toDate) {
            const to = new Date(toDate);
            to.setHours(23, 59, 59, 999); // End of day
            filtered = filtered.filter(file => new Date(file.created_at) <= to);
        }

        // Camera filter
        const selectedCamera = this.cameraFilterSelect?.value;
        if (selectedCamera) {
            filtered = filtered.filter(file => file.camera_alias === selectedCamera);
        }

        // Filename search
        const searchTerm = this.filenameSearchInput?.value.toLowerCase();
        if (searchTerm) {
            filtered = filtered.filter(file => 
                file.filename.toLowerCase().includes(searchTerm)
            );
        }

        this.filteredFiles = filtered;
        this.sortFiles();
        this.updateDisplay();
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        if (this.dateFromInput) this.dateFromInput.value = '';
        if (this.dateToInput) this.dateToInput.value = '';
        if (this.cameraFilterSelect) this.cameraFilterSelect.value = '';
        if (this.filenameSearchInput) this.filenameSearchInput.value = '';
        
        this.applyFilters();
    }

    /**
     * Update camera filter options
     */
    updateCameraFilter() {
        if (!this.cameraFilterSelect) return;

        // Get unique cameras from files
        const cameras = [...new Set(this.files.map(file => file.camera_alias).filter(Boolean))];
        
        // Clear existing options except "All Cameras"
        this.cameraFilterSelect.innerHTML = '<option value="">All Cameras</option>';
        
        // Add camera options
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera;
            option.textContent = camera;
            this.cameraFilterSelect.appendChild(option);
        });
    }

    /**
     * Sort files by current column and direction
     */
    sortFiles() {
        this.filteredFiles.sort((a, b) => {
            let aVal = a[this.sortColumn];
            let bVal = b[this.sortColumn];

            // Handle different data types
            if (this.sortColumn === 'created_at') {
                aVal = new Date(aVal);
                bVal = new Date(bVal);
            } else if (this.sortColumn === 'size') {
                aVal = parseInt(aVal) || 0;
                bVal = parseInt(bVal) || 0;
            } else {
                aVal = String(aVal || '').toLowerCase();
                bVal = String(bVal || '').toLowerCase();
            }

            if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }

    /**
     * Handle column header click for sorting
     */
    handleSort(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        
        this.sortFiles();
        this.updateDisplay();
    }

    /**
     * Update file display
     */
    updateDisplay() {
        if (!this.filesListElement) return;

        if (this.filteredFiles.length === 0) {
            this.filesListElement.innerHTML = '<div class="no-files">No files found</div>';
            return;
        }

        // Create table header
        const tableHTML = `
            <div class="file-table">
                <div class="file-table-header">
                    <div class="file-table-row">
                        <div class="file-table-cell file-checkbox">
                            <input type="checkbox" id="select-all" class="file-checkbox-input">
                        </div>
                        <div class="file-table-cell file-filename sortable" data-column="filename">
                            Filename <span class="sort-indicator"></span>
                        </div>
                        <div class="file-table-cell file-size sortable" data-column="size">
                            Size <span class="sort-indicator"></span>
                        </div>
                        <div class="file-table-cell file-camera sortable" data-column="camera_alias">
                            Camera <span class="sort-indicator"></span>
                        </div>
                        <div class="file-table-cell file-date sortable" data-column="created_at">
                            Date Created <span class="sort-indicator"></span>
                        </div>
                        <div class="file-table-cell file-actions">Actions</div>
                    </div>
                </div>
                <div class="file-table-body">
                    ${this.filteredFiles.map(file => this.createFileRow(file)).join('')}
                </div>
            </div>
            <div class="file-table-footer">
                <div class="file-selection-info">
                    <span id="selection-count">0 files selected</span>
                </div>
                <div class="file-bulk-actions">
                    <button id="bulk-download" class="btn btn-secondary" disabled>
                        Download Selected
                    </button>
                    <button id="bulk-delete" class="btn btn-danger" disabled>
                        Delete Selected
                    </button>
                </div>
            </div>
        `;

        this.filesListElement.innerHTML = tableHTML;

        // Set up event listeners for new elements
        this.setupTableEventListeners();
        this.updateSortIndicators();
    }

    /**
     * Create file row HTML
     */
    createFileRow(file) {
        const isSelected = this.selectedFiles.has(file.filename);
        const fileSize = this.api.formatFileSize(file.size);
        const createdDate = this.api.formatDate(file.created_at);
        
        return `
            <div class="file-table-row ${isSelected ? 'selected' : ''}" data-filename="${file.filename}">
                <div class="file-table-cell file-checkbox">
                    <input type="checkbox" class="file-checkbox-input" ${isSelected ? 'checked' : ''} 
                           data-filename="${file.filename}">
                </div>
                <div class="file-table-cell file-filename">
                    <span class="filename-text">${file.filename}</span>
                </div>
                <div class="file-table-cell file-size">
                    ${fileSize}
                </div>
                <div class="file-table-cell file-camera">
                    ${file.camera_alias || 'Unknown'}
                </div>
                <div class="file-table-cell file-date">
                    ${createdDate}
                </div>
                <div class="file-table-cell file-actions">
                    <button class="btn btn-sm btn-secondary download-btn" data-filename="${file.filename}">
                        Download
                    </button>
                    <button class="btn btn-sm btn-danger delete-btn" data-filename="${file.filename}">
                        Delete
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Set up table event listeners
     */
    setupTableEventListeners() {
        // Sortable column headers
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', (e) => {
                const column = e.currentTarget.dataset.column;
                this.handleSort(column);
            });
        });

        // Select all checkbox
        const selectAllCheckbox = document.getElementById('select-all');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                this.handleSelectAll(e.target.checked);
            });
        }

        // Individual file checkboxes
        document.querySelectorAll('.file-checkbox-input[data-filename]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const filename = e.target.dataset.filename;
                this.handleFileSelection(filename, e.target.checked);
            });
        });

        // Download buttons
        document.querySelectorAll('.download-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filename = e.target.dataset.filename;
                this.handleDownload(filename);
            });
        });

        // Delete buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filename = e.target.dataset.filename;
                this.handleDelete(filename);
            });
        });

        // Bulk actions
        const bulkDownloadBtn = document.getElementById('bulk-download');
        const bulkDeleteBtn = document.getElementById('bulk-delete');
        
        if (bulkDownloadBtn) {
            bulkDownloadBtn.addEventListener('click', () => this.handleBulkDownload());
        }
        if (bulkDeleteBtn) {
            bulkDeleteBtn.addEventListener('click', () => this.handleBulkDelete());
        }
    }

    /**
     * Update sort indicators
     */
    updateSortIndicators() {
        document.querySelectorAll('.sort-indicator').forEach(indicator => {
            indicator.textContent = '';
        });

        const activeColumn = document.querySelector(`[data-column="${this.sortColumn}"] .sort-indicator`);
        if (activeColumn) {
            activeColumn.textContent = this.sortDirection === 'asc' ? '↑' : '↓';
        }
    }

    /**
     * Handle select all checkbox
     */
    handleSelectAll(checked) {
        if (checked) {
            this.filteredFiles.forEach(file => {
                this.selectedFiles.add(file.filename);
            });
        } else {
            this.selectedFiles.clear();
        }
        
        this.updateSelectionDisplay();
        this.updateBulkActions();
    }

    /**
     * Handle individual file selection
     */
    handleFileSelection(filename, selected) {
        if (selected) {
            this.selectedFiles.add(filename);
        } else {
            this.selectedFiles.delete(filename);
        }
        
        this.updateSelectionDisplay();
        this.updateBulkActions();
    }

    /**
     * Update selection display
     */
    updateSelectionDisplay() {
        const selectionCount = document.getElementById('selection-count');
        if (selectionCount) {
            const count = this.selectedFiles.size;
            selectionCount.textContent = `${count} file${count !== 1 ? 's' : ''} selected`;
        }
    }

    /**
     * Update bulk action buttons
     */
    updateBulkActions() {
        const hasSelection = this.selectedFiles.size > 0;
        const bulkDownloadBtn = document.getElementById('bulk-download');
        const bulkDeleteBtn = document.getElementById('bulk-delete');
        
        if (bulkDownloadBtn) bulkDownloadBtn.disabled = !hasSelection;
        if (bulkDeleteBtn) bulkDeleteBtn.disabled = !hasSelection;
    }

    /**
     * Handle individual file download
     */
    handleDownload(filename) {
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
     * Handle individual file deletion
     */
    async handleDelete(filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
            return;
        }

        try {
            this.state.setLoading(true);
            await this.api.deleteVideo(filename);
            this.state.removeProcessedVideo(filename);
            this.selectedFiles.delete(filename);
            this.updateSelectionDisplay();
            this.updateBulkActions();
            this.showSuccess('File deleted successfully');
        } catch (error) {
            console.error('Delete failed:', error);
            this.showError('Failed to delete file');
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Handle bulk download
     */
    async handleBulkDownload() {
        const selectedFilenames = Array.from(this.selectedFiles);
        if (selectedFilenames.length === 0) return;

        try {
            // For now, download files individually
            // In a real implementation, you'd create a ZIP file on the server
            for (const filename of selectedFilenames) {
                this.handleDownload(filename);
                // Small delay between downloads
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        } catch (error) {
            console.error('Bulk download failed:', error);
            this.showError('Failed to download some files');
        }
    }

    /**
     * Handle bulk deletion
     */
    async handleBulkDelete() {
        const selectedFilenames = Array.from(this.selectedFiles);
        if (selectedFilenames.length === 0) return;

        if (!confirm(`Are you sure you want to delete ${selectedFilenames.length} file(s)?`)) {
            return;
        }

        try {
            this.state.setLoading(true);
            
            // Delete files one by one
            for (const filename of selectedFilenames) {
                await this.api.deleteVideo(filename);
                this.state.removeProcessedVideo(filename);
            }
            
            this.selectedFiles.clear();
            this.updateSelectionDisplay();
            this.updateBulkActions();
            this.showSuccess(`${selectedFilenames.length} file(s) deleted successfully`);
        } catch (error) {
            console.error('Bulk delete failed:', error);
            this.showError('Failed to delete some files');
        } finally {
            this.state.setLoading(false);
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        // Use the app's toast system if available
        if (window.app && window.app.showError) {
            window.app.showError(message);
        } else {
            console.error(message);
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        // Use the app's toast system if available
        if (window.app && window.app.showSuccess) {
            window.app.showSuccess(message);
        } else {
            console.log(message);
        }
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FileBrowser;
}
