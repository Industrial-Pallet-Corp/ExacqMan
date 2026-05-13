/**
 * Job Status Component
 * 
 * Handles job status display, progress tracking, and real-time updates.
 */

class JobStatus {
    constructor(apiClient, stateManager) {
        this.api = apiClient;
        this.state = stateManager;
        this.jobListElement = document.getElementById('job-list');
        this.jobPoller = null;
        
        this.init();
    }

    /**
     * Initialize the job status component
     */
    init() {
        if (!this.jobListElement) {
            console.warn('Job list element not found');
            return;
        }

        this.setupStateListeners();
        this.updateDisplay();
    }

    /**
     * Set up state listeners
     */
    setupStateListeners() {
        // Listen for active jobs changes
        this.state.subscribe('activeJobs', (jobs) => {
            this.updateDisplay();
        });

        // Listen for job history changes
        this.state.subscribe('jobHistory', (history) => {
            this.updateDisplay();
        });
    }

    /**
     * Update job display
     */
    updateDisplay() {
        if (!this.jobListElement) return;

        const activeJobs = this.state.getActiveJobs();
        const historyJobs = this.state.get('jobHistory') || [];
        
        // Combine active and recent history jobs (last 5)
        const recentHistory = historyJobs.slice(-5);
        const allJobs = [...activeJobs, ...recentHistory];
        
        if (allJobs.length === 0) {
            this.jobListElement.innerHTML = '<div class="no-jobs">No jobs found</div>';
            return;
        }

        // Sort by creation time (newest first)
        allJobs.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        
        this.jobListElement.innerHTML = allJobs.map(job => this.createJobElement(job)).join('');
    }

    /**
     * Create job element HTML
     */
    createJobElement(job) {
        const status = job.status || 'unknown';
        const progress = job.progress || 0;
        const message = job.message || '';
        const createdAt = this.formatDate(job.createdAt);
        const completedAt = job.completedAt ? this.formatDate(job.completedAt) : null;
        
        // Determine status-specific styling
        const statusClass = this.getStatusClass(status);
        const progressBar = this.createProgressBar(progress, status);
        const actions = this.createJobActions(job);
        
        return `
            <div class="job-item ${statusClass}" data-job-id="${job.id}">
                <div class="job-header">
                    <div class="job-info">
                        <span class="job-created">${createdAt}</span>
                    </div>
                    <div class="job-status">
                        <span class="job-status-badge ${statusClass}">${this.formatStatus(status)}</span>
                        ${actions}
                    </div>
                </div>
                
                ${progressBar}
                
                <div class="job-details">
                    <div class="job-message">${message}</div>
                    ${this.createJobMetadata(job)}
                </div>
                
                ${completedAt ? `<div class="job-completed">Completed: ${completedAt}</div>` : ''}
            </div>
        `;
    }

    /**
     * Create progress bar HTML
     */
    createProgressBar(progress, status) {
        if (status === 'completed' || status === 'failed') {
            return ''; // No progress bar for completed/failed jobs
        }
        
        return `
            <div class="job-progress">
                <div class="job-progress-bar" style="width: ${progress}%"></div>
                <div class="job-progress-text">${progress}%</div>
            </div>
        `;
    }

    /**
     * Create job actions HTML
     */
    createJobActions(job) {
        const actions = [];
        
        if (job.status === 'completed' && job.result?.filename) {
            actions.push(`
                <button class="btn btn-sm btn-primary" onclick="app.handleFileDownload('${job.result.filename}')">
                    Download
                </button>
            `);
        }
        
        return actions.length > 0 ? `<div class="job-actions">${actions.join('')}</div>` : '';
    }

    /**
     * Create job metadata HTML
     */
    createJobMetadata(job) {
        const metadata = [];
        
        if (job.request?.camera_alias) {
            metadata.push(`Camera: ${job.request.camera_alias}`);
        }
        
        if (job.request?.timelapse_multiplier) {
            metadata.push(`Speed: ${job.request.timelapse_multiplier}x`);
        }
        
        if (job.request?.start_datetime && job.request?.end_datetime) {
            const start = new Date(job.request.start_datetime);
            const end = new Date(job.request.end_datetime);
            const duration = this.formatDuration(end - start);
            metadata.push(`Duration: ${duration}`);
        }
        
        if (job.result?.filename) {
            metadata.push(`File: ${job.result.filename}`);
        }
        
        if (job.result?.file_size) {
            metadata.push(`Size: ${this.formatFileSize(job.result.file_size)}`);
        }
        
        return metadata.length > 0 ? 
            `<div class="job-metadata">${metadata.join(' • ')}</div>` : '';
    }

