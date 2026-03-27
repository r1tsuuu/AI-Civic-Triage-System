/**
 * Report Detail View — JavaScript
 *
 * Responsibilities:
 *  1. Initialize progress bars (data-width → inline style)
 *  2. Initialize the read-only incident detail map
 *  3. Edit Report modal — Leaflet click-to-pin map + urgency slider
 */

document.addEventListener('DOMContentLoaded', function () {
    initProgressBars();
    initDetailMap();
    initEditModal();
    initUrgencySlider();
});

// ── 1. Progress bars ──────────────────────────────────────────────────────────
function initProgressBars() {
    document.querySelectorAll('.progress-bar[data-width]').forEach(function (bar) {
        bar.style.width = bar.getAttribute('data-width') + '%';
    });
}

// ── 2. Read-only incident map (existing detail-map div) ───────────────────────
function initDetailMap() {
    const el = document.getElementById('detail-map');
    if (!el) return;

    const lat = parseFloat(el.getAttribute('data-latitude'));
    const lng = parseFloat(el.getAttribute('data-longitude'));
    if (isNaN(lat) || isNaN(lng)) return;

    const detailMap = L.map('detail-map').setView([lat, lng], 15);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
    }).addTo(detailMap);

    L.circleMarker([lat, lng], {
        radius: 9,
        fillColor: '#1A56DB',
        color: '#fff',
        weight: 2,
        fillOpacity: 0.85,
    }).addTo(detailMap)
      .bindPopup(el.getAttribute('data-barangay') || 'Reported location')
      .openPopup();
}

// ── 3. Edit Report modal — click-to-pin Leaflet map ───────────────────────────
let editMap    = null;   // Leaflet map instance (created once on first open)
let editMarker = null;   // Draggable pin

function initEditModal() {
    const modal = document.getElementById('editReportModal');
    if (!modal) return;

    // Bootstrap fires 'shown.bs.modal' AFTER the CSS transition completes,
    // so Leaflet can correctly measure the container dimensions.
    modal.addEventListener('shown.bs.modal', function () {
        const mapEl = document.getElementById('edit-map');
        if (!mapEl) return;

        if (editMap) {
            // Map already exists — just tell Leaflet the container may have resized
            editMap.invalidateSize();
            return;
        }

        const defaultLat = parseFloat(mapEl.getAttribute('data-lat')) || 13.9420;
        const defaultLng = parseFloat(mapEl.getAttribute('data-lng')) || 121.1628;

        editMap = L.map('edit-map').setView([defaultLat, defaultLng], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
        }).addTo(editMap);

        // Place the initial pin (draggable)
        editMarker = L.marker([defaultLat, defaultLng], { draggable: true })
            .addTo(editMap)
            .bindPopup('Drag or click to reposition')
            .openPopup();

        // Update coords when marker is dragged
        editMarker.on('dragend', function (e) {
            const ll = e.target.getLatLng();
            pinLocation(ll.lat, ll.lng);
        });

        // Click anywhere on the map to drop the pin
        editMap.on('click', function (e) {
            editMarker.setLatLng(e.latlng);
            pinLocation(e.latlng.lat, e.latlng.lng);
        });
    });
}

/**
 * Update the hidden lat/lng inputs and show a brief confirmation popup.
 * @param {number} lat
 * @param {number} lng
 */
function pinLocation(lat, lng) {
    const latInput = document.getElementById('edit-lat');
    const lngInput = document.getElementById('edit-lng');
    if (latInput) latInput.value = lat.toFixed(6);
    if (lngInput) lngInput.value = lng.toFixed(6);

    if (editMarker) {
        editMarker
            .bindPopup(lat.toFixed(5) + ', ' + lng.toFixed(5))
            .openPopup();
    }
}

// ── 4. Urgency score range slider live display ────────────────────────────────
function initUrgencySlider() {
    const slider  = document.getElementById('edit-urgency');
    const display = document.getElementById('urgency-display');
    if (!slider || !display) return;

    slider.addEventListener('input', function () {
        display.textContent = this.value;

        // Colour the number by severity bracket
        display.className = 'fw-bold';
        const v = parseInt(this.value, 10);
        if (v >= 75)      display.classList.add('text-danger');
        else if (v >= 50) display.classList.add('text-warning');
        else              display.classList.add('text-success');
    });

    // Trigger once on load so the initial colour is correct
    slider.dispatchEvent(new Event('input'));
}

// ── CSRF helper ───────────────────────────────────────────────────────────────
function getCsrfToken() {
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.trim().slice('csrftoken='.length)) : '';
}

// ── 5. Save Routing Notes via AJAX ────────────────────────────────────────────
function saveRoutingNotes() {
    const textarea = document.getElementById('routing-notes');
    const btn      = document.getElementById('save-notes-btn');
    const indicator = document.getElementById('notes-saved-indicator');
    if (!textarea) return;

    const saveUrl = textarea.getAttribute('data-save-url');
    if (!saveUrl) return;

    const originalHTML = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Saving…';
    }

    fetch(saveUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken(),
        },
        body: 'routing_notes=' + encodeURIComponent(textarea.value),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            if (indicator) {
                indicator.textContent = '✓ Saved';
                indicator.className = 'text-success small';
                setTimeout(function() { indicator.textContent = ''; }, 3000);
            }
            if (btn) {
                btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Saved';
                btn.className = btn.className.replace('btn-primary', 'btn-success');
                setTimeout(function() {
                    btn.innerHTML = originalHTML;
                    btn.className = btn.className.replace('btn-success', 'btn-primary');
                    btn.disabled = false;
                }, 2000);
            }
        }
    })
    .catch(function(err) {
        console.error('saveRoutingNotes failed:', err);
        if (btn) {
            btn.innerHTML = originalHTML;
            btn.disabled = false;
        }
        if (indicator) {
            indicator.textContent = '⚠ Save failed';
            indicator.className = 'text-danger small';
        }
    });
}

function submitFlag() {
    const textarea = document.getElementById('flag-reason');
    const feedback = document.getElementById('flag-feedback');
    const btn = document.getElementById('flag-submit-btn');
    const modal = document.getElementById('flagModal');
    if (!textarea || !modal) return;

    const reason = textarea.value.trim();
    if (!reason) {
        if (feedback) {
            feedback.textContent = 'Please enter a reason before submitting.';
            feedback.className = 'mb-2 small text-danger';
        }
        return;
    }

    const flagUrl = modal.getAttribute('data-flag-url');
    if (!flagUrl) return;

    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Submitting…'; }

    fetch(flagUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken(),
        },
        body: 'reason=' + encodeURIComponent(reason),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            if (feedback) {
                feedback.textContent = '✓ Flagged — report returned to review queue.';
                feedback.className = 'mb-2 small text-success';
            }
            setTimeout(function() { window.location.reload(); }, 1200);
        } else {
            if (feedback) {
                feedback.textContent = data.error || 'Flag failed.';
                feedback.className = 'mb-2 small text-danger';
            }
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-flag me-1"></i>Submit Flag'; }
        }
    })
    .catch(function(err) {
        console.error('submitFlag failed:', err);
        if (feedback) {
            feedback.textContent = '⚠ Network error — try again.';
            feedback.className = 'mb-2 small text-danger';
        }
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-flag me-1"></i>Submit Flag'; }
    });
}
