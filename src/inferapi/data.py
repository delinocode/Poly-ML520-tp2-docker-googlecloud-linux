"""Loading, converting and splitting the dataset.

Contains multiple methods and classes pertaining to data management.

Typically, you would split this into subfiles.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

TARGET_COLUMN = "y"
POSITIVE_LABEL = "yes"

LEAKY_COLUMN = "duration"

# We know the values should be in this problem
# Need to also keep in mind future data changes
KNOWN_CATEGORIES: dict[str, list[str]] = {
    "month": ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
    "day_of_week": ["sun", "mon", "tue", "wed", "thu", "fri", "sat"],
}


@dataclass
class Dataset:
    """A dataclass used to represent a Dataset.

    Easier to manipulate than passing a bunch of dataframes
    """

    train_x: pd.DataFrame
    train_y: pd.Series
    val_x: pd.DataFrame
    val_y: pd.Series
    test_x: pd.DataFrame
    test_y: pd.Series


def csv_to_parquet(csv_path: Path, parquet_path: Path) -> Path:
    """Saves a Parquet dataframe from CSV.

    Rather than regenerating the parquet in a notebook, somewhere
    this needs to live. You can add custom logic if you want.
    """
    frame = pd.read_csv(csv_path, sep=";")

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(parquet_path, index=False)

    logger.info(
        "dataset_converted rows=%s csv_bytes=%s parquet_bytes=%s source=%s destination=%s",
        len(frame),
        csv_path.stat().st_size,
        parquet_path.stat().st_size,
        csv_path,
        parquet_path,
    )
    return parquet_path


def load_raw(path: Path) -> pd.DataFrame:
    """Read the dataset. Parquet only: the CSV is the delivery format, not ours."""
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing - download the dataset from Moodle into data/")
    return pd.read_parquet(path)


def to_features_and_labels(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split a raw frame into model inputs and 0/1 labels.

    Returns new objects: a function that quietly empties its caller's dataframe is a
    bug waiting for the second caller.
    """
    labels = (frame[TARGET_COLUMN] == POSITIVE_LABEL).astype(int)
    features = frame.drop(columns=[TARGET_COLUMN, LEAKY_COLUMN], errors="ignore")
    return features, labels


def get_dataset(frame: pd.DataFrame, test_size: float = 0.2, val_size: float = 0.2, seed: int = 0) -> Dataset:
    """Random train/val/test split, stratified on the target.

    We know this dataset has no duplicate clients (no client appears twice in this
    dataset), so a random split does not leak a client from train into test.

    Stratified because roughly one client in nine subscribes: an unstratified split
    can hand you a validation set with a visibly different positive rate, and then the
    metrics move for reasons that have nothing to do with the model.
    """
    assert test_size >= 0 and val_size >= 0
    assert test_size + val_size < 1.0

    features, labels = to_features_and_labels(frame)

    n_test = int(len(frame) * test_size)
    n_val = int(len(frame) * val_size)

    train_x, test_x, train_y, test_y = train_test_split(
        features, labels, test_size=n_test, random_state=seed, stratify=labels
    )

    train_x, val_x, train_y, val_y = train_test_split(
        train_x, train_y, test_size=n_val, random_state=seed, stratify=train_y
    )

    return Dataset(train_x=train_x, train_y=train_y, val_x=val_x, val_y=val_y, test_x=test_x, test_y=test_y)
