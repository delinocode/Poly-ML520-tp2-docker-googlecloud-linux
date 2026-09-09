"""HTTP serving for the subscription model.

    make serve          # gunicorn with uvicorn workers (Linux, macOS, WSL2)
    make serve-dev      # plain uvicorn with reload - works everywhere, native Windows included

The application is provided: the routes, the token middleware, the X-Served-By header
and the busy-wait are already wired. Serving is a lab of its own later in the course.
"""

import logging
import os
import random
import socket
import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from secrets import compare_digest

import pandas as pd
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware

from inferapi import __version__
from inferapi.config import InferApiSettings
from inferapi.logging_setup import setup_logging
from inferapi.predictor import Predictor

logger = logging.getLogger(__name__)

# The header an upstream caller (a gateway, another service) uses to name the request.
# We honour it when it is there, and mint one when it is not.
REQUEST_ID_HEADER = "X-Request-ID"


class ApiTokenMiddleware(BaseHTTPMiddleware):
    """Reject calls to the protected prefix that do not carry the right token.

    The token arrives as a constructor argument: this class never reads the
    settings, the environment or a file, which is what makes it testable on its
    own and reusable for any other prefix.
    """

    def __init__(self, app, token: str, protected_prefix: str = "/v1"):
        super().__init__(app)
        self._token = token
        self._protected_prefix = protected_prefix

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith(self._protected_prefix):
            # When doing credentials comparison, always use a constant-time string check
            if not compare_digest(request.headers.get("ML520-API-Key", ""), self._token):
                return JSONResponse({"detail": "missing or invalid ML520-API-Key"}, status_code=401)
        return await call_next(request)


class PredictRequest(BaseModel):
    """One client, raw attributes only - every derived value is computed server-side.

    Aliases carry the dataset's dotted column names, which are not valid Python names.
    `duration` is deliberately absent: it does not exist before the call happens.
    """

    model_config = ConfigDict(populate_by_name=True)

    age: int
    job: str
    marital: str
    education: str
    default: str
    housing: str
    loan: str
    contact: str
    month: str
    day_of_week: str
    campaign: int
    pdays: int
    previous: int
    poutcome: str
    emp_var_rate: float = Field(alias="emp.var.rate")
    cons_price_idx: float = Field(alias="cons.price.idx")
    cons_conf_idx: float = Field(alias="cons.conf.idx")
    euribor3m: float
    nr_employed: float = Field(alias="nr.employed")

    def to_frame(self) -> pd.DataFrame:
        """A single-row frame with the training-time column names."""
        return pd.DataFrame([self.model_dump(by_alias=True)])


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    model_version: str


def _busy_wait(duration_ms: int, random_wait: bool = True) -> None:
    """Burn CPU for `duration_ms`.

    Note this will come in handy in later labs

    Note this is not async since model prediction is not async and consumes CPU cycles.
    """
    if duration_ms == 0.0:
        return

    duration_ms = duration_ms if not random_wait else random.uniform(0, duration_ms)

    logger.debug("busy_wait waiting an additional %.1f ms", duration_ms)
    deadline = time.perf_counter() + duration_ms / 1000
    while time.perf_counter() < deadline:
        pass


def create_app(
    settings: InferApiSettings,
    model_loader: Callable[[InferApiSettings], Predictor],
) -> FastAPI:
    """Build the application.

    Why a predictor_factory?
        1. So that it is easier to run the tests.
        2. So model happens inside the ASGI server, allowing for more control
    """
    # NOTE(LAB): A time where it is acceptable to use print is before logging is setup
    #            api_token is a SecretStr, so it renders masked.
    print("Creating application with settings:", settings)

    setup_logging(settings.logging)

    logger.debug("settings_loaded settings=%s", settings.model_dump(mode="json"))

    # Filled at startup by the lifespan
    predictors: dict[str, Predictor] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        predictors["main"] = model_loader(settings)
        logger.info(
            "model_loaded artifact=%s model_version=%s",
            settings.serving.model_path,
            predictors["main"].get_version(),
        )
        yield
        predictors.clear()

    app = FastAPI(title="inferapi", version=__version__, lifespan=lifespan)

    # Conditionally add the token middleware
    # Added before served_by_header
    # so that header still lands on the 401s this one returns.
    if settings.security.enable_api_key_check:
        # The token is guaranteed to be there: SecurityConfig refuses to validate
        # with the check on and no token.
        app.add_middleware(ApiTokenMiddleware, token=settings.security.api_token.get_secret_value())
    else:
        logger.warning("api_key_check_disabled: /v1 is open to anyone who can reach this process")

    # Which replica answered? On Kubernetes, HOSTNAME is the pod name; locally it falls back to the machine name.
    # You will see the reason in a later lab
    SERVED_BY = os.environ.get("HOSTNAME") or socket.gethostname()

    @app.middleware("http")
    async def served_by_header(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Served-By"] = SERVED_BY
        return response

    # Added last, which makes it the outermost middleware: the id exists before any
    # other code runs, including the 401s the token middleware returns.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        # An id minted upstream is reused, never replaced. That is the whole point: the
        # same request keeps one name across every service it touches.
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/version")
    async def version() -> dict[str, str]:
        # Two different things, both worth knowing when a prediction looks wrong:
        # which code is running, and which weights it loaded.
        return {"app": __version__, "model": predictors["main"].get_version()}

    # A plain def, on purpose: FastAPI runs it in a worker thread, so the CPU burnt
    # by _busy_wait never blocks /healthz on the event loop.
    @app.post("/v1/predict")
    def predict(predict_request: PredictRequest, request: Request) -> PredictResponse:
        predictor = predictors["main"]
        _model_version = predictor.get_version()
        # Put there by request_id_middleware. Threading it by hand into every line is
        # the price of a plain text formatter - and the reason to want better later.
        request_id = request.state.request_id

        started = time.perf_counter()

        logger.debug("prediction_started request_id=%s", request_id)

        _busy_wait(settings.serving.simulate_work_ms)
        label, probability = predictor.predict(predict_request.to_frame())

        ended = time.perf_counter()

        logger.info(
            "predict request_id=%s model_version=%s latency_ms=%.2f prediction=%s probability=%.4f",
            request_id,
            _model_version,
            (ended - started) * 1000,
            label,
            probability,
        )
        return PredictResponse(prediction=label, probability=probability, model_version=_model_version)

    return app
