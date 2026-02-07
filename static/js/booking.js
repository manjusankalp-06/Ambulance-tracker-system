// --- 1. INITIALIZE MAP (Google Maps Style) ---
const map = L.map('map', { zoomControl: false }).setView([12.9716, 77.5946], 13);

// Using 'Voyager' tiles - this is the "Normal" clean map look you asked for
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CartoDB'
}).addTo(map);

L.control.zoom({ position: 'bottomright' }).addTo(map);

let pickupMarker, hospitalMarker;
let clickCount = 0;

// --- 2. MAP CLICK LOGIC ---
map.on('click', function(e) {
    const { lat, lng } = e.latlng;
    const coordString = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;

    if (clickCount === 0) {
        if (pickupMarker) map.removeLayer(pickupMarker);
        pickupMarker = L.marker([lat, lng], {
            icon: L.icon({
                iconUrl: 'https://cdn-icons-png.flaticon.com/512/6877/6877471.png',
                iconSize: [35, 35], iconAnchor: [17, 35]
            })
        }).addTo(map).bindPopup("Pickup Location").openPopup();
        
        document.getElementById('p-stat').className = 'pin-status active';
        document.getElementById('pick_addr').value = coordString;
        clickCount = 1;
    } else {
        if (hospitalMarker) map.removeLayer(hospitalMarker);
        hospitalMarker = L.marker([lat, lng], {
            icon: L.icon({
                iconUrl: 'https://cdn-icons-png.flaticon.com/512/3757/3757965.png',
                iconSize: [35, 35], iconAnchor: [17, 35]
            })
        }).addTo(map).bindPopup("Target Hospital").openPopup();
        
        document.getElementById('h-stat').className = 'pin-status active';
        document.getElementById('dest_addr').value = coordString;
        clickCount = 0;
    }
});

// --- 3. GPS BUTTON LOGIC ---
document.getElementById('get-location').addEventListener('click', function() {
    const btn = this;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Locating...';
    
    if (!navigator.geolocation) {
        alert("Geolocation not supported");
        return;
    }

    navigator.geolocation.getCurrentPosition((pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        map.setView([lat, lng], 16);
        
        if (pickupMarker) map.removeLayer(pickupMarker);
        pickupMarker = L.marker([lat, lng]).addTo(map).bindPopup("You are here").openPopup();
        
        document.getElementById('pick_addr').value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        document.getElementById('p-stat').className = 'pin-status active';
        btn.innerHTML = '<i class="fas fa-location-arrow"></i> Use My GPS';
        clickCount = 1; // Next click will be hospital
    }, (err) => {
        alert("Could not get location. Please enable GPS.");
        btn.innerHTML = '<i class="fas fa-location-arrow"></i> Use My GPS';
    }, { enableHighAccuracy: true });
});