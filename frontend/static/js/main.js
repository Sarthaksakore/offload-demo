// static/js/main.js - Common utilities and header carbon update

const API_BASE = 'http://localhost:5000';
const BACKEND_BASE = 'http://localhost:8000';

// Update header carbon value periodically
async function updateHeaderCarbon() {
    try {
        const response = await fetch(`${API_BASE}/api/carbon-intensity?region=IN-WE`);
        const data = await response.json();
        
        if (data.carbon_intensity) {
            const carbonValue = document.getElementById('header-carbon-value');
            if (carbonValue) {
                carbonValue.textContent = `${data.carbon_intensity.toFixed(1)} gCO₂/kWh`;
            }
        }
    } catch (error) {
        console.error('Error updating header carbon:', error);
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Format timestamp
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? 'var(--primary-color)' : type === 'error' ? 'var(--accent-color)' : 'var(--secondary-color)'};
        color: var(--background-dark);
        border-radius: 8px;
        font-weight: bold;
        z-index: 10000;
        animation: slideIn 0.3s ease;
        box-shadow: 0 5px 15px rgba(0,0,0,0.5);
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Update header carbon immediately
    updateHeaderCarbon();
    
    // Update every 30 seconds
    setInterval(updateHeaderCarbon, 30000);
});

// Export functions for use in other scripts
window.AppUtils = {
    formatFileSize,
    formatTimestamp,
    showNotification,
    API_BASE,
    BACKEND_BASE
};