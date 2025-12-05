// map.js - World Carbon Intensity Map

// Major electricity zones with coordinates
const ZONES = [
    // India
    { code: 'IN-WE', name: 'India West (Mumbai)', lat: 19.0760, lng: 72.8777 },
    { code: 'IN-NO', name: 'India North', lat: 28.7041, lng: 77.1025 },
    { code: 'IN-SO', name: 'India South', lat: 13.0827, lng: 80.2707 },
    { code: 'IN-EA', name: 'India East', lat: 22.5726, lng: 88.3639 },
    { code: 'IN-NE', name: 'India Northeast', lat: 26.1445, lng: 91.7362 },
    
    // Europe - Sweden
    { code: 'SE-SE4', name: 'Sweden Stockholm', lat: 59.3293, lng: 18.0686 },
    { code: 'SE-SE3', name: 'Sweden South', lat: 55.6050, lng: 13.0038 },
    { code: 'SE-SE1', name: 'Sweden North', lat: 63.8258, lng: 20.2630 },
    
    // Europe - Other
    { code: 'DE', name: 'Germany', lat: 52.5200, lng: 13.4050 },
    { code: 'FR', name: 'France', lat: 48.8566, lng: 2.3522 },
    { code: 'GB', name: 'United Kingdom', lat: 51.5074, lng: -0.1278 },
    { code: 'NO-NO1', name: 'Norway Oslo', lat: 59.9139, lng: 10.7522 },
    { code: 'DK-DK1', name: 'Denmark West', lat: 56.2639, lng: 9.5018 },
    
    // USA
    { code: 'US-CAL-CISO', name: 'California', lat: 36.7783, lng: -119.4179 },
    { code: 'US-TEX-ERCO', name: 'Texas', lat: 31.9686, lng: -99.9018 },
    { code: 'US-NY-NYIS', name: 'New York', lat: 40.7128, lng: -74.0060 },
    
    // Asia-Pacific
    { code: 'JP-TK', name: 'Japan Tokyo', lat: 35.6762, lng: 139.6503 },
    { code: 'AU-NSW', name: 'Australia NSW', lat: -33.8688, lng: 151.2093 },
    { code: 'SG', name: 'Singapore', lat: 1.3521, lng: 103.8198 },
    
    // South America
    { code: 'BR-CS', name: 'Brazil Central', lat: -15.7801, lng: -47.9292 },
    
    // Africa
    { code: 'ZA', name: 'South Africa', lat: -30.5595, lng: 22.9375 }
];

let map;
let markers = [];
let carbonData = {};

// Initialize map
function initMap() {
    // Create map centered on India
    map = L.map('carbon-map').setView([20, 78], 3);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    // Load initial data
    loadMapData();
}

// Get color based on carbon intensity
function getCarbonColor(intensity) {
    if (intensity < 100) return '#22c55e'; // Green
    if (intensity < 300) return '#eab308'; // Yellow
    if (intensity < 500) return '#f97316'; // Orange
    return '#ef4444'; // Red
}

// Get status text
function getCarbonStatus(intensity) {
    if (intensity < 100) return '🟢 Excellent';
    if (intensity < 300) return '🟡 Moderate';
    if (intensity < 500) return '🟠 High';
    return '🔴 Very High';
}

// Create custom marker
function createMarker(zone, intensity) {
    const color = getCarbonColor(intensity);
    const status = getCarbonStatus(intensity);
    
    // Create circle marker
    const marker = L.circleMarker([zone.lat, zone.lng], {
        radius: 12,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(map);
    
    // Popup content
    const popupContent = `
        <div style="min-width: 200px;">
            <h4 style="margin: 0 0 10px 0;">${zone.name}</h4>
            <p style="margin: 5px 0;"><strong>Zone:</strong> ${zone.code}</p>
            <p style="margin: 5px 0;"><strong>Carbon Intensity:</strong> ${intensity.toFixed(1)} gCO₂/kWh</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> ${status}</p>
        </div>
    `;
    
    marker.bindPopup(popupContent);
    
    return marker;
}

// Load carbon data for all zones
async function loadMapData() {
    const zoneDetailsDiv = document.getElementById('zone-details');
    zoneDetailsDiv.innerHTML = '<p>Loading zone data...</p>';
    
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    let detailsHTML = '<table class="data-table"><thead><tr><th>Zone</th><th>Region</th><th>Carbon Intensity</th><th>Status</th></tr></thead><tbody>';
    
    // Fetch data for each zone
    for (const zone of ZONES) {
        try {
            // For demo, we'll use your backend API which currently supports IN-WE and SE-SE4
            // For other zones, we'll use simulated data based on typical values
            
            let intensity;
            if (zone.code === 'IN-WE' || zone.code === 'SE-SE4') {
                // Fetch real data from your backend
                const response = await fetch(`/api/carbon-intensity?region=${zone.code}`);
                const data = await response.json();
                intensity = data.carbon_intensity || 400; // Fallback
            } else {
                // Simulated data for other zones (you can replace with real API calls)
                intensity = getSimulatedCarbon(zone.code);
            }
            
            carbonData[zone.code] = intensity;
            
            // Create marker
            const marker = createMarker(zone, intensity);
            markers.push(marker);
            
            // Add to details table
            const status = getCarbonStatus(intensity);
            detailsHTML += `
                <tr>
                    <td><strong>${zone.code}</strong></td>
                    <td>${zone.name}</td>
                    <td>${intensity.toFixed(1)} gCO₂/kWh</td>
                    <td>${status}</td>
                </tr>
            `;
            
        } catch (error) {
            console.error(`Error loading data for ${zone.code}:`, error);
        }
    }
    
    detailsHTML += '</tbody></table>';
    zoneDetailsDiv.innerHTML = detailsHTML;
}

// Simulated carbon data for zones without API access
function getSimulatedCarbon(zoneCode) {
    // Typical carbon intensities for different regions
    const typicalValues = {
        // India - typically high
        'IN-NO': 700,
        'IN-SO': 650,
        'IN-EA': 750,
        'IN-NE': 600,
        
        // Sweden - very clean
        'SE-SE1': 30,
        'SE-SE3': 40,
        
        // Europe
        'DE': 350,
        'FR': 60,
        'GB': 250,
        'NO-NO1': 25,
        'DK-DK1': 180,
        
        // USA
        'US-CAL-CISO': 280,
        'US-TEX-ERCO': 450,
        'US-NY-NYIS': 320,
        
        // Asia-Pacific
        'JP-TK': 480,
        'AU-NSW': 650,
        'SG': 520,
        
        // South America
        'BR-CS': 380,
        
        // Africa
        'ZA': 880
    };
    
    return typicalValues[zoneCode] || 400;
}

// Refresh map data
function refreshMapData() {
    loadMapData();
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initMap();
});