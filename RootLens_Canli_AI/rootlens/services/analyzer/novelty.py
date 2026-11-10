"""Per-service novelty detection fitted exclusively on earlier normal windows."""

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from sklearn.svm import OneClassSVM


MODEL_NAME = "OneClassSVM"
MIN_MODEL_WINDOWS = 6
MAX_MODEL_WINDOWS = 256


@dataclass
class ServiceModel:
    classifier: OneClassSVM
    names: list
    sources: list
    center: np.ndarray
    scale: np.ndarray
    cutoff: float
    training_windows: int

    def score(self, signals):
        if not all(name in signals for name in self.names):
            return None
        values = np.asarray([signals[name][1] for name in self.names])
        decision = float(self.classifier.decision_function([(values - self.center) / self.scale])[0])
        return float(np.clip(1 + (self.cutoff - decision) / 0.10, 0, 4))

    def describe(self):
        return {"training_windows": self.training_windows, "sources": self.sources, "features": self.names}


def fit_models(windows, extract_signals):
    by_service = defaultdict(list)
    for window in windows:
        by_service[window["service"]].append(extract_signals(window))

    models = {}
    for service, examples in by_service.items():
        if len(examples) < MIN_MODEL_WINDOWS:
            continue
        examples = examples[-MAX_MODEL_WINDOWS:]
        names = sorted(set(examples[0]).intersection(*examples[1:]))
        sources = sorted({examples[0][name][0] for name in names})
        if len(sources) < 2:
            continue
        values = np.asarray([[example[name][1] for name in names] for example in examples])
        center = np.median(values, axis=0)
        mad = np.median(np.abs(values - center), axis=0)
        floor = np.asarray([examples[0][name][2] for name in names])
        scale = np.maximum.reduce([3 * mad, np.abs(center) * 0.25, floor])
        standardized = (values - center) / scale
        classifier = OneClassSVM(kernel="rbf", nu=0.10, gamma=1 / len(names))
        classifier.fit(standardized)
        # The display boundary is calibrated only on normal training data.
        cutoff = min(0.0, float(classifier.decision_function(standardized).min())) - 0.01
        models[service] = ServiceModel(classifier, names, sources, center, scale, cutoff, len(examples))
    return models
