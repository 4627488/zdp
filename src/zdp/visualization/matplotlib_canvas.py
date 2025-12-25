"""Embedded Matplotlib canvas widgets."""

from __future__ import annotations

from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class MatplotlibCanvas(FigureCanvasQTAgg):
    """Simple FigureCanvas that exposes a helper for drawing callables."""

    def __init__(self, width: float = 5.0, height: float = 4.0, dpi: int = 100) -> None:
        self._figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self._figure)

    def draw_plot(self, builder: Callable[[Figure], None]) -> None:
        """Clear the figure and let the builder populate axes."""

        self.figure.clf()
        builder(self.figure)
        self.draw_idle()
