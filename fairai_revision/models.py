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
            warm_start=True,
        )
        self.set_parameters(
            [
                np.zeros((1, input_dim), dtype=float),
                np.zeros(1, dtype=float),
            ]
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


class FederatedLogisticModel(FederatedModel):
    model_type = "federated_logistic_regression"

    def __init__(self, seed=42, epochs=1, learning_rate=0.05, l2=1e-4):
        self.seed = seed
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.l2 = l2
        self.coef = None
        self.intercept = None

    def initialize(self, input_dim):
        self.coef = np.zeros((1, input_dim), dtype=float)
        self.intercept = np.zeros(1, dtype=float)
        return self

    def train_local(self, features, labels):
        features = np.asarray(features, dtype=float)
        labels = np.asarray(labels, dtype=float)
        if self.coef is None:
            self.initialize(features.shape[1])
        for _ in range(self.epochs):
            logits = features @ self.coef[0] + self.intercept[0]
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
            residual = probabilities - labels
            gradient = features.T @ residual / len(features) + self.l2 * self.coef[0]
            intercept_gradient = residual.mean()
            self.coef[0] -= self.learning_rate * gradient
            self.intercept[0] -= self.learning_rate * intercept_gradient
        return self

    def predict(self, features):
        return (self.predict_proba(features) >= 0.5).astype(int)

    def predict_proba(self, features):
        logits = np.asarray(features, dtype=float) @ self.coef[0] + self.intercept[0]
        return 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))

    def serialize(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "schema_version": "fairai.federated_logistic.v1",
                "coef": self.coef,
                "intercept": self.intercept,
                "epochs": self.epochs,
                "learning_rate": self.learning_rate,
                "l2": self.l2,
            },
            path,
        )
        return path

    def deserialize(self, path):
        payload = joblib.load(path)
        if payload.get("schema_version") != "fairai.federated_logistic.v1":
            raise ValueError("Unsupported federated logistic artifact")
        self.coef = np.asarray(payload["coef"], dtype=float)
        self.intercept = np.asarray(payload["intercept"], dtype=float)
        self.epochs = int(payload["epochs"])
        self.learning_rate = float(payload["learning_rate"])
        self.l2 = float(payload["l2"])
        return self

    def get_parameters(self):
        return [self.coef.copy(), self.intercept.copy()]

    def set_parameters(self, parameters):
        coef, intercept = parameters
        self.coef = np.asarray(coef, dtype=float).copy()
        self.intercept = np.asarray(intercept, dtype=float).copy()
        return self


class FederatedMLPModel(FederatedModel):
    model_type = "federated_mlp"

    def __init__(
        self,
        seed=42,
        epochs=1,
        hidden_size=16,
        learning_rate=0.01,
        l2=1e-4,
    ):
        self.seed = seed
        self.epochs = epochs
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.l2 = l2
        self.parameters = None

    def initialize(self, input_dim):
        rng = np.random.default_rng(self.seed)
        input_scale = np.sqrt(2.0 / max(1, input_dim))
        hidden_scale = np.sqrt(2.0 / max(1, self.hidden_size))
        self.parameters = [
            rng.normal(0, input_scale, size=(input_dim, self.hidden_size)),
            np.zeros(self.hidden_size, dtype=float),
            rng.normal(0, hidden_scale, size=(self.hidden_size, 1)),
            np.zeros(1, dtype=float),
        ]
        return self

    def train_local(self, features, labels):
        features = np.asarray(features, dtype=float)
        labels = np.asarray(labels, dtype=float).reshape(-1, 1)
        if self.parameters is None:
            self.initialize(features.shape[1])
        for _ in range(self.epochs):
            w1, b1, w2, b2 = self.parameters
            hidden_linear = features @ w1 + b1
            hidden = np.maximum(hidden_linear, 0)
            logits = hidden @ w2 + b2
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
            output_gradient = (probabilities - labels) / len(features)
            grad_w2 = hidden.T @ output_gradient + self.l2 * w2
            grad_b2 = output_gradient.sum(axis=0)
            hidden_gradient = (output_gradient @ w2.T) * (hidden_linear > 0)
            grad_w1 = features.T @ hidden_gradient + self.l2 * w1
            grad_b1 = hidden_gradient.sum(axis=0)
            self.parameters = [
                w1 - self.learning_rate * grad_w1,
                b1 - self.learning_rate * grad_b1,
                w2 - self.learning_rate * grad_w2,
                b2 - self.learning_rate * grad_b2,
            ]
        return self

    def predict(self, features):
        return (self.predict_proba(features) >= 0.5).astype(int)

    def predict_proba(self, features):
        w1, b1, w2, b2 = self.parameters
        hidden = np.maximum(np.asarray(features, dtype=float) @ w1 + b1, 0)
        logits = (hidden @ w2 + b2).reshape(-1)
        return 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))

    def serialize(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "schema_version": "fairai.federated_mlp.v1",
                "parameters": self.parameters,
                "epochs": self.epochs,
                "hidden_size": self.hidden_size,
                "learning_rate": self.learning_rate,
                "l2": self.l2,
            },
            path,
        )
        return path

    def deserialize(self, path):
        payload = joblib.load(path)
        if payload.get("schema_version") != "fairai.federated_mlp.v1":
            raise ValueError("Unsupported federated MLP artifact")
        self.parameters = [
            np.asarray(value, dtype=float) for value in payload["parameters"]
        ]
        self.epochs = int(payload["epochs"])
        self.hidden_size = int(payload["hidden_size"])
        self.learning_rate = float(payload["learning_rate"])
        self.l2 = float(payload["l2"])
        return self

    def get_parameters(self):
        return [value.copy() for value in self.parameters]

    def set_parameters(self, parameters):
        if len(parameters) != 4:
            raise ValueError("Federated MLP requires W1, b1, W2, and b2")
        self.parameters = [
            np.asarray(value, dtype=float).copy() for value in parameters
        ]
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
    if model_type == "federated_logistic_regression":
        return FederatedLogisticModel(**kwargs)
    if model_type == "federated_mlp":
        return FederatedMLPModel(**kwargs)
    raise ValueError(f"Unsupported model type: {model_type}")