    /**
     * Get status class for styling
     */
    getStatusClass(status) {
        switch (status) {
            case 'queued': return 'queued';
            case 'processing': return 'processing';
            case 'completed': return 'completed';
            case 'failed': return 'failed';
            default: return 'unknown';
        }
    }

    /**
     * Format status for display
     */
    formatStatus(status) {
        switch (status) {
            case 'queued': return 'Queued';
            case 'processing': return 'Processing';
            case 'completed': return 'Completed';
            case 'failed': return 'Failed';
            default: return 'Unknown';
        }
    }

    /**
     * Format job ID for display
     */
    formatJobId(jobId) {
        if (!jobId) return 'Unknown';
        return jobId.substring(0, 8) + '...';
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        // Show relative time for recent dates
        if (diff < 60 * 1000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 60 * 60 * 1000) { // Less than 1 hour
            const minutes = Math.floor(diff / (60 * 1000));
            return `${minutes}m ago`;
        } else if (diff < 24 * 60 * 60 * 1000) { // Less than 1 day
            const hours = Math.floor(diff / (60 * 60 * 1000));
            return `${hours}h ago`;
        } else {
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    /**
     * Format duration for display
     */
    formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Start polling for job status
     */
    startPolling(jobId) {
        if (this.jobPoller) {
            this.jobPoller.stop();
        }
        
        this.jobPoller = new JobPoller(this.api, (jobId, status) => {
            this.state.updateJobStatus(jobId, status);
            
        });
        
        this.jobPoller.start(jobId);
    }

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.jobPoller) {
            this.jobPoller.stop();
            this.jobPoller = null;
        }
    }

    /**
     * Remove job from display
     */
    removeJob(jobId) {
        this.state.removeJob(jobId);
    }

    /**
     * Clear all completed jobs
     */
    clearCompleted() {
        const activeJobs = this.state.getActiveJobs();
        const completedJobs = activeJobs.filter(job => job.status === 'completed');
        
        completedJobs.forEach(job => {
            this.state.removeJob(job.id);
        });
    }

    /**
     * Clear all failed jobs
     */
    clearFailed() {
        const activeJobs = this.state.getActiveJobs();
        const failedJobs = activeJobs.filter(job => job.status === 'failed');
        
        failedJobs.forEach(job => {
            this.state.removeJob(job.id);
        });
    }

    /**
     * Get job statistics
     */
    getStats() {
        const activeJobs = this.state.getActiveJobs();
        const historyJobs = this.state.get('jobHistory') || [];
        
        return {
            active: activeJobs.length,
            completed: historyJobs.filter(job => job.status === 'completed').length,
            failed: historyJobs.filter(job => job.status === 'failed').length,
            total: activeJobs.length + historyJobs.length
        };
    }
}

/**
 * Job Poller Class
 */
class JobPoller {
    constructor(apiClient, onUpdate) {
        this.api = apiClient;
        this.onUpdate = onUpdate;
        this.activeJobs = new Set();
        this.intervalId = null;
        this.pollInterval = 1000; // 1 second for real-time progress updates
    }

    start(jobId) {
        this.activeJobs.add(jobId);
        
        if (!this.intervalId) {
            this.intervalId = setInterval(() => this.pollJobs(), this.pollInterval);
        }
    }

    stop(jobId) {
        if (jobId) {
            this.activeJobs.delete(jobId);
        } else {
            this.activeJobs.clear();
        }
        
        if (this.activeJobs.size === 0 && this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async pollJobs() {
        const jobs = Array.from(this.activeJobs);
        
        for (const jobId of jobs) {
            try {
                const status = await this.api.getJobStatus(jobId);
                this.onUpdate(jobId, status);
                
                // Stop polling for completed/failed jobs
                if (status.status === 'completed' || status.status === 'failed') {
                    this.stop(jobId);
                }
            } catch (error) {
                console.error(`Failed to poll job ${jobId}:`, error);
                // Continue polling other jobs even if one fails
            }
        }
    }
}

// Export for ES6 module usage
export default JobStatus;
