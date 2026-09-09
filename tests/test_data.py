"""Conversion and splitting of the provided data module.

Mainly here to have some tests...
"""

import math

import pandas as pd

from inferapi.data import csv_to_parquet, get_dataset, load_raw, to_features_and_labels
from inferapi.data_stubs import sample_frame


def grow_to_n_rows(frame: pd.DataFrame, n: int) -> pd.DataFrame:
    """Repeat the twelve stub rows until there are enough of them to split."""
    if n <= len(frame):
        return frame.head(n).reset_index(drop=True)

    repeats = math.ceil(n / len(frame))
    return pd.concat([frame] * repeats, ignore_index=True).head(n)


def test_csv_to_parquet_roundtrip(tmp_path):
    csv_path = tmp_path / "raw.csv"
    sample_frame().to_csv(csv_path, sep=";", index=False)

    reloaded = load_raw(csv_to_parquet(csv_path, tmp_path / "raw.parquet"))

    assert list(reloaded.columns) == list(sample_frame().columns)
    assert len(reloaded) == len(sample_frame())


def test_to_features_and_labels_leaves_its_input_alone():
    frame = sample_frame()

    features, labels = to_features_and_labels(frame)

    assert "y" in frame.columns and "duration" in frame.columns
    assert "y" not in features.columns and "duration" not in features.columns
    assert set(labels.unique()) <= {0, 1}


def test_split_sizes_are_shares_of_the_whole_dataset():
    thousand_rows = grow_to_n_rows(sample_frame(), 1_000)

    dataset = get_dataset(thousand_rows, test_size=0.314, val_size=0.186)

    assert len(dataset.train_x) == 500
    assert len(dataset.test_x) == 314
    assert len(dataset.val_x) == 186

    assert len(dataset.train_x) + len(dataset.test_x) + len(dataset.val_x) == len(thousand_rows)
