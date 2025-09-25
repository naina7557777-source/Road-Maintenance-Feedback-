import pandas as pd
from flask import Flask, render_template_string, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import uuid

# --- Flask App Initialization ---
app = Flask(__name__)
CSV_FILE_PATH = 'road_issues.csv'

# --- Firebase Initialization (Credentials will be provided by the environment) ---
db = None
bucket = None
try:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL"),
        "universe_domain": "googleapis.com"
    })
    firebase_admin.initialize_app(cred, {'storageBucket': os.environ.get("FIREBASE_STORAGE_BUCKET")})
    db = firestore.client()
    bucket = storage.bucket()
    print("Firebase initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    db = None
    bucket = None
    print("Warning: Firebase not initialized. API endpoints will not be functional.")


# --- HTML Template for the Frontend ---
FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Citizen Watch</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">

    <div id="app-container" class="bg-white rounded-lg shadow-xl p-6 md:p-8 max-w-4xl w-full">
        <h1 class="text-3xl md:text-4xl font-bold text-center text-gray-800 mb-2">
            Citizen Watch
        </h1>
        <p class="text-center text-sm text-gray-500 mb-6">Transparent Road Maintenance System</p>

        <!-- Tab Navigation -->
        <div class="flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-4 mb-6">
            <button id="tab-report" class="flex-1 py-3 px-4 rounded-md font-medium transition-colors duration-200 focus:outline-none bg-blue-600 text-white shadow-lg hover:bg-blue-700">
                Report Issue
            </button>
            <button id="tab-dashboard" class="flex-1 py-3 px-4 rounded-md font-medium transition-colors duration-200 focus:outline-none bg-gray-200 text-gray-800 hover:bg-gray-300">
                Public Dashboard
            </button>
            <button id="tab-admin" class="flex-1 py-3 px-4 rounded-md font-medium transition-colors duration-200 focus:outline-none bg-gray-200 text-gray-800 hover:bg-gray-300">
                Admin
            </button>
        </div>

        <!-- Report Form View -->
        <div id="report-view" class="view">
            <form id="report-form" class="space-y-4">
                <div>
                    <label for="issue_type" class="block text-sm font-medium text-gray-700">Issue Type</label>
                    <select id="issue_type" name="issue_type" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 transition-all duration-200 p-2">
                        <option value="Pothole">Pothole</option>
                        <option value="Streetlight Out">Streetlight Out</option>
                        <option value="Drainage Blockage">Drainage Blockage</option>
                        <option value="Damaged Guardrail">Damaged Guardrail</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
                <div>
                    <label for="description" class="block text-sm font-medium text-gray-700">Description</label>
                    <textarea id="description" name="description" rows="4" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 transition-all duration-200 p-2"></textarea>
                </div>
                <div>
                    <label for="location" class="block text-sm font-medium text-gray-700">Location</label>
                    <input type="text" id="location" name="location" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50 transition-all duration-200 p-2">
                </div>
                <div>
                    <label for="issue_photo" class="block text-sm font-medium text-gray-700">Attach Photo (Optional)</label>
                    <input type="file" id="issue_photo" name="issue_photo" accept="image/*" class="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/>
                </div>
                <button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-md shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200">
                    Submit Report
                </button>
                <div id="report-message" class="mt-4 text-center text-sm font-medium hidden"></div>
            </form>
        </div>

        <!-- Public Dashboard View -->
        <div id="dashboard-view" class="view hidden">
            <div class="overflow-x-auto rounded-md shadow-lg">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Issue</th>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Photo</th>
                        </tr>
                    </thead>
                    <tbody id="dashboard-body" class="bg-white divide-y divide-gray-200">
                        <!-- Data will be populated by JavaScript -->
                    </tbody>
                </table>
            </div>
            <div class="mt-4 text-center text-sm text-gray-500">
                <p>Status: 
                    <span class="font-bold text-red-600">Reported</span>, 
                    <span class="font-bold text-yellow-600">In Progress</span>, 
                    <span class="font-bold text-green-600">Completed</span>
                </p>
            </div>
        </div>
        
        <!-- Admin View -->
        <div id="admin-view" class="view hidden">
            <div class="space-y-4">
                <div>
                    <label for="issue_id_select" class="block text-sm font-medium text-gray-700">Select Issue ID</label>
                    <select id="issue_id_select" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2"></select>
                </div>
                <div>
                    <label for="status_select" class="block text-sm font-medium text-gray-700">Update Status to</label>
                    <select id="status_select" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2">
                        <option value="Reported">Reported</option>
                        <option value="In Progress">In Progress</option>
                        <option value="Completed">Completed</option>
                    </select>
                </div>
                <button id="update-status-btn" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-md shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200">
                    Update Status
                </button>
                <div id="admin-message" class="mt-4 text-center text-sm font-medium hidden"></div>
            </div>
        </div>
    </div>
    
    <!-- Modal for Messages -->
    <div id="modal-overlay" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden items-center justify-center p-4">
        <div class="bg-white rounded-lg p-6 shadow-xl w-full max-w-sm text-center">
            <h3 id="modal-title" class="text-xl font-bold mb-4 text-gray-800"></h3>
            <p id="modal-message" class="text-gray-600 mb-6"></p>
            <button id="modal-close-btn" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-md hover:bg-blue-700">
                Close
            </button>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', async () => {
            const tabs = {
                report: document.getElementById('tab-report'),
                dashboard: document.getElementById('tab-dashboard'),
                admin: document.getElementById('tab-admin'),
            };
            const views = {
                report: document.getElementById('report-view'),
                dashboard: document.getElementById('dashboard-view'),
                admin: document.getElementById('admin-view'),
            };
            const reportForm = document.getElementById('report-form');
            const dashboardBody = document.getElementById('dashboard-body');
            const issueIdSelect = document.getElementById('issue_id_select');
            const statusSelect = document.getElementById('status_select');
            const updateStatusBtn = document.getElementById('update-status-btn');
            const reportMessage = document.getElementById('report-message');
            const adminMessage = document.getElementById('admin-message');
            const modalOverlay = document.getElementById('modal-overlay');
            const modalCloseBtn = document.getElementById('modal-close-btn');
            const modalTitle = document.getElementById('modal-title');
            const modalMessage = document.getElementById('modal-message');

            const showTab = async (tabId) => {
                Object.values(tabs).forEach(tab => {
                    tab.classList.remove('bg-blue-600', 'text-white', 'shadow-lg');
                    tab.classList.add('bg-gray-200', 'text-gray-800');
                });
                Object.values(views).forEach(view => view.classList.add('hidden'));

                tabs[tabId].classList.remove('bg-gray-200', 'text-gray-800');
                tabs[tabId].classList.add('bg-blue-600', 'text-white', 'shadow-lg');
                views[tabId].classList.remove('hidden');

                if (tabId === 'dashboard' || tabId === 'admin') {
                    await fetchDashboardData();
                }
            };
            showTab('report');
            tabs.report.addEventListener('click', () => showTab('report'));
            tabs.dashboard.addEventListener('click', () => showTab('dashboard'));
            tabs.admin.addEventListener('click', () => showTab('admin'));
            modalCloseBtn.addEventListener('click', () => modalOverlay.classList.add('hidden'));

            reportForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                reportMessage.textContent = 'Submitting...';
                reportMessage.classList.remove('hidden', 'text-green-600', 'text-red-600');
                reportMessage.classList.add('text-gray-600');
                const formData = new FormData(reportForm);

                try {
                    const response = await fetch('/api/report', {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    if (response.ok) {
                        reportMessage.textContent = 'Report submitted successfully!';
                        reportMessage.classList.remove('text-gray-600');
                        reportMessage.classList.add('text-green-600');
                        reportForm.reset();
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    console.error('Error submitting report:', error);
                    reportMessage.textContent = 'Failed to submit report. Please try again.';
                    reportMessage.classList.remove('text-gray-600');
                    reportMessage.classList.add('text-red-600');
                }
            });

            const fetchDashboardData = async () => {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();
                    renderDashboard(data);
                    renderAdminPanel(data);
                } catch (error) {
                    console.error('Failed to fetch dashboard data:', error);
                    modalTitle.textContent = 'Error';
                    modalMessage.textContent = 'Could not load data from the server. Please ensure the Python server is running.';
                    modalOverlay.classList.remove('hidden');
                }
            };

            const renderDashboard = (reports) => {
                dashboardBody.innerHTML = '';
                reports.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                reports.forEach(report => {
                    const statusColor = report.status === 'Reported' ? 'bg-red-100 text-red-800' :
                                        report.status === 'In Progress' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-green-100 text-green-800';
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-4 md:px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${report.id.substring(0, 6)}...</td>
                        <td class="px-4 md:px-6 py-4 text-sm text-gray-900">${report.issueType}</td>
                        <td class="px-4 md:px-6 py-4 text-sm text-gray-900">${report.location}</td>
                        <td class="px-4 md:px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColor}">
                                ${report.status}
                            </span>
                        </td>
                        <td class="px-4 md:px-6 py-4 text-sm text-gray-900">
                            ${report.photoURL ? `<a href="${report.photoURL}" target="_blank" class="text-blue-500 hover:underline">View Photo</a>` : 'No Photo'}
                        </td>
                    `;
                    dashboardBody.appendChild(row);
                });
            };

            const renderAdminPanel = (reports) => {
                issueIdSelect.innerHTML = '';
                reports.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                if (reports.length > 0) {
                    reports.forEach(report => {
                        const option = document.createElement('option');
                        option.value = report.id;
                        option.textContent = `ID: ${report.id.substring(0, 6)}... - ${report.issueType} (${report.location})`;
                        issueIdSelect.appendChild(option);
                    });
                } else {
                    const option = document.createElement('option');
                    option.textContent = 'No issues to update';
                    issueIdSelect.appendChild(option);
                }
            };

            updateStatusBtn.addEventListener('click', async () => {
                const issueId = issueIdSelect.value;
                const newStatus = statusSelect.value;
                if (!issueId) {
                    adminMessage.textContent = 'No issues to update.';
                    adminMessage.classList.remove('hidden', 'text-green-600');
                    adminMessage.classList.add('text-red-600');
                    return;
                }

                adminMessage.textContent = 'Updating...';
                adminMessage.classList.remove('hidden', 'text-green-600', 'text-red-600');
                adminMessage.classList.add('text-gray-600');

                try {
                    const response = await fetch('/api/update-status', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: issueId, status: newStatus })
                    });
                    const result = await response.json();
                    if (response.ok) {
                        adminMessage.textContent = 'Status updated successfully!';
                        adminMessage.classList.remove('text-gray-600');
                        adminMessage.classList.add('text-green-600');
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    console.error("Error updating document:", error);
                    adminMessage.textContent = 'Failed to update status.';
                    adminMessage.classList.remove('text-gray-600');
                    adminMessage.classList.add('text-red-600');
                }
            });
        });
    </script>
</body>
</html>
"""
@app.route('/')
def serve_frontend():
    """Serves the main HTML page."""
    return render_template_string(FRONTEND_HTML)

@app.route('/api/report', methods=['POST'])
def handle_report():
    """Receives report and photo, stores them in Firebase."""
    if not db or not bucket:
        return jsonify({"error": "Firebase is not configured."}), 500

    issue_type = request.form.get('issue_type')
    description = request.form.get('description')
    location = request.form.get('location')
    photo_file = request.files.get('issue_photo')
    photo_url = None

    try:
        if photo_file:
            unique_id = uuid.uuid4().hex
            file_extension = os.path.splitext(photo_file.filename)[1]
            blob_name = f'reports/{unique_id}{file_extension}'
            blob = bucket.blob(blob_name)
            blob.upload_from_file(photo_file)
            blob.make_public()
            photo_url = blob.public_url

        report_data = {
            'issueType': issue_type,
            'description': description,
            'location': location,
            'photoURL': photo_url,
            'status': 'Reported',
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection('reports').document()
        doc_ref.set(report_data)

        return jsonify({"message": "Report submitted", "id": doc_ref.id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard')
def get_dashboard_data():
    """Fetches all reports from Firebase."""
    if not db:
        return jsonify({"error": "Firebase is not configured."}), 500

    try:
        reports_ref = db.collection('reports')
        docs = reports_ref.stream()
        reports = []
        for doc in docs:
            report = doc.to_dict()
            report['id'] = doc.id
            reports.append(report)
        return jsonify(reports), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-status', methods=['POST'])
def update_status():
    """Updates the status of a specific report in Firebase."""
    if not db:
        return jsonify({"error": "Firebase is not configured."}), 500

    data = request.json
    report_id = data.get('id')
    new_status = data.get('status')

    if not report_id or not new_status:
        return jsonify({"error": "Missing ID or status"}), 400

    try:
        doc_ref = db.collection('reports').document(report_id)
        doc_ref.update({"status": new_status})
        return jsonify({"message": "Status updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
