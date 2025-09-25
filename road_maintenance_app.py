from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import pandas as pd
import os
import secrets

# --- NEW: Firebase Admin SDK Initialization ---
import firebase_admin
from firebase_admin import credentials, firestore

# Path to your downloaded service account key JSON file
# !!! IMPORTANT: REPLACE 'road-maintenance-feedback-firebase-adminsdk-xxxxx-xxxxxx.json' WITH YOUR ACTUAL FILENAME !!!
SERVICE_ACCOUNT_KEY_PATH = 'road-maintenance-feedback-firebase-adminsdk-fb5vc-a4fba31142.json'

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully!")
except Exception as e:
    print(f"ERROR: Could not initialize Firebase Admin SDK: {e}")
    print("Please ensure your service account key path is correct and the file exists.")
# --- END NEW: Firebase Admin SDK Initialization ---


# --- Flask App Initialization and Data Handling ---
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
# The CSV file path is no longer needed as we are using Firestore for persistence.
# CSV_FILE_PATH = 'road_issues.csv'

# Hardcoded credentials for this example
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# --- MODIFIED: load_data now fetches from Firestore ---
def load_data():
    """Loads data from Firestore."""
    reports_ref = db.collection('reports')
    docs = reports_ref.stream()
    data_list = []
    for doc in docs:
        report = doc.to_dict()
        report['ID'] = doc.id
        data_list.append(report)
    
    if not data_list:
        return pd.DataFrame(columns=['ID', 'Issue Type', 'Description', 'Location', 'Status'])
    
    return pd.DataFrame(data_list)

# The save_data function is no longer needed in its current form
# def save_data(df):
#     """Saves the DataFrame to a CSV file."""
#     df.to_csv(CSV_FILE_PATH, index=False)

