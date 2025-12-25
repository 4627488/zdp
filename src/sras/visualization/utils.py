"""Utility helpers for visualization exports."""

from __future__ import annotations

import base64
from io import BytesIO

from matplotlib.figure import Figure


def figure_to_png_bytes(figure: Figure) -> bytes:
    """Render a figure to PNG bytes."""

    buffer = BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    return buffer.getvalue()


def figure_to_base64(figure: Figure) -> str:
    """Convert a figure into a base64 data URI."""

    encoded = base64.b64encode(figure_to_png_bytes(figure)).decode("ascii")
    return f"data:image/png;base64,{encoded}"


__all__ = ["figure_to_png_bytes", "figure_to_base64"]
