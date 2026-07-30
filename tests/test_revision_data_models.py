import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from fairai_revision.data import TabularPreprocessor
from fairai_revision.datasets import DATASETS, download_dataset, read_adult_rows
from fairai_revision.models import LogisticRegressionModel, SmallMLPModel


class RevisionDataAndModelTests(unittest.TestCase):
    def test_adult_reader_normalizes_test_label_suffix(self):
        row = (
            "39, Private, 77516, Bachelors, 13, Never-married, Adm-clerical, "
            "Not-in-family, White, Male, 2174, 0, 40, United-States, >50K.\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adult.test"
            path.write_text("| header\n" + row, encoding="utf-8")
            records = read_adult_rows(path, test_file=True)
        self.assertEqual(records[0]["income"], ">50K")

    def test_dataset_download_rejects_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.csv"
            source.write_bytes(b"test-data")
            DATASETS["test_fixture"] = {
                "url": source.as_uri(),
                "sha256": "0" * 64,
                "filename": "fixture.csv",
                "source": "test",
                "license": "test-only",
            }
            try:
                with self.assertRaises(ValueError):
                    download_dataset("test_fixture", Path(tmp) / "data")
            finally:
                DATASETS.pop("test_fixture", None)

    def test_preprocessor_is_fit_on_train_and_handles_unseen_category(self):
        train = pd.DataFrame(
            {"numeric": [1.0, 2.0, 3.0], "category": ["a", "b", "a"]}
        )
        test = pd.DataFrame({"numeric": [4.0], "category": ["unseen"]})
        preprocessor = TabularPreprocessor()
        train_array = preprocessor.fit(train)
        test_array = preprocessor.transform(test)
        self.assertEqual(train_array.shape[1], test_array.shape[1])
        self.assertEqual(len(preprocessor.transformer.named_transformers_["categorical"].categories_[0]), 2)

    def test_logistic_model_interface_and_serialization(self):
        features = np.asarray([[0.0], [1.0], [2.0], [3.0]])
        labels = np.asarray([0, 0, 1, 1])
        model = LogisticRegressionModel(seed=7).train_local(features, labels)
        self.assertEqual(model.predict(features).shape, (4,))
        self.assertEqual(model.predict_proba(features).shape, (4,))
        self.assertGreater(model.parameter_count(), 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = model.serialize(Path(tmp) / "model.joblib")
            restored = LogisticRegressionModel(seed=7).deserialize(path)
            np.testing.assert_array_equal(model.predict(features), restored.predict(features))

    def test_small_mlp_is_deterministic_for_fixed_seed(self):
        features = np.asarray(
            [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]] * 20
        )
        labels = np.asarray([0, 1, 1, 1] * 20)
        first = SmallMLPModel(seed=11, hidden_layers=(4,), max_iter=40).train_local(
            features, labels
        )
        second = SmallMLPModel(seed=11, hidden_layers=(4,), max_iter=40).train_local(
            features, labels
        )
        for left, right in zip(first.get_parameters(), second.get_parameters()):
            np.testing.assert_allclose(left, right)
        restored = SmallMLPModel(seed=11, hidden_layers=(4,), max_iter=40)
        restored.initialize(features.shape[1]).set_parameters(first.get_parameters())
        np.testing.assert_array_equal(first.predict(features), restored.predict(features))


if __name__ == "__main__":
    unittest.main()
