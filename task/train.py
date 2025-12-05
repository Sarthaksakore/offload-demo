import os
import time
import json
import pickle

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

# 1) Prepare output folder
BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

log_lines = []

def log(msg):
    print(msg)  # goes to container logs
    log_lines.append(msg)

def main():
    start_time = time.time()
    log("🚀 Starting demo training task...")

    # 2) Load a tiny built-in dataset (no external file needed)
    data = load_iris()
    X = data.data
    y = data.target
    log(f"Loaded Iris dataset with {X.shape[0]} samples and {X.shape[1]} features.")

    # 3) Split into train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    log(f"Split into {X_train.shape[0]} train and {X_test.shape[0]} test samples.")

    # 4) Train a simple Logistic Regression model
    model = LogisticRegression(max_iter=200)
    model.fit(X_train, y_train)
    log("Model training completed.")

    # 5) Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    log(f"Test Accuracy: {acc:.4f}")

    # 6) Save metrics to JSON
    metrics_path = os.path.join(OUTPUT_DIR, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "accuracy": acc,
                "classification_report": report,
            },
            f,
            indent=2,
        )
    log(f"Saved metrics to {metrics_path}")

    # 7) Save the trained model
    model_path = os.path.join(OUTPUT_DIR, "model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    log(f"Saved trained model to {model_path}")

    # 8) Save a simple log file
    elapsed = time.time() - start_time
    log(f"⏱️ Total training time: {elapsed:.2f} seconds")

    log_path = os.path.join(OUTPUT_DIR, "training_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    log("✅ Demo training task finished successfully.")

if __name__ == "__main__":
    main()
