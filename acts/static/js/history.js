/**
 * History View - JavaScript Functionality
 * Handles filter form enhancement and export functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeFilters();
    initializeExport();
    enhanceTimeline();
});

/**
 * Initialize filter form enhancements
 */
function initializeFilters() {
    const filterForm = document.getElementById('filter-form');
    if (!filterForm) return;

    // Auto-focus date fields
    const dateFields = filterForm.querySelectorAll('input[type="date"]');
    dateFields.forEach(field => {
        field.addEventListener('change', function() {
            // Validate date range
            const dateFrom = document.getElementById('date_from').value;
            const dateTo = document.getElementById('date_to').value;
            
            if (dateFrom && dateTo && dateFrom > dateTo) {
                alert('Start date cannot be after end date');
                this.value = '';
            }
        });
    });

    // Report ID field - allow partial match highlighting
    const reportIdField = document.getElementById('report_id');
    if (reportIdField) {
        reportIdField.addEventListener('input', function() {
            // Clear selection highlights on input
            clearReportHighlights();
        });
    }
}

/**
 * Initialize export button with filter preservation
 */
function initializeExport() {
    const exportBtn = document.getElementById('export-btn');
    if (!exportBtn) return;

    exportBtn.addEventListener('click', function(e) {
        const dateFrom = document.getElementById('date_from').value;
        const dateTo = document.getElementById('date_to').value;
        const reportId = document.getElementById('report_id').value;
        
        // Build query string
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (reportId) params.append('report_id', reportId);
        
        // Update href with current filters
        const baseUrl = this.getAttribute('href').split('?')[0];
        this.href = baseUrl + (params.toString() ? '?' + params.toString() : '');
    });
}

/**
 * Enhance timeline with interactivity
 */
function enhanceTimeline() {
    const timelineItems = document.querySelectorAll('.timeline-item');
    
    timelineItems.forEach(item => {
        // Add hover effect
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(5px)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
        
        // Make report link clickable on entire item
        const reportLink = item.querySelector('.report-link');
        if (reportLink) {
            item.style.cursor = 'pointer';
            item.addEventListener('click', function(e) {
                // Don't redirect if clicking on a link that's already handled
                if (e.target.tagName !== 'A') {
                    reportLink.click();
                }
            });
        }
    });
}

/**
 * Clear report ID highlights
 */
function clearReportHighlights() {
    document.querySelectorAll('.report-link.highlight').forEach(link => {
        link.classList.remove('highlight');
    });
}

/**
 * Export filtered results as CSV
 */
function exportAsCSV() {
    const dateFrom = document.getElementById('date_from').value;
    const dateTo = document.getElementById('date_to').value;
    const reportId = document.getElementById('report_id').value;
    
    const params = new URLSearchParams();
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (reportId) params.append('report_id', reportId);
    
    // Trigger download
    const url = `/dashboard/history/export/?${params.toString()}`;
    window.location.href = url;
}
