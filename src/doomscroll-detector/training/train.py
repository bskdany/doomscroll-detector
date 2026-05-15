import sys
from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

if len(sys.argv) < 2:
    print("Usage: python train.py <feature_matrix.csv>")
    sys.exit(1)

df = pd.read_csv(sys.argv[1])
df = df[df["label"] != "unknown"]

DOOMSCROLLING_LABELS = {"scrolling_home", "scrolling_reels"}

X = df.drop(columns=["label"])
y = df["label"].apply(lambda l: "doomscrolling" if l in DOOMSCROLLING_LABELS else "not_doomscrolling")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

model = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
model.fit(X_train, y_train)

print(classification_report(y_test, model.predict(X_test)))

# Bundle the feature list with the model so inference can validate it matches
# features.py at load time, catching mismatches before they silently corrupt predictions.
artifact = {
    "model": model,
    "features": list(X.columns),
}

out_path = Path(__file__).parent / "model.joblib"
joblib.dump(artifact, out_path)
print(f"Model saved to {out_path}")
print(f"Features: {list(X.columns)}")
