
import pickle
import os
import sys
import sklearn

print(f"Sklearn version: {sklearn.__version__}")

ml_dir = "C:\\Users\\Sai Madhu\\Downloads\\Loan prediction project\\ML model"
encoder_path = os.path.join(ml_dir, "bank_label_encoder.pkl")

try:
    with open(encoder_path, "rb") as f:
        encoder = pickle.load(f)
    print("Encoder loaded successfully.")
    print(f"Classes: {encoder.classes_}")
except Exception as e:
    print(f"Failed to load encoder: {e}")
