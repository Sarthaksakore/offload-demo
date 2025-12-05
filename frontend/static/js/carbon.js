// static/js/carbon.js - Carbon intensity monitoring with Chart.js

let historicalChart = null;
let liveChart = null;
let carbonHistory = [];

// Initialize charts
function initCharts() {
    // Initialize historical chart if on carbon page
    const historicalCanvas = document.getElementById('historicalCarbonChart');
    if (historicalCanvas) {
        const ctx = historicalCanvas.getContext('2d');
        historicalChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Carbon Intensity (gCO₂/kWh)',
                    data: [],
                    borderColor: 'rgba(57, 255, 20, 1)',
                    backgroundColor: 'rgba(57, 255, 20, 0.2)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: 'rgba(57, 255, 20, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: '#f1f5f9',
                            font: { size: 14 }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Carbon Intensity Over Time',
                        color: '#00BFFF',
                        font: { size: 16, weight: 'bold' }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(148, 163, 184, 0.1)' }
                    },
                    x: {
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(148, 163, 184, 0.1)' }
                    }
                }
            }
        });
        
        // Load initial data
        loadHistoricalData('IN-WE');
    }
    
    // Initialize live chart if on dashboard
    const liveCanvas = document.getElementById('liveCarbonChart');
    if (liveCanvas) {
        const ctx = liveCanvas.getContext('2d');
        liveChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Live Carbon Intensity',
                    data: [],
                    borderColor: 'rgba(0, 191, 255, 1)',
                    backgroundColor: 'rgba(0, 191, 255, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: { color: '#f1f5f9' }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(148, 163, 184, 0.1)' }
                    },
                    x: {
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(148, 163, 184, 0.1)' }
                    }
                }
            }
        });
        
        // Start live updates
        updateLiveChart();
        setInterval(updateLiveChart, 60000); // Update every minute
    }
}

// Load historical data for a region
async function loadHistoricalData(region) {
    try {
        // Since we don't have historical API, we'll simulate by fetching current data
        // and creating a trend over the last 24 hours
        const response = await fetch(`/api/carbon-intensity?region=${region}`);
        const data = await response.json();
        
        if (data.carbon_intensity) {
            // Simulate 24 hours of data (one point per hour)
            const currentValue = data.carbon_intensity;
            const labels = [];
            const values = [];
            
            for (let i = 23; i >= 0; i--) {
                const hour = new Date();
                hour.setHours(hour.getHours() - i);
                labels.push(hour.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
                
                // Add some random variation (±10%) to simulate realistic data
                const variation = (Math.random() - 0.5) * 0.2;
                values.push(currentValue * (1 + variation));
            }
            
            if (historicalChart) {
                historicalChart.data.labels = labels;
                historicalChart.data.datasets[0].data = values;
                historicalChart.update();
            }
            
            // Update current display
            updateCurrentCarbonDisplay(data);
        }
    } catch (error) {
        console.error('Error loading historical data:', error);
        showNotification('Failed to load historical data', 'error');
    }
}

// Update current carbon display
function updateCurrentCarbonDisplay(data) {
    const displayDiv = document.getElementById('current-carbon-display');
    if (!displayDiv) return;
    
    const ci = data.carbon_intensity;
    const region = data.region;
    const status = getCarbonStatus(ci);
    const color = getCarbonColor(ci);
    
    displayDiv.innerHTML = `
        <div style="padding: 20px;">
            <div style="font-size: 4em; font-weight: bold; color: ${color}; text-shadow: 0 0 10px ${color};">
                ${ci.toFixed(1)}
            </div>
            <div style="font-size: 1.2em; margin-top: 10px; color: #94a3b8;">
                gCO₂eq/kWh
            </div>
            <div style="font-size: 1.5em; margin-top: 20px; color: ${color};">
                ${status}
            </div>
            <div style="margin-top: 10px; color: #94a3b8;">
                Region: ${region}
            </div>
        </div>
    `;
}

// Update live chart on dashboard
async function updateLiveChart() {
    try {
        const response = await fetch('/api/carbon-intensity?region=IN-WE');
        const data = await response.json();
        
        if (data.carbon_intensity && liveChart) {
            const now = new Date().toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            
            // Add new data point
            liveChart.data.labels.push(now);
            liveChart.data.datasets[0].data.push(data.carbon_intensity);
            
            // Keep only last 20 points
            if (liveChart.data.labels.length > 20) {
                liveChart.data.labels.shift();
                liveChart.data.datasets[0].data.shift();
            }
            
            liveChart.update();
        }
        
        // Update dashboard stats
        updateDashboardStats(data);
        
    } catch (error) {
        console.error('Error updating live chart:', error);
    }
}

// Update dashboard statistics
function updateDashboardStats(carbonData) {
    // Update carbon intensity
    const carbonElement = document.getElementById('dash-carbon');
    const regionElement = document.getElementById('dash-region');
    
    if (carbonElement && carbonData.carbon_intensity) {
        const ci = carbonData.carbon_intensity;
        const color = getCarbonColor(ci);
        carbonElement.textContent = ci.toFixed(1);
        carbonElement.style.color = color;
        carbonElement.style.textShadow = `0 0 10px ${color}`;
        
        if (regionElement) {
            regionElement.textContent = `Region: ${carbonData.region}`;
        }
    }
    
    // Update best region recommendation
    const bestElement = document.getElementById('dash-best');
    if (bestElement) {
        // Simple logic: IN-WE vs SE-SE4
        if (carbonData.carbon_intensity < 300) {
            bestElement.textContent = carbonData.region;
        } else {
            bestElement.textContent = 'SE-SE4 (Stockholm)';
        }
    }
}

// Get carbon status text
function getCarbonStatus(intensity) {
    if (intensity < 100) return '🟢 Excellent - Very Clean Grid';
    if (intensity < 300) return '🟡 Good - Moderate Carbon';
    if (intensity < 500) return '🟠 High - Consider Delaying';
    return '🔴 Very High - Avoid Tasks';
}

// Get carbon color
function getCarbonColor(intensity) {
    if (intensity < 100) return '#39FF14';
    if (intensity < 300) return '#FFD700';
    if (intensity < 500) return '#FF8C00';
    return '#FF073A';
}

// Refresh carbon data
function refreshCarbon() {
    const region = document.getElementById('chart-region')?.value || 'IN-WE';
    loadHistoricalData(region);
    showNotification('Carbon data refreshed', 'success');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
});