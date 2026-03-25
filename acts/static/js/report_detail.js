/**
 * Report Detail View - JavaScript Functionality
 * Handles progress bar initialization, map setup, and form interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize progress bars with dynamic widths from data-width attributes
    initializeProgressBars();
    
    // Initialize map if coordinates available
    initializeMap();
});

/**
 * Set progress bar widths from data-width attributes
 */
function initializeProgressBars() {
    document.querySelectorAll('.progress-bar[data-width]').forEach(function(bar) {
        const width = bar.getAttribute('data-width');
        bar.style.width = width + '%';
    });
}

/**
 * Initialize Leaflet map with report location
 */
function initializeMap() {
    const mapElement = document.getElementById('detail-map');
    if (!mapElement) return;
    
    // Map initialization happens here - coordinates are injected by Django template
    // This function is called after DOM is ready
}

/**
 * Update report status
 * @param {string} status - New status to update to
 */
function updateStatus(status) {
    alert('Status update to ' + status + ' would be sent to backend');
    const badge = document.getElementById('status-badge');
    if (badge) {
        badge.innerHTML = status.toUpperCase();
    }
}

/**
 * Save routing notes
 */
function saveRoutingNotes() {
    const routingNotesElement = document.getElementById('routing-notes');
    if (!routingNotesElement) return;
    
    const notes = routingNotesElement.value;
    alert('Routing notes saved: ' + notes.substring(0, 50) + '...');
}

/**
 * Submit override form
 * @param {Event} event - Form submit event
 */
function submitOverride(event) {
    event.preventDefault();
    
    const category = document.getElementById('override-category').value;
    const location = document.getElementById('override-location').value;
    const status = document.getElementById('override-status').value;
    const reason = document.getElementById('override-reason').value;
    
    alert(`Override submitted:\nCategory: ${category}\nLocation: ${location}\nStatus: ${status}\nReason: ${reason}`);
}

/**
 * Submit flag for senior review
 */
function submitFlag() {
    const reasonElement = document.getElementById('flag-reason');
    if (!reasonElement) return;
    
    const reason = reasonElement.value;
    alert('Flag submitted for senior review: ' + reason);
}
