"""Process-local server state.

The FastAPI process owns the loaded runtime. This is why CLI load/unload calls the
server instead of attempting to retain a model in a short-lived command process.
"""

from tieny.models.service import ModelService
from tieny.runtimes.coordinator import RuntimeCoordinator

models = ModelService()
runtime = RuntimeCoordinator(models)
