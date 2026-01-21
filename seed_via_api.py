
import requests
import json

base_url = "http://localhost:5000"

def seed_application():
    # 1. Predict (Save Initial Application)
    payload = {
        "Age": 32, "Gender": 1, "Marital_Status": 1, "Dependents": 0, "Education": 1, "Self_Employed": 1, 
        "Work_Experience_Years": 5, "ApplicantIncome": 75000, "CoapplicantIncome": 0, 
        "Salary_Payment_Mode": 1, "Existing_EMI": 1000, "Residential_Assets": 0, "Area": 1, 
        "Loan_Purpose": 1, "LoanAmount": 500000, "Loan_Amount_Term": 24,
        "Name": "Dynamic Test User" 
    }
    
    print("Sending prediction request...")
    res = requests.post(f"{base_url}/predict", json=payload)
    if res.status_code != 200:
        print(f"Prediction failed: {res.text}")
        return

    data = res.json()
    app_id = data.get('application_id')
    print(f"Application created with ID: {app_id}")
    
    if not app_id:
        print("No application_id returned.")
        return

    # 2. Apply to SBI (so it shows up for Officer 'saimadhu')
    apply_payload = {
        "application_id": app_id,
        "bank_name": "SBI"
    }
    
    print(f"Applying to SBI for app_id: {app_id}")
    res_apply = requests.post(f"{base_url}/apply", json=apply_payload)
    
    if res_apply.status_code == 200:
        print("Application submitted successfully to SBI.")
    else:
        print(f"Application submission failed: {res_apply.text}")

if __name__ == "__main__":
    seed_application()
