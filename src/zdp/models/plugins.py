"""Plugin model loading via Python entry points.

Plugins can register models by exposing an entry point group:

    [project.entry-points."zdp.models"]
    my_model = "some_pkg.some_module:MyModel"

The entry point object can be either:
- a ReliabilityModel subclass (callable with no args), or
- a factory function returning a ReliabilityModel instance.

"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable, Iterable, List

from .base import ReliabilityModel


ENTRYPOINT_GROUP = "zdp.models"


def load_plugin_model_factories() -> list[Callable[[], ReliabilityModel]]:
    """Discover plugin-provided model factories."""

    factories: List[Callable[[], ReliabilityModel]] = []

    # Python 3.10+ returns EntryPoints with .select
    eps = entry_points().select(group=ENTRYPOINT_GROUP)
    group = list(eps)

    for ep in group:
        try:
            obj = ep.load()
        except Exception:
            continue

        factory = _coerce_factory(obj)
        if factory is not None:
            factories.append(factory)

    return factories


def _coerce_factory(obj: object) -> Callable[[], ReliabilityModel] | None:
    if isinstance(obj, type) and issubclass(obj, ReliabilityModel):
        return lambda: obj()  # type: ignore[misc]
    if callable(obj):
        def _factory() -> ReliabilityModel:
            instance = obj()
            if not isinstance(instance, ReliabilityModel):
                raise TypeError("Plugin factory did not return a ReliabilityModel")
            return instance

        return _factory
    return None


def iter_all_model_factories(
    builtins: Iterable[Callable[[], ReliabilityModel]],
    *,
    include_plugins: bool = True,
) -> list[Callable[[], ReliabilityModel]]:
    factories = list(builtins)
    if include_plugins:
        factories.extend(load_plugin_model_factories())
    return factories


__all__ = [
    "ENTRYPOINT_GROUP",
    "load_plugin_model_factories",
    "iter_all_model_factories",
]
