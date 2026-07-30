import json
from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelBinarizer


class FederatedModel(ABC):
    model_type = "abstract"

    @abstractmethod
    def initialize(self, input_dim):
        raise NotImplementedError

    @abstractmethod
    def train_local(self, features, labels):
        raise NotImplementedError

    def evaluate(self, features, labels):
        predictions = self.predict(features)
        return {"accuracy": float(accuracy_score(labels, predictions))}

    @abstractmethod
    def predict(self, features):
        raise NotImplementedError

    @abstractmethod
    def predict_proba(self, features):
        raise NotImplementedError

    def serialize(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.estimator, path)
        return path

    def deserialize(self, path):
        self.estimator = joblib.load(path)
        return self

    @abstractmethod
    def get_parameters(self):
        raise NotImplementedError

    @abstractmethod
    def set_parameters(self, parameters):
        raise NotImplementedError

    def parameter_count(self):
        return int(sum(np.asarray(value).size for value in self.get_parameters()))

    def artifact_size_bytes(self, path):
        return Path(path).stat().st_size


class LogisticRegressionModel(FederatedModel):
    model_type = "logistic_regression"

    def __init__(self, seed=42, max_iter=200):
        self.seed = seed
        self.max_iter = max_iter
        self.estimator = None
        self.input_dim = None

    def initialize(self, input_dim):
        self.input_dim = input_dim
        self.estimator = LogisticRegression(
            max_iter=self.max_iter,
            random_state=self.seed,
            solver="lbfgs",
        )
        return self

    def train_local(self, features, labels):
        if self.estimator is None:
            self.initialize(features.shape[1])
        self.estimator.fit(features, labels)
        return self

    def predict(self, features):
        return self.estimator.predict(features)

    def predict_proba(self, features):
        return self.estimator.predict_proba(features)[:, 1]

    def get_parameters(self):
        return [self.estimator.coef_.copy(), self.estimator.intercept_.copy()]

    def set_parameters(self, parameters):
        coef, intercept = parameters
        self.estimator.coef_ = np.asarray(coef, dtype=float).copy()
        self.estimator.intercept_ = np.asarray(intercept, dtype=float).copy()
        self.estimator.classes_ = np.asarray([0, 1])
        self.estimator.n_features_in_ = self.estimator.coef_.shape[1]
        return self


class SmallMLPModel(FederatedModel):
    model_type = "small_mlp"

    def __init__(self, seed=42, hidden_layers=(32, 16), max_iter=100):
        self.seed = seed
        self.hidden_layers = tuple(hidden_layers)
        self.max_iter = max_iter
        self.estimator = None
        self.input_dim = None

    def initialize(self, input_dim):
        self.input_dim = input_dim
        self.estimator = MLPClassifier(
            hidden_layer_sizes=self.hidden_layers,
            activation="relu",
            solver="adam",
            batch_size=64,
            learning_rate_init=0.001,
            max_iter=self.max_iter,
            random_state=self.seed,
            shuffle=True,
        )
        return self

    def train_local(self, features, labels):
        if self.estimator is None:
            self.initialize(features.shape[1])
        self.estimator.fit(features, labels)
        return self

    def predict(self, features):
        return self.estimator.predict(features)

    def predict_proba(self, features):
        return self.estimator.predict_proba(features)[:, 1]

    def get_parameters(self):
        parameters = []
        for weights, biases in zip(self.estimator.coefs_, self.estimator.intercepts_):
            parameters.extend([weights.copy(), biases.copy()])
        return parameters

    def set_parameters(self, parameters):
        if len(parameters) % 2:
            raise ValueError("MLP parameters must contain weight/bias pairs")
        self.estimator.coefs_ = [
            np.asarray(parameters[index], dtype=float).copy()
            for index in range(0, len(parameters), 2)
        ]
        self.estimator.intercepts_ = [
            np.asarray(parameters[index], dtype=float).copy()
            for index in range(1, len(parameters), 2)
        ]
        self.estimator.n_layers_ = len(self.estimator.coefs_) + 1
        self.estimator.n_outputs_ = 1
        self.estimator.out_activation_ = "logistic"
        self.estimator.classes_ = np.asarray([0, 1])
        self.estimator._label_binarizer = LabelBinarizer().fit(self.estimator.classes_)
        self.estimator.n_features_in_ = self.estimator.coefs_[0].shape[0]
        return self


def create_model(model_type, **kwargs):
    if model_type == "logistic_regression":
        return LogisticRegressionModel(**kwargs)
    if model_type == "small_mlp":
        return SmallMLPModel(**kwargs)
    raise ValueError(f"Unsupported model type: {model_type}")
