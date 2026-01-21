
from flask import Flask
from flask_pymongo import PyMongo
import pandas as pd
from bson.objectid import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/loan_db"
mongo = PyMongo(app)

def seed():
    # Create a sample application
    sample_app = {
        'input': {
            'Name': 'Test Applicant Dynamic',
            'Age': 35,
            'Gender': 1,
            'Marital_Status': 1,
            'Dependents': 2,
            'Education': 1,
            'Self_Employed': 0,
            'Work_Experience_Years': 8,
            'ApplicantIncome': 75000,
            'CoapplicantIncome': 0,
            'Salary_Payment_Mode': 1,
            'Existing_EMI': 1500,
            'Residential_Assets': 1,
            'Area': 1,
            'Loan_Purpose': 1,
            'LoanAmount': 1000000,
            'Loan_Amount_Term': 60,
            # Hidden_CIBIL is missing, simulating user submission without it
        },
        'prediction': {
             # Mock prediction from user level (optional)
        },
        'status': 'applied',
        'selected_bank': 'SBI', # Linked to saimadhu
        'timestamp': pd.Timestamp.now().isoformat()
    }

    try:
        # Clear existing to be clean (optional, maybe just insert)
        # mongo.db.loan_applications.delete_many({}) 
        
        result = mongo.db.loan_applications.insert_one(sample_app)
        print(f"Inserted sample application with ID: {result.inserted_id}")
    except Exception as e:
        print(f"Error seeding data: {e}")

if __name__ == '__main__':
    with app.app_context():
        seed()
