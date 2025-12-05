// static/js/task.js - Task upload, execution, and log display

let selectedFile = null;
let uploadedFilename = null;

// Initialize drag and drop
document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    if (uploadArea && fileInput) {
        // Click to upload
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
        
        // File input change
        fileInput.addEventListener('change', handleFileSelect);
    }
});

// Drag over handler
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.style.borderColor = 'var(--primary-color)';
    e.currentTarget.style.background = 'rgba(57, 255, 20, 0.1)';
}

// Drag leave handler
function handleDragLeave(e) {
    e.currentTarget.style.borderColor = '';
    e.currentTarget.style.background = '';
}

// Drop handler
function handleDrop(e) {
    e.preventDefault();
    handleDragLeave(e);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

// File select handler
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

// Handle selected file
function handleFile(file) {
    if (!file.name.endsWith('.zip')) {
        showNotification('Please select a ZIP file', 'error');
        return;
    }
    
    selectedFile = file;
    
    // Show file info
    const fileInfoCard = document.getElementById('file-info-card');
    const fileInfo = document.getElementById('file-info');
    
    fileInfo.innerHTML = `
        <div style="padding: 15px; background: rgba(57, 255, 20, 0.1); border-radius: 8px; border-left: 4px solid var(--primary-color);">
            <p><strong>📁 Filename:</strong> ${file.name}</p>
            <p><strong>📦 Size:</strong> ${formatFileSize(file.size)}</p>
            <p><strong>📅 Modified:</strong> ${new Date(file.lastModified).toLocaleString()}</p>
        </div>
    `;
    
    fileInfoCard.style.display = 'block';
    showNotification('File selected successfully', 'success');
}

// Upload task file to server
async function uploadTaskFile() {
    if (!selectedFile) {
        showNotification('Please select a file first', 'error');
        return null;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
        const response = await fetch('/api/upload-task', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            uploadedFilename = data.filename;
            return data;
        } else {
            throw new Error(data.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

// Run uploaded task
async function runTask() {
    const runBtn = document.getElementById('run-task-btn');
    const statusCard = document.getElementById('task-status-card');
    const statusDiv = document.getElementById('task-status');
    
    // Show status card
    statusCard.style.display = 'block';
    
    // Disable button
    runBtn.disabled = true;
    runBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    
    // Clear previous logs
    statusDiv.innerHTML = '<div class="log-message">⏳ Uploading task file...</div>';
    
    try {
        // Step 1: Upload file
        const uploadResult = await uploadTaskFile();
        addLog(`✅ File uploaded: ${uploadResult.filename}`);
        addLog(`📦 Size: ${formatFileSize(uploadResult.size)}`);
        addLog('');
        
        // Step 2: Execute task
        runBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Executing Task...';
        addLog('🚀 Starting task execution...');
        addLog('⏱️  This may take a few moments...');
        addLog('');
        
        const response = await fetch('/api/run-task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: uploadedFilename })
        });
        
        const result = await response.json();
        
        if (result.success) {
            addLog('✅ Task completed successfully!');
            addLog('');
            addLog('📄 Output Logs:');
            addLog('─'.repeat(50));
            
            // Display logs from output
            if (result.logs && result.logs.length > 0) {
                result.logs.forEach(log => {
                    addLog(`📂 ${log.filename}:`);
                    addLog(log.content);
                    addLog('');
                });
            } else {
                addLog('No logs found in output');
            }
            
            addLog('─'.repeat(50));
            
            // Show download button
            const downloadDiv = document.getElementById('output-download');
            const downloadLink = document.getElementById('download-link');
            downloadLink.href = `/api/download-output/${result.output_file}`;
            downloadDiv.style.display = 'block';
            
            showNotification('Task completed successfully!', 'success');
            
            // Save CO2 report
            saveCarbonReport();
            
        } else {
            throw new Error(result.error || 'Task execution failed');
        }
        
    } catch (error) {
        console.error('Task error:', error);
        addLog('');
        addLog(`❌ Error: ${error.message}`);
        showNotification('Task execution failed', 'error');
    }
    
    // Re-enable button
    runBtn.disabled = false;
    runBtn.innerHTML = '<i class="fas fa-rocket"></i> Execute Task';
}

// Add log message
function addLog(message) {
    const statusDiv = document.getElementById('task-status');
    const logLine = document.createElement('div');
    logLine.className = 'log-message';
    logLine.textContent = message;
    statusDiv.appendChild(logLine);
    
    // Auto-scroll to bottom
    statusDiv.scrollTop = statusDiv.scrollHeight;
}

// Save carbon report to CSV
async function saveCarbonReport() {
    try {
        // Get current carbon data
        const response = await fetch('/api/carbon-intensity?region=IN-WE');
        const carbonData = await response.json();
        
        // Calculate estimated values (simplified for demo)
        const executionTime = Math.random() * 100 + 50; // 50-150 seconds
        const powerWatts = 65; // Laptop average
        const energyKwh = (powerWatts * executionTime) / (3600 * 1000);
        const co2Grams = energyKwh * (carbonData.carbon_intensity || 700);
        const co2Saved = Math.random() * 10; // Random savings for demo
        
        const reportData = {
            task_name: selectedFile ? selectedFile.name : 'unknown',
            region: carbonData.region || 'IN-WE',
            carbon_intensity: carbonData.carbon_intensity || 0,
            execution_time: executionTime.toFixed(2),
            energy_kwh: energyKwh.toFixed(6),
            co2_grams: co2Grams.toFixed(4),
            co2_saved: co2Saved.toFixed(4)
        };
        
        await fetch('/api/save-carbon-report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reportData)
        });
        
        addLog(`💾 Carbon report saved: ${co2Grams.toFixed(4)}g CO₂ emitted`);
        
    } catch (error) {
        console.error('Error saving carbon report:', error);
    }
}

// Format file size helper
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}