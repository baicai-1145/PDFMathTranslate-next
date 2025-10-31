from __future__ import annotations

import os
import logging


logger = logging.getLogger(__name__)


def patch_onnxruntime_for_gpu_parallel() -> None:
    """Best-effort: prefer GPU EPs and enable parallel execution for all ORT sessions.

    - Providers priority: TensorRT -> CUDA -> CPU
    - Disable thread affinity by default to avoid cpuset warnings
    - Allow tuning with env: P2Z_ORT_INTRA_OP / P2Z_ORT_INTER_OP
    """

    try:
        import onnxruntime as ort  # type: ignore
    except Exception:  # pragma: no cover
        logger.debug("onnxruntime not installed; skip ORT patch")
        return

    os.environ.setdefault("ORT_DISABLE_THREAD_AFFINITY", "1")

    try:
        available = list(ort.get_available_providers())  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        available = []

    preferred: list[str] = []
    if "TensorrtExecutionProvider" in available:
        preferred.append("TensorrtExecutionProvider")
    if "CUDAExecutionProvider" in available:
        preferred.append("CUDAExecutionProvider")
    preferred.append("CPUExecutionProvider")

    OriginalSession = ort.InferenceSession  # type: ignore[attr-defined]

    def _default_sess_options(existing=None):
        try:
            so = existing or ort.SessionOptions()  # type: ignore[attr-defined]
            # Parallel graph execution when possible
            try:
                so.execution_mode = getattr(ort, "ExecutionMode").ORT_PARALLEL  # type: ignore[attr-defined]
            except Exception:
                pass
            intra = int(os.getenv("P2Z_ORT_INTRA_OP", "0") or "0")
            inter = int(os.getenv("P2Z_ORT_INTER_OP", "0") or "0")
            if intra > 0:
                so.intra_op_num_threads = intra
            if inter > 0:
                so.inter_op_num_threads = inter
            return so
        except Exception:  # pragma: no cover
            return existing

    def PatchedInferenceSession(*args, providers=None, sess_options=None, **kwargs):  # type: ignore[no-redef]
        try:
            use_providers = providers or preferred
            so = _default_sess_options(sess_options)
            return OriginalSession(*args, providers=use_providers, sess_options=so, **kwargs)
        except Exception:  # pragma: no cover
            return OriginalSession(*args, providers=providers, sess_options=sess_options, **kwargs)

    try:
        ort.InferenceSession = PatchedInferenceSession  # type: ignore[assignment]
        logger.info(
            "onnxruntime patched: preferred providers=%s, intra=%s, inter=%s",
            preferred,
            os.getenv("P2Z_ORT_INTRA_OP", "0"),
            os.getenv("P2Z_ORT_INTER_OP", "0"),
        )
    except Exception:  # pragma: no cover
        logger.debug("failed to patch onnxruntime", exc_info=True)


__all__ = ["patch_onnxruntime_for_gpu_parallel"]


