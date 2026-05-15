import sys
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

joblib.dump(model, "model.joblib")
print("Model saved to model.joblib")
