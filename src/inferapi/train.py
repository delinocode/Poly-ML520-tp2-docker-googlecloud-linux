"""Fit the subscription model, evaluate it and write the artifact.

    make model-train        # or: uv run inferapi train

This is where the notebook's modelling cells land. Every function below ships as a
stub followed by its solution, so you can read the shape you have to fill.
"""

import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from inferapi.config import TrainingConfig
from inferapi.data import KNOWN_CATEGORIES, Dataset, get_dataset
from inferapi.utils import file_creation_time

logger = logging.getLogger(__name__)

NUMERIC_COLUMNS = [
    "age",
    "campaign",
    "pdays",
    "previous",
    "emp.var.rate",
    "cons.price.idx",
    "cons.conf.idx",
    "euribor3m",
    "nr.employed",
]
# Categories we know the full list of up front (see data.KNOWN_CATEGORIES)...
FIXED_CATEGORY_COLUMNS = list(KNOWN_CATEGORIES)
# ...and the ones we have to learn from the rows we were given.
LEARNED_CATEGORY_COLUMNS = [
    "job",
    "marital",
    "education",
    "default",
    "housing",
    "loan",
    "contact",
    "poutcome",
]


def build_model(training: TrainingConfig) -> Pipeline:
    """The whole model: preprocessing and classifier as one artifact."""
    data_processor = ColumnTransformer(
        [
            ("numerical", StandardScaler(), NUMERIC_COLUMNS),
            # Explicit categories: the encoder always produces the twelve month
            # columns and the five weekday columns, whatever the training rows
            # happened to contain. Fit on a June-to-August extract and the model
            # still has a "december" input on the day someone calls in December.
            (
                "categorical_fixed",
                OneHotEncoder(
                    categories=[KNOWN_CATEGORIES[column] for column in FIXED_CATEGORY_COLUMNS],
                    handle_unknown="ignore",
                ),
                FIXED_CATEGORY_COLUMNS,
            ),
            (
                "categorical_learned",
                OneHotEncoder(handle_unknown="infrequent_if_exist"),
                LEARNED_CATEGORY_COLUMNS,
            ),
        ]
    )

    # Named steps are useful
    return Pipeline(
        [
            ("data_processor", data_processor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=training.n_estimators,
                    max_depth=training.max_depth,
                    random_state=training.seed,
                ),
            ),
        ]
    )


def get_model_evaluation_metrics(
    model: Pipeline, x: pd.DataFrame, y: pd.Series, decision_threshold: float = 0.5
) -> dict[str, float]:
    """Score a fitted model on one split.

    Roughly one client in nine subscribes, so accuracy is close to useless here: a
    model that answers "no" every time already scores about 0.89. It is reported
    anyway, next to positive_rate, so the comparison is impossible to miss.

    What we actually care about is the cost of a call. precision answers "of the
    clients we are about to call, how many will subscribe", which is what a campaign
    budget is spent on. recall is the other half of the trade-off, and it moves the
    opposite way when you change the threshold.

    precision and recall describe one operating point (decision_threshold); roc_auc
    and average_precision describe the ranking at every threshold at once, which is
    what you compare across runs when the threshold is still up for discussion.
    average_precision (the area under the precision-recall curve) is the one to
    watch on imbalanced data: roc_auc stays flattering because true negatives are
    abundant and cheap.
    """
    probabilities = model.predict_proba(x)[:, 1]
    predictions = (probabilities >= decision_threshold).astype(int)

    metrics = {
        "positive_rate": float(y.mean()),
        "accuracy": accuracy_score(y, predictions),
        # zero_division=0: a model that never predicts a subscriber has no precision
        "precision": precision_score(y, predictions, zero_division=0),
        "recall": recall_score(y, predictions, zero_division=0),
    }

    # A split with a single class breaks both ranking metrics. It happens on tiny
    # samples, never on the real dataset, and it must not take a sweep down with it.
    if y.nunique() < 2:
        logger.warning("ranking_metrics_skipped: evaluation split holds a single class (rows=%s)", len(y))
    else:
        metrics["roc_auc"] = float(roc_auc_score(y, probabilities))
        metrics["average_precision"] = float(average_precision_score(y, probabilities))

    return metrics


def train(train_config: TrainingConfig, dataset: Dataset) -> Pipeline:
    """Fit the pipeline. Returns the fitted model, and nothing else.

    Evaluating and saving are someone else's job (training_procedure): a function
    that fits, scores and writes to disk cannot be reused by any of the three.
    """
    logger.debug(
        "data_split train_rows=%s val_rows=%s test_rows=%s",
        len(dataset.train_x),
        len(dataset.val_x),
        len(dataset.test_x),
    )

    model = build_model(train_config)
    # from inferapi.torch_model import build_torch_model
    # model = build_torch_model()
    model.fit(dataset.train_x, dataset.train_y)

    return model


def persist_model(model: Pipeline, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)


def training_procedure(
    train_config: TrainingConfig,
    dataframe: pd.DataFrame,
    output_model_path: Path | str,
    overwrite_model: bool = True,
) -> tuple[Pipeline, dict[str, float]]:
    """A whole train + evaluation sequence + hyperopt if necessary"""

    # Transform into Path just in case someone passes a str
    output_model_path = Path(output_model_path)

    # Fail fast
    if not overwrite_model and output_model_path.exists():
        raise FileExistsError(f"{output_model_path} exists and overwrite_model is false")
    if output_model_path.is_dir():
        raise IsADirectoryError(f"Expected a file name for output_model_path. {output_model_path} is a directory")

    dataset = get_dataset(
        dataframe, test_size=train_config.test_size, val_size=train_config.val_size, seed=train_config.seed
    )

    model = train(train_config, dataset=dataset)
    metrics = get_model_evaluation_metrics(
        model, x=dataset.val_x, y=dataset.val_y, decision_threshold=train_config.decision_threshold
    )

    # The metrics go in as one dict rather than one %s per metric: the ranking metrics
    # are absent on a single-class split, and a format string cannot have optional holes.
    # Rounded here only so the line stays readable in a report.
    logger.info(
        "model_trained rows=%s n_estimators=%s max_depth=%s decision_threshold=%s metrics=%s",
        len(dataset.train_x),
        train_config.n_estimators,
        train_config.max_depth,
        train_config.decision_threshold,
        {name: round(value, 4) for name, value in metrics.items()},
    )

    persist_model(model, output_model_path)

    # Good tip to avoid you some headaches in the future:
    # Always log AFTER having done the action
    logger.info(
        "model_persisted artifact=%s model_version=%s",
        output_model_path,
        # Same source of truth as SklearnPredictor.get_version(), so the version in
        # this line is the one the API will report once it loads the file.
        file_creation_time(output_model_path).isoformat(),
    )

    return model, metrics