# --- Unified HTML Template ---
MAIN_APP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Road Maintenance System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">

    <div id="app-container" class="bg-white rounded-lg shadow-xl p-6 md:p-8 max-w-4xl w-full">
        <h1 class="text-3xl md:text-4xl font-bold text-center text-gray-800 mb-2">
            Road Maintenance System
        </h1>
        <p class="text-center text-sm text-gray-500 mb-6">A unified reporting and admin app</p>

        <!-- Tab Navigation -->
        <div class="flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-4 mb-6">
            <button id="tab-report" class="flex-1 py-3 px-4 rounded-md font-medium transition-colors duration-200 focus:outline-none bg-blue-600 text-white shadow-lg hover:bg-blue-700">
                Report an Issue
            </button>
            <button id="tab-dashboard" class="flex-1 py-3 px-4 rounded-md font-medium transition-colors duration-200 focus:outline-none bg-gray-200 text-gray-800 hover:bg-gray-300">
                Public Dashboard
            </button>
            <button id="tab-admin" class="flex-1 py-3 px-4 rounded-md font-medium transition-colors duration-200 focus:outline-none bg-gray-200 text-gray-800 hover:bg-gray-300">
                Admin
            </button>
        </div>

        <!-- View Containers -->
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
                <button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-md shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200">
                    Submit Report
                </button>
                <div id="report-message" class="mt-4 text-center text-sm font-medium hidden"></div>
            </form>
        </div>

        <div id="dashboard-view" class="view hidden">
            <div class="overflow-x-auto rounded-md shadow-lg">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Issue</th>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                            <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        </tr>
                    </thead>
                    <tbody id="dashboard-body" class="bg-white divide-y divide-gray-200">
                        <!-- Data will be populated by JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <div id="admin-view" class="view hidden">
            <div id="admin-login" class="space-y-4">
                <h2 class="text-xl font-bold text-center">Admin Login</h2>
                <form id="login-form" class="space-y-4">
                    <div>
                        <label for="username" class="block text-sm font-medium text-gray-700">Username</label>
                        <input type="text" id="username" name="username" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2">
                    </div>
                    <div>
                        <label for="password" class="block text-sm font-medium text-gray-700">Password</label>
                        <input type="password" id="password" name="password" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2">
                    </div>
                    <button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-md shadow-lg hover:bg-blue-700">
                        Log In
                    </button>
                    <div id="login-message" class="mt-2 text-center text-sm font-medium hidden"></div>
                </form>
            </div>

            <div id="admin-panel" class="space-y-4 hidden">
                <div class="space-y-4">
                    <div class="overflow-x-auto rounded-md shadow-lg">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                                    <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Issue</th>
                                    <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                                    <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                    <th class="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                                </tr>
                            </thead>
                            <tbody id="admin-body" class="bg-white divide-y divide-gray-200">
                                <!-- Data will be populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
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
            const adminBody = document.getElementById('admin-body');
            const reportMessage = document.getElementById('report-message');
            const loginForm = document.getElementById('login-form');
            const loginMessage = document.getElementById('login-message');
            const adminLogin = document.getElementById('admin-login');
            const adminPanel = document.getElementById('admin-panel');
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

            function showModal(title, message) {
                modalTitle.textContent = title;
                modalMessage.textContent = message;
                modalOverlay.classList.remove('hidden');
                modalOverlay.classList.add('flex');
            }

            reportForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                reportMessage.textContent = 'Submitting...';
                reportMessage.classList.remove('hidden', 'text-green-600', 'text-red-600');
                reportMessage.classList.add('text-gray-600');
                
                const formData = new FormData(reportForm);
                const data = Object.fromEntries(formData.entries());

                try {
                    const response = await fetch('/report', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
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
                    const response = await fetch('/dashboard_data');
                    const data = await response.json();
                    renderDashboard(data);
                    renderAdminPanel(data);
                } catch (error) {
                    console.error('Failed to fetch dashboard data:', error);
                    showModal('Error', 'Could not load data from the server.');
                }
            };

            const renderDashboard = (reports) => {
                dashboardBody.innerHTML = '';
                reports.sort((a, b) => b.ID - a.ID);
                reports.forEach(report => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-4 md:px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${report.ID}</td>
                        <td class="px-4 md:px-6 py-4 text-sm text-gray-900">${report['Issue Type']}</td>
                        <td class="px-4 md:px-6 py-4 text-sm text-gray-900">${report.Location}</td>
                        <td class="px-4 md:px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(report.Status)}">
                                ${report.Status}
                            </span>
                        </td>
                    `;
                    dashboardBody.appendChild(row);
                });
            };

            const renderAdminPanel = (reports) => {
                adminBody.innerHTML = '';
                reports.sort((a, b) => b.ID - a.ID);
                reports.forEach(report => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-4 md:px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${report.ID}</td>
                        <td class="px-4 md:px-6 py-4 text-sm text-gray-900">${report['Issue Type']}</td>
                        <td class="px-4 md:px-6 py-4 text-sm text-gray-900">${report.Location}</td>
                        <td class="px-4 md:px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <select id="status-select-${report.ID}" class="p-1 rounded-md">
                                <option value="Reported" ${report.Status === 'Reported' ? 'selected' : ''}>Reported</option>
                                <option value="In Progress" ${report.Status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                                <option value="Completed" ${report.Status === 'Completed' ? 'selected' : ''}>Completed</option>
                            </select>
                        </td>
                        <td class="px-4 md:px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button data-id="${report.ID}" class="update-btn text-indigo-600 hover:text-indigo-900">Update</button>
                        </td>
                    `;
                    adminBody.appendChild(row);
                });

                document.querySelectorAll('.update-btn').forEach(button => {
                    button.addEventListener('click', async (e) => {
                        const id = e.target.dataset.id;
                        const newStatus = document.getElementById(`status-select-${id}`).value;
                        await updateStatus(id, newStatus);
                    });
                });
            };

            const getStatusColor = (status) => {
                switch (status) {
                    case 'Reported': return 'bg-red-100 text-red-800';
                    case 'In Progress': return 'bg-yellow-100 text-yellow-800';
                    case 'Completed': return 'bg-green-100 text-green-800';
                    default: return 'bg-gray-100 text-gray-800';
                }
            };

            const updateStatus = async (id, newStatus) => {
                try {
                    const response = await fetch('/update_status', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: id, status: newStatus })
                    });
                    const result = await response.json();
                    if (response.ok) {
                        showModal('Success', 'Status updated successfully!');
                        await fetchDashboardData();
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    console.error("Error updating status:", error);
                    showModal('Error', 'Failed to update status.');
                }
            };

            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = loginForm.username.value;
                const password = loginForm.password.value;
                
                loginMessage.textContent = 'Logging in...';
                loginMessage.classList.remove('hidden');
                loginMessage.classList.add('text-gray-600');

                try {
                    const response = await fetch('/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    const result = await response.json();
                    if (response.ok) {
                        adminLogin.classList.add('hidden');
                        adminPanel.classList.remove('hidden');
                        loginMessage.textContent = 'Login successful!';
                        loginMessage.classList.remove('text-red-600', 'text-gray-600');
                        loginMessage.classList.add('text-green-600');
                        await fetchDashboardData();
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    console.error("Login failed:", error);
                    showModal('Login Failed', 'Invalid username or password.');
                    loginMessage.textContent = '';
                }
            });
        });
    </script>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/', methods=['GET'])
def index():
    return render_template_string(MAIN_APP_HTML)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# --- MODIFIED: The report_issue route will now save to Firestore ---
@app.route('/report', methods=['POST'])
def report_issue():
    data = request.json
    issue_type = data.get('issue_type')
    description = data.get('description')
    location = data.get('location')

    new_report = {
        'issue_type': issue_type,
        'description': description,
        'location': location,
        'status': 'Reported'
    }
    
    try:
        doc_ref = db.collection('reports').add(new_report)
        return jsonify({"message": "Report submitted", "id": doc_ref[1].id}), 200
    except Exception as e:
        print(f"Error saving report to Firestore: {e}")
        return jsonify({"error": "Failed to submit report"}), 500

@app.route('/dashboard_data', methods=['GET'])
def get_dashboard_data():
    df = load_data()
    return jsonify(df.to_dict('records'))

# --- MODIFIED: The update_status route will now update in Firestore ---
@app.route('/update_status', methods=['POST'])
def update_status():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    report_id = data.get('id')
    new_status = data.get('status')

    try:
        doc_ref = db.collection('reports').document(report_id)
        doc_ref.update({'status': new_status})
        
        return jsonify({"message": "Status updated successfully"}), 200
    except Exception as e:
        print(f"Error updating report status in Firestore: {e}")
        return jsonify({"error": "Failed to update status"}), 500

if __name__ == '__main__':
    app.run(debug=True)
