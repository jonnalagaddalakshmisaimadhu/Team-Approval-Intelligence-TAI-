
import pickle
import os

base_dir = r"c:\Users\Sai Madhu\Downloads\Loan prediction project\ML model"

try:
    with open(os.path.join(base_dir, "approval_features.pkl"), "rb") as f:
        features = pickle.load(f)
        with open("features_list.txt", "w") as out:
            out.write(str(features))
except Exception as e:
    with open("features_list.txt", "w") as out:
        out.write(str(e))
