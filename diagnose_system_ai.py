import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime
import json



# AI-enhanced diagnosis
class AIDiagnoser:
    @staticmethod
    def __init__(self, baseline_data=None):
        self.model = IsolationForest(n_estimators=100, contamination=0.1)
        self.trained = False
        if baseline_data is not None:
            self.train_baseline(baseline_data)

    def train_baseline(self, data):
        X = [self.vectorize(d) for d in data]
        self.model.fit(X)
        self.trained = True

    def vectorize(self, metrics):
        return [
            metrics['cpu_usage'],
            metrics['memory_usage'],
            metrics['disk_latency'],
            metrics['top_process_cpu'] or 0,
            metrics['top_process_memory'] or 0
        ]

    def detect_anomaly(self, metrics):
        if not self.trained:
            return 0, "Model not trained"
        vec = self.vectorize(metrics)
        score = self.model.decision_function([vec])[0]
        is_anomaly = self.model.predict([vec])[0] == -1
        return is_anomaly, score


   

def diagnose_series(self, series):
    timestamps = [entry["timestamp"] for entry in series]
    vectors = [self.vectorize(entry) for entry in series]

    self.model.fit(vectors)
    scores = self.model.decision_function(vectors)
    flags = self.model.predict(vectors)

    results = []
    for i, entry in enumerate(series):
        results.append({
            "timestamp": timestamps[i],
            "anomaly_score": round(scores[i], 4),
            "is_anomaly": flags[i] == -1,
            "cpu": entry.get("cpu_usage", 0),
            "mem": entry.get("memory_usage", 0),
            "trend": "spike" if flags[i] == -1 and scores[i] < -0.2 else "stable"
        })
    return results
     