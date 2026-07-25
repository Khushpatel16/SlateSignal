"""SlateSignal inference service."""

import os

# ONNX Runtime and XGBoost both load OpenMP. A single serving thread avoids
# duplicate-runtime crashes on Apple Silicon and oversubscription in Cloud Run.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

__version__ = "0.1.0"
