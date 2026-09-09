"""Deployment wiring: read the real configuration, pick the real model, build the app.

    gunicorn --worker-class uvicorn.workers.UvicornWorker inferapi.serve:app

It is cleaner to have a single file rather than putting this in app.py.
"""

from inferapi.app import create_app
from inferapi.config import InferApiSettings
from inferapi.predictor import Predictor, SklearnPredictor


def load_predictor(settings: InferApiSettings) -> Predictor:
    """Build the predictor the settings describe.

    This one is passed the whole configuration. A second backend (a torch model, a
    remote scoring service) is a second implementation and one branch here; nothing
    in app.py changes.
    """
    return SklearnPredictor(settings.serving.model_path, settings.serving.prediction_threshold)


app = create_app(settings=InferApiSettings(), model_loader=load_predictor)
