
from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import os
import sys
import pandas as pd
import json
import uuid
import glob

# Add "ML model" directory to path to import prediction_script
base_dir = os.path.dirname(os.path.abspath(__file__))
ml_dir = os.path.join(base_dir, "ML model")
officer_dir = os.path.join(base_dir, "officer models")
sys.path.append(ml_dir)
sys.path.append(officer_dir)

try:
    import prediction_script
except ImportError as e:
    print(f"Error importing prediction_script: {e}")
    # Fallback if import fails (unlikely)
    prediction_script = None

try:
    import prediction as officer_prediction
except ImportError as e:
    print(f"Error importing officer prediction module: {e}")
    officer_prediction = None

from flask_pymongo import PyMongo
from bson.objectid import ObjectId

app = Flask(__name__)
# Enable CORS for Angular App
CORS(app, resources={r"/*": {"origins": "*"}})

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/loan_db"
mongo = PyMongo(app)

# Test MongoDB Connection immediately
try:
    mongo.cx.server_info() # Forces a connection attempt
    print("\n" + "="*50)
    print(" SUCCESS: Connected to Local MongoDB!")
    print(f" Database: {app.config['MONGO_URI']}")
    print("="*50 + "\n")
except Exception as e:
    print("\n" + "!"*50)
    print(" WARNING: Cound NOT connect to MongoDB.")
    print(" ensure the MongoDB Service is running.")
    print(f" Error details: {e}")
    print(" System will fall back to 'local_applications.json'")
    print("!"*50 + "\n")

# Global Variables for Models
approval_model = None
bank_model = None
bank_encoder = None
approval_features = []

def load_models():
    global approval_model, bank_model, bank_encoder, approval_features
    try:
        print("Loading models from:", ml_dir)
        
        with open(os.path.join(ml_dir, "user_approval_model.pkl"), "rb") as f:
            approval_model = pickle.load(f)
            
        with open(os.path.join(ml_dir, "user_bank_recommendation_model.pkl"), "rb") as f:
            bank_model = pickle.load(f)
            
        # Try loading encoder
        try:
            with open(os.path.join(ml_dir, "bank_label_encoder.pkl"), "rb") as f:
                bank_encoder = pickle.load(f)
        except Exception as e:
            print(f"Warning: Bank Encoder could not be loaded: {e}")
            bank_encoder = None
            
        # Try loading feature list
        try:
            with open(os.path.join(ml_dir, "approval_features.pkl"), "rb") as f:
                approval_features = pickle.load(f)
        except Exception as e:
            print(f"Warning: Feature list could not be loaded, using default: {e}")
            # Fallback list based on previous inspection
            approval_features = ['Age', 'Gender', 'Marital_Status', 'Dependents', 'Education', 'Self_Employed', 
                                 'Work_Experience_Years', 'ApplicantIncome', 'CoapplicantIncome', 'Salary_Payment_Mode', 
                                 'Existing_EMI', 'Residential_Assets', 'Area', 'Loan_Purpose', 'LoanAmount', 'Loan_Amount_Term']

        print("Models loaded successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load models: {e}")

    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load models: {e}")

# --- DB Helper Functions ---
DB_FILE = os.path.join(base_dir, "local_applications.json")

def read_local_db():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_local_db(data):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, default=str, indent=4)
    except Exception as e:
        print(f"Error saving local DB: {e}")

def db_insert_application(record):
    try:
        # Try Mongo first
        if mongo.db: # connection might technically be live object even if server down, but insert throws
            inserted = mongo.db.loan_applications.insert_one(record)
            return str(inserted.inserted_id)
    except Exception:
        pass
    
    # Fallback/Primary JSON
    print("Using local JSON DB for insert.")
    apps = read_local_db()
    if '_id' not in record:
        record['_id'] = str(uuid.uuid4())
    # Ensure timestamp is string
    if hasattr(record.get('timestamp'), 'isoformat'):
        record['timestamp'] = record['timestamp'].isoformat()
    
    apps.append(record)
    save_local_db(apps)
    return record['_id']

def db_update_application(app_id, update_fields):
    success = False
    # Try Mongo
    try:
        if mongo.db:
            try:
                oid = ObjectId(app_id)
                res = mongo.db.loan_applications.update_one({'_id': oid}, {'$set': update_fields})
                if res.modified_count > 0:
                    success = True
            except:
                pass # ID might be UUID, not ObjectId
    except Exception:
        pass
        
    if success: return True

    # Local JSON update
    apps = read_local_db()
    updated = False
    for app in apps:
        if str(app.get('_id')) == str(app_id):
            # Update nested keys like 'input.Name'
            for key, val in update_fields.items():
                if '.' in key:
                    parent, child = key.split('.')
                    if parent not in app: app[parent] = {}
                    if isinstance(app[parent], dict):
                        app[parent][child] = val
                else:
                    app[key] = val
            updated = True
            break
    if updated:
        save_local_db(apps)
        return True
    return False

