// static/js/dashboard.js - Dashboard initialization and stats

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard if on index page
    if (document.getElementById('dash-carbon')) {
        initDashboard();
        
        // Refresh dashboard every 60 seconds
        setInterval(refreshDashboardStats, 60000);
    }
});

// Initialize dashboard
async function initDashboard() {
    await refreshDashboardStats();
    loadDashboardReports();
}

// Refresh dashboard statistics
async function refreshDashboardStats() {
    try {
        // Fetch current carbon intensity
        const response = await fetch('/api/carbon-intensity?region=IN-WE');
        const data = await response.json();
        
        if (data.carbon_intensity) {
            updateCarbonDisplay(data);
            updateBestRegion(data);
        }
    } catch (error) {
        console.error('Error refreshing dashboard stats:', error);
    }
}

// Update carbon intensity display
function updateCarbonDisplay(carbonData) {
    const carbonElement = document.getElementById('dash-carbon');
    const regionElement = document.getElementById('dash-region');
    const card = document.getElementById('live-carbon-card');
    
    if (!carbonElement) return;
    
    const ci = carbonData.carbon_intensity;
    const region = carbonData.region;
    
    // Get color based on intensity
    const color = getCarbonColor(ci);
    const status = getCarbonStatus(ci);
    
    // Update display
    carbonElement.textContent = ci.toFixed(1);
    carbonElement.style.color = color;
    carbonElement.style.textShadow = `0 0 15px ${color}`;
    
    if (regionElement) {
        regionElement.textContent = `Region: ${region} - ${status}`;
        regionElement.style.color = color;
    }
    
    // Update card border color
    if (card) {
        card.style.borderLeft = `5px solid ${color}`;
    }
}

// Update best region recommendation
async function updateBestRegion(currentData) {
    const bestElement = document.getElementById('dash-best');
    if (!bestElement) return;
    
    try {
        // Compare IN-WE and SE-SE4
        const mumbaiCI = currentData.carbon_intensity;
        
        // Fetch Stockholm data (using fixed value from your carbon_api.py)
        const stockholmCI = 50.0; // SE-SE4 fixed value
        
        let recommendation = '';
        let color = '';
        
        if (mumbaiCI < stockholmCI * 1.2) {
            // Mumbai is competitive (within 20%)
            recommendation = '🇮🇳 Mumbai (IN-WE)';
            color = getCarbonColor(mumbaiCI);
        } else {
            // Stockholm is significantly better
            recommendation = '🇸🇪 Stockholm (SE-SE4)';
            color = getCarbonColor(stockholmCI);
        }
        
        bestElement.textContent = recommendation;
        bestElement.style.color = color;
        bestElement.style.textShadow = `0 0 10px ${color}`;
        
    } catch (error) {
        console.error('Error updating best region:', error);
        bestElement.textContent = 'Calculating...';
    }
}

// Load reports summary for dashboard
async function loadDashboardReports() {
    try {
        const response = await fetch('/api/get-reports');
        const reports = await response.json();
        
        // Update tasks count
        const tasksElement = document.getElementById('dash-tasks');
        if (tasksElement) {
            tasksElement.textContent = reports.length;
        }
        
        // Calculate total CO2 saved (estimated)
        const totalSaved = reports.length * 5.5; // 5.5g average per task
        const savedElement = document.getElementById('dash-saved');
        if (savedElement) {
            savedElement.textContent = totalSaved.toFixed(2);
            savedElement.style.color = 'var(--primary-color)';
            savedElement.style.textShadow = '0 0 10px var(--primary-color)';
        }
        
    } catch (error) {
        console.error('Error loading dashboard reports:', error);
    }
}

// Get carbon color based on intensity
function getCarbonColor(intensity) {
    if (intensity < 100) return '#39FF14'; // Electric green
    if (intensity < 300) return '#FFD700'; // Gold
    if (intensity < 500) return '#FF8C00'; // Dark orange
    return '#FF073A'; // Neon red
}

// Get carbon status text
function getCarbonStatus(intensity) {
    if (intensity < 100) return '🟢 Excellent';
    if (intensity < 300) return '🟡 Moderate';
    if (intensity < 500) return '🟠 High';
    return '🔴 Very High';
}

// Animation for stat cards
function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = current.toFixed(2);
    }, 16);
}