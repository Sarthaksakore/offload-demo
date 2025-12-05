from flask import Flask, render_template, request, jsonify, send_file, url_for
import requests
import os
import json
import csv
from datetime import datetime
import zipfile
import logging

# Set up logging for Flask for better debugging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- Configuration ---
# Allow overriding the FastAPI backend URL via env var so we can deploy Flask wherever needed.
# Default stays on localhost so relative routes work out of the box.
BACKEND_URL = os.environ.get("FASTAPI_BASE_URL", "http://localhost:8000").rstrip("/")

# Folder configuration
# BASE_DIR ensures that the relative path resolution works regardless of the execution context
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, 'outputs')
app.config['REPORTS_FOLDER'] = os.path.join(BASE_DIR, 'reports')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload size

# Create necessary folders on startup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

# ==================== ROUTES (Template Rendering) ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/carbon')
def carbon():
    return render_template('carbon.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/tasks')
def tasks():
    return render_template('tasks.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/map')
def carbon_map():
    return render_template('map.html')

# ==================== API ROUTES (Backend Interaction) ====================

@app.route('/api/carbon-intensity')
def get_carbon_intensity():
    try:
        region = request.args.get('region', 'IN-WE')
        response = requests.get(f"{BACKEND_URL}/carbon-intensity?region={region}")
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"FastAPI Carbon API Error: {e}")
        return jsonify({"error": "FastAPI communication error or invalid region"}), 503

@app.route('/api/greenai', methods=['POST'])
def ask_greenai():
    try:
        data = request.get_json()
        question = data.get('question', '')
                
        response = requests.post(
            f"{BACKEND_URL}/greenai",
            json={"question": question},
            timeout=180
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"FastAPI Green AI Error: {e}")
        try:
            detail = response.json().get('details', 'No detail provided.')
        except:
            detail = str(e)
            
        return jsonify({"error": "FastAPI communication error for Green AI", "details": detail}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload-task', methods=['POST'])
def upload_task():
    """Upload task ZIP file and save it locally on the Flask server."""
    try:
        if 'file' not in request.files:
            app.logger.warning("Upload attempt failed: No file part.")
            return jsonify({"error": "No file part in the request"}), 400
                
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected for upload"}), 400
                
        if not file.filename.lower().endswith('.zip'):
            return jsonify({"error": "Only ZIP files (.zip) are allowed"}), 400
                
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_name = os.path.splitext(file.filename)[0].replace(' ', '_')
        filename = f"{timestamp}_{original_name}.zip"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        app.logger.info(f"File saved successfully to: {filepath}")

        return jsonify({
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "size": os.path.getsize(filepath)
        })
    except Exception as e:
        app.logger.error(f"File upload failed in Flask: {e}")
        return jsonify({"error": f"Internal Server Error during file save in Flask: {str(e)}"}), 500

@app.route('/api/run-task', methods=['POST'])
def run_task():
    """Execute task on FastAPI backend and get output ZIP"""
    try:
        data = request.get_json()
        filename = data.get('filename')
                
        if not filename:
            return jsonify({"error": "No uploaded filename provided"}), 400
                
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "Uploaded file not found on server"}), 404
                
        # Send to FastAPI Backend
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f, 'application/zip')}
            response = requests.post(
                f"{BACKEND_URL}/run-task",
                files=files,
                timeout=600
            )
                
        response.raise_for_status() 
        
        output_filename = f"output_{filename}"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Save output ZIP file (binary write)
        with open(output_path, 'wb') as f:
            f.write(response.content)

        # Extract and read logs 
        logs = extract_task_logs(output_path)
            
        return jsonify({
            "success": True,
            "output_file": output_filename,
            "logs": logs
        })
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"FastAPI Run Task Error: {e}")
        try:
            error_detail = response.json().get('detail', response.text)
        except:
            error_detail = str(e)
            
        return jsonify({"error": "Backend execution failed", "details": error_detail}), 503
    except Exception as e:
        app.logger.error(f"Run Task failed in Flask: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download-output/<filename>')
def download_output(filename):
    """
    [CRITICAL FUNCTION] - Downloads the output ZIP file saved by Flask.
    """
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(filepath):
            # send_file correctly sets the MIME type and forces download
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return jsonify({"error": "Output file not found in Flask outputs folder"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # Ensure the function returns a response

@app.route('/api/get-reports')
def get_reports():
    try:
        reports = []
        for filename in os.listdir(app.config['REPORTS_FOLDER']):
            if filename.endswith('.csv'):
                filepath = os.path.join(app.config['REPORTS_FOLDER'], filename)
                reports.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                })
        return jsonify(reports)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download-report/<filename>')
def download_report(filename):
    try:
        filepath = os.path.join(app.config['REPORTS_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return jsonify({"error": "Report not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # Ensure the function returns a response

# ==================== HELPER FUNCTIONS ====================

def extract_task_logs(output_zip_path):
    """Extract logs (e.g., result.txt) from output ZIP file for display"""
    logs = []
    try:
        with zipfile.ZipFile(output_zip_path, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                # Only check for common log/text files
                if filename.endswith('.txt') or filename.endswith('.log') or filename.endswith('.csv'):
                    if zip_ref.getinfo(filename).file_size < 10 * 1024 * 1024: # Limit log size
                        with zip_ref.open(filename) as f:
                            content = f.read().decode('utf-8', errors='ignore')
                            logs.append({
                                'filename': filename,
                                'content': content
                            })
    except Exception as e:
        logs.append({'filename': 'error.log', 'content': f"Error extracting logs: {str(e)}"})
    return logs

# ==================== RUN APP ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)