def db_get_applications(query_bank=None):
    results = []
    # Try Mongo
    try:
        query = {}
        if query_bank:
            query['selected_bank'] = {'$regex': f'^{query_bank}$', '$options': 'i'}
        apps = list(mongo.db.loan_applications.find(query).sort('timestamp', -1).limit(50))
        for app in apps:
            app['_id'] = str(app['_id'])
            results.append(app)
    except Exception as e:
        print(f"Mongo Fetch Error: {e}")

    # Local JSON
    local_apps = read_local_db()
    for app in local_apps:
        # Filter
        if query_bank:
            if app.get('selected_bank') and query_bank.lower() in str(app.get('selected_bank')).lower():
                results.append(app)
        else:
            results.append(app)
            
    # Dedup
    seen = set()
    unique_results = []
    for r in results:
        rid = str(r.get('_id'))
        if rid not in seen:
            seen.add(rid)
            unique_results.append(r)
            
    # Sort
    unique_results.sort(key=lambda x: str(x.get('timestamp', '')), reverse=True)
    return unique_results

def db_get_application(app_id):
    # Mongo
    try:
        try:
            oid = ObjectId(app_id)
            app = mongo.db.loan_applications.find_one({'_id': oid})
            if app:
                app['_id'] = str(app['_id'])
                return app
        except:
            pass
    except:
        pass
        
    # Local JSON
    apps = read_local_db()
    for app in apps:
        if str(app.get('_id')) == str(app_id):
            return app
    return None

def db_get_all_applications():
    # Helper to get ALL applications without bank filter
    return db_get_applications()

