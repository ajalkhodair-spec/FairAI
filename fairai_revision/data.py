from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .datasets import ADULT_COLUMNS, read_adult_rows


@dataclass
class RawSplit:
    features: pd.DataFrame
    labels: np.ndarray
    protected: pd.DataFrame


@dataclass
class DatasetSplits:
    train: RawSplit
    validation: RawSplit
    test: RawSplit
    favorable_label: int
    primary_protected_attribute: str
    privileged_value: str
    unprivileged_value: str
    metadata: dict


def _joint_strata(labels, protected):
    return pd.Series(labels).astype(str) + "|" + protected.astype(str).reset_index(drop=True)


def _split_frame(frame, label_column, protected_columns, seed, test_size, validation_size):
    labels = frame[label_column].to_numpy(dtype=int)
    primary = frame[protected_columns[0]]
    train_val, test = train_test_split(
        frame,
        test_size=test_size,
        random_state=seed,
        stratify=_joint_strata(labels, primary),
    )
    relative_validation = validation_size / (1.0 - test_size)
    train, validation = train_test_split(
        train_val,
        test_size=relative_validation,
        random_state=seed + 1,
        stratify=_joint_strata(
            train_val[label_column].to_numpy(dtype=int),
            train_val[protected_columns[0]],
        ),
    )
    return train.reset_index(drop=True), validation.reset_index(drop=True), test.reset_index(drop=True)


def _raw_split(frame, feature_columns, label_column, protected_columns):
    return RawSplit(
        features=frame[feature_columns].copy(),
        labels=frame[label_column].to_numpy(dtype=int),
        protected=frame[protected_columns].copy(),
    )


def load_adult(raw_dir, seed=42):
    raw_dir = Path(raw_dir)
    train_rows = read_adult_rows(raw_dir / "adult.data")
    test_rows = read_adult_rows(raw_dir / "adult.test", test_file=True)
    train_frame = pd.DataFrame(train_rows, columns=ADULT_COLUMNS)
    test_frame = pd.DataFrame(test_rows, columns=ADULT_COLUMNS)
    combined = pd.concat(
        [
            train_frame.assign(_official_split="train"),
            test_frame.assign(_official_split="test"),
        ],
        ignore_index=True,
    )
    before = len(combined)
    combined = combined.replace("?", np.nan).dropna().reset_index(drop=True)
    dropped = before - len(combined)
    numeric = [
        "age",
        "fnlwgt",
        "education_num",
        "capital_gain",
        "capital_loss",
        "hours_per_week",
    ]
    for column in numeric:
        combined[column] = pd.to_numeric(combined[column], errors="raise")
    combined["label"] = (combined["income"] == ">50K").astype(int)

    official_train = combined[combined["_official_split"] == "train"].copy()
    official_test = combined[combined["_official_split"] == "test"].copy()
    train, validation = train_test_split(
        official_train,
        test_size=0.15,
        random_state=seed,
        stratify=_joint_strata(official_train["label"], official_train["sex"]),
    )
    protected_columns = ["sex", "race"]
    excluded = {"income", "label", "_official_split", *protected_columns}
    feature_columns = [column for column in combined.columns if column not in excluded]
    return DatasetSplits(
        train=_raw_split(train.reset_index(drop=True), feature_columns, "label", protected_columns),
        validation=_raw_split(validation.reset_index(drop=True), feature_columns, "label", protected_columns),
        test=_raw_split(official_test.reset_index(drop=True), feature_columns, "label", protected_columns),
        favorable_label=1,
        primary_protected_attribute="sex",
        privileged_value="Male",
        unprivileged_value="Female",
        metadata={
            "dataset": "adult",
            "rows_after_missing_value_exclusion": len(combined),
            "rows_excluded_for_missing_values": dropped,
            "official_test_preserved": True,
            "protected_attributes_excluded_from_features": True,
            "favorable_label_definition": "income >50K",
        },
    )


def load_compas(raw_file, seed=42):
    frame = pd.read_csv(raw_file)
    before = len(frame)
    frame = frame[
        frame["days_b_screening_arrest"].between(-30, 30)
        & (frame["is_recid"] != -1)
        & (frame["c_charge_degree"] != "O")
        & (frame["score_text"] != "N/A")
        & frame["race"].isin(["African-American", "Caucasian"])
    ].copy()
    frame["label"] = 1 - frame["two_year_recid"].astype(int)
    feature_columns = [
        "age",
        "age_cat",
        "juv_fel_count",
        "juv_misd_count",
        "juv_other_count",
        "priors_count",
        "c_charge_degree",
    ]
    protected_columns = ["race", "sex"]
    required = feature_columns + protected_columns + ["label"]
    frame = frame[required].dropna().reset_index(drop=True)
    train, validation, test = _split_frame(
        frame,
        "label",
        protected_columns,
        seed=seed,
        test_size=0.15,
        validation_size=0.15,
    )
    return DatasetSplits(
        train=_raw_split(train, feature_columns, "label", protected_columns),
        validation=_raw_split(validation, feature_columns, "label", protected_columns),
        test=_raw_split(test, feature_columns, "label", protected_columns),
        favorable_label=1,
        primary_protected_attribute="race",
        privileged_value="Caucasian",
        unprivileged_value="African-American",
        metadata={
            "dataset": "compas",
            "rows_before_filtering": before,
            "rows_after_filtering": len(frame),
            "filter": "ProPublica two-year analysis exclusions plus Black/White comparison scope",
            "protected_attributes_excluded_from_features": True,
            "favorable_label_definition": "no recidivism within two years",
        },
    )


class TabularPreprocessor:
    def __init__(self):
        self.transformer = None
        self.feature_names = None

    def fit(self, frame):
        categorical = [
            column
            for column in frame.columns
            if not pd.api.types.is_numeric_dtype(frame[column])
        ]
        numeric = [column for column in frame.columns if column not in categorical]
        self.transformer = ColumnTransformer(
            [
                ("numeric", StandardScaler(), numeric),
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    categorical,
                ),
            ],
            remainder="drop",
            verbose_feature_names_out=True,
        )
        transformed = self.transformer.fit_transform(frame)
        self.feature_names = list(self.transformer.get_feature_names_out())
        return np.asarray(transformed, dtype=float)

    def transform(self, frame):
        if self.transformer is None:
            raise RuntimeError("Preprocessor must be fit on training data first")
        return np.asarray(self.transformer.transform(frame), dtype=float)

