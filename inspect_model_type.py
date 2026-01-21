
import pickle
import os

base_dir = r"c:\Users\Sai Madhu\Downloads\Loan prediction project\ML model"

try:
    with open(os.path.join(base_dir, "user_approval_model.pkl"), "rb") as f:
        model = pickle.load(f)
        print("Model Type:", type(model))
        if hasattr(model, 'steps'):
            print("Pipeline steps:", [s[0] for s in model.steps])
except Exception as e:
    print("Error loading model:", e)
