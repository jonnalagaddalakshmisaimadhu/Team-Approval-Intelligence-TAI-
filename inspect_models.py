
import pickle
import os
import sys

base_dir = r"c:\Users\Sai Madhu\Downloads\Loan prediction project\ML model"

def inspect():
    try:
        with open(os.path.join(base_dir, "approval_features.pkl"), "rb") as f:
            features = pickle.load(f)
            print("Features:", features)
    except Exception as e:
        print("Error loading features:", e)

    try:
        with open(os.path.join(base_dir, "bank_label_encoder.pkl"), "rb") as f:
            le = pickle.load(f)
            print("Label Encoder Classes:", le.classes_)
    except Exception as e:
        print("Error loading label encoder:", e)

if __name__ == "__main__":
    inspect()
