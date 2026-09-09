"""Train a model, write it, load it back.

Pondering the question:
Do you think we should be training models during our tests?

Mainly here to have some tests...
"""

from inferapi.config import TrainingConfig
from inferapi.data_stubs import sample_frame
from inferapi.predictor import SklearnPredictor
from inferapi.train import training_procedure


# tmp_path is a directory pytest creates for this test and throws away afterwards.
def test_a_trained_model_can_be_loaded_back(tmp_path):
    artifact = tmp_path / "model.joblib"

    # Twelve rows held in memory: no downloaded dataset, no `make model-train`.
    training_procedure(TrainingConfig(), dataframe=sample_frame(), output_model_path=artifact)

    assert artifact.is_file()
    assert SklearnPredictor(artifact).get_version()
