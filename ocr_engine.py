"""Python 3.14-compatible OCR engine.

Official paddlepaddle wheels stop at CPython 3.13 (no cp314). This module runs
PP-OCRv5 through onnxocr + ONNX Runtime, which publishes Python 3.14 wheels and
returns the same result layout as PaddleOCR 2.x:

    result[0] == [[box, (text, confidence)], ...]
"""

from __future__ import annotations

import sys

import cv2
import numpy as np
from onnxocr.onnx_paddleocr import ONNXPaddleOcr

if sys.version_info < (3, 11):
    raise RuntimeError(
        "This application requires Python 3.11 or newer. "
        "Python 3.14 is recommended."
    )

ocr = ONNXPaddleOcr(use_angle_cls=True, use_gpu=False)


def _as_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.ndim == 3 and image.shape[2] == 1:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image


def run_ocr(image: np.ndarray):
    """Run OCR and return PaddleOCR 2.x-style results."""
    return ocr.ocr(_as_bgr(image))