def get_blocked_users():
    # Simple file-based blocked users
    BLOCKED_FILE = os.path.join(base_dir, "blocked_users.json")
    if not os.path.exists(BLOCKED_FILE):
        return []
    try:
        with open(BLOCKED_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_blocked_user(user_identifier):
    BLOCKED_FILE = os.path.join(base_dir, "blocked_users.json")
    blocked = get_blocked_users()
    if user_identifier not in blocked:
        blocked.append(user_identifier)
        with open(BLOCKED_FILE, 'w') as f:
            json.dump(blocked, f)

def remove_blocked_user(user_identifier):
    BLOCKED_FILE = os.path.join(base_dir, "blocked_users.json")
    blocked = get_blocked_users()
    if user_identifier in blocked:
        blocked.remove(user_identifier)
        with open(BLOCKED_FILE, 'w') as f:
            json.dump(blocked, f)

# --- Admin Routes ---

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Simple hardcoded auth for demo
    if username == "admin" and password == "admin123":
        return jsonify({'token': 'admin-demo-token-123', 'message': 'Login successful'})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    apps = db_get_all_applications()
    blocked_users = get_blocked_users()
    
    # Aggregations
    total_apps = len(apps)
    approved = sum(1 for a in apps if str(a.get('status')).lower() == 'approved')
    rejected = sum(1 for a in apps if str(a.get('status')).lower() == 'rejected')
    fraud = sum(1 for a in apps if str(a.get('status')).lower() == 'fraud' or a.get('fraud_flag') == True)
    
    # Estimated Active Officers (count folders in officer directory)
    officer_count = 0
    if os.path.exists(officer_dir):
        officer_count = len([name for name in os.listdir(officer_dir) if os.path.isdir(os.path.join(officer_dir, name))])
        
    return jsonify({
        'total_applications': total_apps,
        'approved_loans': approved,
        'rejected_loans': rejected,
        'fraud_reports': fraud,
        'active_officers': officer_count,
        'blocked_users': len(blocked_users)
    })

@app.route('/admin/bank-stats', methods=['GET'])
def admin_bank_stats():
    apps = db_get_all_applications()
    stats = {}
    
    for app in apps:
        bank = app.get('selected_bank', 'Unknown')
        if not bank: bank = 'Unknown'
        
        if bank not in stats:
            stats[bank] = {'applications': 0, 'approved': 0, 'rejected': 0, 'fraud': 0}
            
        stats[bank]['applications'] += 1
        status = str(app.get('status')).lower()
        if status == 'approved':
            stats[bank]['approved'] += 1
        elif status == 'rejected':
            stats[bank]['rejected'] += 1
        elif status == 'fraud' or app.get('fraud_flag'):
             stats[bank]['fraud'] += 1
             
    return jsonify(stats)

@app.route('/admin/officer-stats', methods=['GET'])
def admin_officer_stats():
    # In a real app, we'd query an Officer DB.
    # Here we'll Mock it or derive from Applications if 'officer_id' was present (it's not clearly currently).
    # We will list officers from the directory and try to find their stats.
    
    officers = []
    if os.path.exists(officer_dir):
        for name in os.listdir(officer_dir):
            if os.path.isdir(os.path.join(officer_dir, name)):
                 officers.append({
                     'name': name,
                     'bank': 'Assigned Bank', # Placeholder as we don't have mapping yet
                     'processed': 0,
                     'approved': 0,
                     'rejected': 0,
                     'fraud': 0
                 })
    return jsonify(officers)

@app.route('/admin/fraud-cases', methods=['GET'])
def admin_fraud_cases():
    apps = db_get_all_applications()
    frauds = [a for a in apps if str(a.get('status')).lower() == 'fraud' or a.get('fraud_flag') == True]
    return jsonify(frauds)

@app.route('/admin/users', methods=['GET'])
def admin_users():
    apps = db_get_all_applications()
    users_map = {}
    blocked = set(get_blocked_users())
    
    for app in apps:
        # Identify user by Name or Mobile? Let's use Name + Mobile as key or Input.Name
        inp = app.get('input', {})
        name = inp.get('Name', 'Unknown')
        mobile = inp.get('Mobile', 'Unknown')
        
        key = f"{name}|{mobile}"
        if key not in users_map:
            users_map[key] = {
                'name': name,
                'mobile': mobile,
                'applications': 0,
                'last_status': None,
                'is_blocked': key in blocked
            }
        users_map[key]['applications'] += 1
        users_map[key]['last_status'] = app.get('status')
        
    return jsonify(list(users_map.values()))

@app.route('/admin/block-user', methods=['POST'])
def admin_block_user():
    data = request.get_json()
    user_key = data.get('user_key') # expects "Name|Mobile"
    action = data.get('action') # 'block' or 'unblock'
    
    if action == 'block':
        save_blocked_user(user_key)
    elif action == 'unblock':
        remove_blocked_user(user_key)
        
    return jsonify({'success': True})

@app.route('/predict', methods=['POST'])
def predict():
    if not approval_model:
        return jsonify({'error': 'Models not loaded'}), 500
        
    try:
        data = request.get_json()
        print("Received prediction request:", data)
        
        result = prediction_script.predict(
            data, 
            approval_model, 
            bank_model, 
            bank_encoder, 
            approval_features
        )
        
        # Save using Helper
        try:
            record = {
                'input': data,
                'prediction': result,
                'status': 'predicted',
                'selected_bank': None,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            # Use abstracted insert
            app_id = db_insert_application(record)
            result['application_id'] = app_id
            print(f"Saved prediction with ID: {app_id}")
        except Exception as db_err:
            print(f"DB Error (Prediction not saved): {db_err}")
            result['application_id'] = None
            
        print("Prediction result:", result)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error during prediction: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/apply', methods=['POST'])
def apply_for_loan():
    try:
        data = request.get_json()
        app_id = data.get('application_id')
        bank_name = data.get('bank_name')
        
        # New fields for officer contact
        applicant_name = data.get('applicant_name')
        applicant_mobile = data.get('applicant_mobile')
        
        if not app_id or not bank_name:
            return jsonify({'error': 'Missing application_id or bank_name'}), 400
            
        update_fields = {
            'selected_bank': bank_name,
            'status': 'applied',
            'applied_at': pd.Timestamp.now().isoformat()
        }
        
        # Add contact info to input section (or top level, but input is where user data lives)
        if applicant_name:
            update_fields['input.Name'] = applicant_name
        if applicant_mobile:
            update_fields['input.Mobile'] = applicant_mobile
            
        # Update DB using Helper
        success = db_update_application(app_id, update_fields)
        
        if success:
            return jsonify({'success': True, 'message': f'Application submitted for {bank_name}'})
        else:
            return jsonify({'success': False, 'message': 'Application not found or update failed'}), 404
            
    except Exception as e:
        print(f"Error during application: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'online', 'models_loaded': approval_model is not None})

@app.route('/applications', methods=['GET'])
def get_applications():
    try:
        bank_name = request.args.get('bank')
        query = {}
        if bank_name:
            # Case-insensitive match for bank name (Relaxed to substring match for safety)
            print(f"Searching for applications for bank query: {repr(bank_name)}")
            query['selected_bank'] = {'$regex': f'{bank_name}', '$options': 'i'}
            
        # Use Helper
        results = db_get_applications(bank_name)
        print(f"Found {len(results)} applications for {bank_name}")
        return jsonify(results)
    except Exception as e:
        print(f"Error fetching applications: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/application/<app_id>', methods=['GET'])
def get_application_details(app_id):
    try:
        # Use Helper
        app_details = db_get_application(app_id)
        if app_details:
            return jsonify(app_details)
        else:
            return jsonify({'error': 'Application not found'}), 404
    except Exception as e:
        print(f"Error fetching application {app_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/officer_predict', methods=['POST'])
def officer_predict_endpoint():
    if not officer_prediction:
        return jsonify({'error': 'Officer prediction module not loaded'}), 500
        
    try:
        data = request.get_json()
        print("Received officer prediction request:", data)
        
        # Officer prediction does not depend on the global 'load_models' for ML model folder
        # It handles its own loading internally in prediction.py
        result = officer_prediction.officer_predict(data)
        
        print("Officer prediction result:", result)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error during officer prediction: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    load_models()
    # Run on Port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
