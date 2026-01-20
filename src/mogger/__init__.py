import toml

from .core import Mogger
from .loki import LokiConfig, LokiLogger

pyproject_conf = toml.load("pyproject.toml")
__version__ = pyproject_conf["project"]["version"]

__all__ = ["Mogger", "LokiConfig", "LokiLogger"]
