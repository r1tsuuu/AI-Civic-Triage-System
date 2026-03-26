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

// ── Misc stubs called by inline onclick in the template ───────────────────────
function saveRoutingNotes() {
    const el = document.getElementById('routing-notes');
    if (!el) return;
    // Routing notes are saved server-side; this stub prevents JS errors
    // if the button is wired to this function by older template code.
}

function submitFlag() {
    const el = document.getElementById('flag-reason');
    if (!el) return;
    // Flag modal — backend endpoint not yet implemented; no-op stub.
}
