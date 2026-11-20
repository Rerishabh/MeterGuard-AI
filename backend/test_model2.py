import joblib
from pathlib import Path

from model2_features import create_model2_features

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load trained Model 2
model = joblib.load(PROJECT_ROOT / "models" / "sih_fault_detection_model_2.joblib")


# Sample ESP32 reading
sample_data = {
    "T1_CS": 2.31,
    "T1_VS": 231.4,
    "T2_CS": 2.28,
    "T2_VS": 230.8,
    "H1_CS": 0.84,
    "H1_VS": 229.7
}


# Create the exact 12 features
features = create_model2_features(sample_data)

print("\nGenerated Model 2 features:")
print(features.to_string(index=False))


# Prediction
prediction = model.predict(features)[0]

print("\nRaw model prediction:", prediction)

if prediction == "normal":
    print("Model 2 result: NORMAL")
elif prediction == "fault_S1":
    print("Model 2 result: FAULT - S1")
elif prediction == "fault_S2":
    print("Model 2 result: FAULT - S2")
else:
    print("Model 2 result: UNKNOWN")