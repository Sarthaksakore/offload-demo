# train_decision.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.tree import DecisionTreeClassifier, _tree
import joblib

CSV_PATH = "telemetry_labeled.csv"
MODEL_PATH = "decision_model_lgb.joblib"

FEATURE_COLUMNS = [
    "input_size_bytes",
    "rtt_ms",
    "cpu_percent",
    "battery_percent",
    "is_charging",
    "gpu_available",
]

CSV_COLUMNS = [
    "timestamp",
    "input_size_bytes",
    "local_time_s",
    "cloud_time_s",
    "local_ok",
    "cloud_ok",
    "cloud_http_status",
    "rtt_ms",
    "cpu_percent",
    "battery_percent",
    "is_charging",
    "gpu_available",
    "local_ci_g_per_kwh",
    "cloud_ci_g_per_kwh",
    "local_co2_g",
    "cloud_co2_g",
    "co2_saved_g",
    "co2_saved_pct",
    "offload_better",
]

CARBON_MARGIN = 0.85
TIME_MARGIN = 1.2


def _load_dataframe(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(
        csv_path,
        names=CSV_COLUMNS,
        header=None,
        engine="python",
        skip_blank_lines=True,
    )

    df = df[df["timestamp"] != "timestamp"].copy()

    numeric_cols = FEATURE_COLUMNS + [
        "offload_better",
        "local_co2_g",
        "cloud_co2_g",
        "local_time_s",
        "cloud_time_s",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    missing_label = df["offload_better"].isna()
    if missing_label.any():
        derived = (
            (df.loc[missing_label, "cloud_co2_g"] < df.loc[missing_label, "local_co2_g"] * CARBON_MARGIN)
            & (
                df.loc[missing_label, "cloud_time_s"]
                < df.loc[missing_label, "local_time_s"] * TIME_MARGIN
            )
        ).astype(int)
        df.loc[missing_label, "offload_better"] = derived

    df = df.dropna(subset=FEATURE_COLUMNS + ["offload_better"]).copy()
    df["offload_better"] = df["offload_better"].astype(int)

    return df


def _extract_rules(decision_tree: DecisionTreeClassifier, columns):
    tree_ = decision_tree.tree_
    rules = []

    def recurse(node_id, conditions):
        feature_index = tree_.feature[node_id]
        if feature_index != _tree.TREE_UNDEFINED:
            feature_name = columns[feature_index]
            threshold = float(tree_.threshold[node_id])

            left_condition = conditions + [
                {"feature": feature_name, "op": "<=", "threshold": threshold}
            ]
            right_condition = conditions + [
                {"feature": feature_name, "op": ">", "threshold": threshold}
            ]

            recurse(tree_.children_left[node_id], left_condition)
            recurse(tree_.children_right[node_id], right_condition)
        else:
            value = tree_.value[node_id][0]
            total = value.sum()
            prob = float(value[1] / total) if total else 0.0
            decision = "cloud" if prob >= 0.5 else "local"
            rules.append(
                {
                    "conditions": conditions,
                    "probability": prob,
                    "decision": decision,
                    "samples": int(tree_.n_node_samples[node_id]),
                }
            )

    recurse(0, [])
    return rules


def train_and_save(csv_path: str = CSV_PATH, model_path: str = MODEL_PATH, quiet: bool = False):
    df = _load_dataframe(csv_path)

    if df.empty:
        raise ValueError("No usable telemetry samples found for training")

    if df["offload_better"].nunique() < 2:
        raise ValueError(
            "Need at least two classes in the log data to learn rules. Collect more telemetry with both decisions."
        )

    X = df[FEATURE_COLUMNS]
    y = df["offload_better"]

    X_train, X_test, Y_train, Y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    tree = DecisionTreeClassifier(
        max_depth=3,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
    )
    tree.fit(X_train, Y_train)

    y_prob = tree.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    if not quiet:
        print("Classification report:\n", classification_report(Y_test, y_pred))
        print("ROC AUC:", roc_auc_score(Y_test, y_prob))

    rules = _extract_rules(tree, FEATURE_COLUMNS)

    if not quiet:
        print("\nLearned decision rules:")
        for idx, rule in enumerate(rules, start=1):
            cond_text = " AND ".join(
                f"{c['feature']} {c['op']} {c['threshold']:.4f}" for c in rule["conditions"]
            ) or "<any>"
            print(
                f" Rule {idx}: IF {cond_text} -> {rule['decision']} (p={rule['probability']:.2f}, samples={rule['samples']})"
            )

    bundle = {
        "feature_cols": FEATURE_COLUMNS,
        "rules": rules,
        "tree_model": tree,
    }
    joblib.dump(bundle, model_path)

    if not quiet:
        print(f"\nSaved rule bundle to {model_path}")

    return bundle


if __name__ == "__main__":
    train_and_save()
