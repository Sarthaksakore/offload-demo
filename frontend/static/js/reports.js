// static/js/reports.js - CO2 Reports and Billing Display

// Load reports on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('reports-table')) {
        loadReports();
        calculateBilling();
    }
});

// Load all CO2 reports
async function loadReports() {
    const tableBody = document.querySelector('#reports-table tbody');
    
    if (!tableBody) return;
    
    tableBody.innerHTML = '<tr><td colspan="4"><i class="fas fa-spinner fa-spin"></i> Loading reports...</td></tr>';
    
    try {
        const response = await fetch('/api/get-reports');
        const reports = await response.json();
        
        if (reports.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4">No reports found. Run some tasks to generate reports!</td></tr>';
            return;
        }
        
        // Sort by modified date (newest first)
        reports.sort((a, b) => new Date(b.modified) - new Date(a.modified));
        
        // Build table rows
        let html = '';
        reports.forEach(report => {
            const date = new Date(report.modified);
            html += `
                <tr>
                    <td><strong>${report.filename}</strong></td>
                    <td>${formatFileSize(report.size)}</td>
                    <td>${date.toLocaleString()}</td>
                    <td>
                        <a href="/api/download-report/${report.filename}" 
                           class="btn btn-sm btn-primary" 
                           download>
                            <i class="fas fa-download"></i> Download
                        </a>
                        <button onclick="viewReport('${report.filename}')" 
                                class="btn btn-sm btn-secondary">
                            <i class="fas fa-eye"></i> Preview
                        </button>
                    </td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
        
        // Calculate total CO2 saved from all reports
        calculateTotalSavings(reports);
        
    } catch (error) {
        console.error('Error loading reports:', error);
        tableBody.innerHTML = '<tr><td colspan="4" style="color: var(--accent-color);">Error loading reports</td></tr>';
        showNotification('Failed to load reports', 'error');
    }
}

// Calculate total CO2 savings
async function calculateTotalSavings(reports) {
    let totalSaved = 0;
    let totalTasks = 0;
    
    // For demo, we'll estimate based on number of reports
    // In production, you'd parse each CSV and sum the co2_saved column
    totalTasks = reports.length;
    totalSaved = totalTasks * 5.5; // Average 5.5g saved per task (demo value)
    
    // Update dashboard if elements exist
    const savedElement = document.getElementById('dash-saved');
    const tasksElement = document.getElementById('dash-tasks');
    
    if (savedElement) {
        savedElement.textContent = totalSaved.toFixed(2);
    }
    
    if (tasksElement) {
        tasksElement.textContent = totalTasks;
    }
}

// Calculate estimated cloud billing
function calculateBilling() {
    const hoursElement = document.getElementById('bill-hours');
    const costElement = document.getElementById('bill-cost');
    
    if (!hoursElement || !costElement) return;
    
    // For demo: estimate based on localStorage or default values
    // In production, you'd track actual execution times
    
    const totalHours = parseFloat(localStorage.getItem('totalCloudHours') || '0');
    const hourlyRate = 0.05; // $0.05 per hour
    const totalCost = totalHours * hourlyRate;
    
    hoursElement.textContent = totalHours.toFixed(2);
    costElement.textContent = `$${totalCost.toFixed(2)}`;
}

// View report preview (shows first few lines)
async function viewReport(filename) {
    try {
        const response = await fetch(`/api/download-report/${filename}`);
        const text = await response.text();
        
        // Parse CSV and show first 10 rows
        const lines = text.split('\n').slice(0, 11); // Header + 10 rows
        const preview = lines.join('\n');
        
        // Create modal to show preview
        showPreviewModal(filename, preview);
        
    } catch (error) {
        console.error('Error viewing report:', error);
        showNotification('Failed to load report preview', 'error');
    }
}

// Show preview modal
function showPreviewModal(filename, content) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    
    // Create modal content
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: var(--card-bg);
        border: 2px solid var(--primary-color);
        border-radius: 15px;
        padding: 30px;
        max-width: 800px;
        max-height: 80vh;
        overflow: auto;
        box-shadow: 0 0 30px rgba(57, 255, 20, 0.3);
    `;
    
    modalContent.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="color: var(--primary-color);">📄 ${filename}</h3>
            <button onclick="this.closest('.modal-overlay').remove()" 
                    class="btn btn-secondary" 
                    style="padding: 8px 15px;">
                <i class="fas fa-times"></i> Close
            </button>
        </div>
        <pre style="background: #000; color: var(--primary-color); padding: 20px; border-radius: 8px; overflow-x: auto; font-family: var(--font-mono); font-size: 0.9em;">${escapeHtml(content)}</pre>
        <p style="margin-top: 15px; color: var(--text-muted); font-size: 0.9em;">
            <i class="fas fa-info-circle"></i> Showing first 10 rows. Download for full report.
        </p>
    `;
    
    modal.className = 'modal-overlay';
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Close on overlay click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export report data as JSON
function exportReportAsJSON() {
    // This would parse all CSVs and create a combined JSON export
    showNotification('JSON export feature coming soon!', 'info');
}