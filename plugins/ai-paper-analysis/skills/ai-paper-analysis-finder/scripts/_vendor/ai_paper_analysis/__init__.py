"""Deterministic support runtime for the AI Paper Analysis Skills."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ai-paper-analysis")
except PackageNotFoundError:
    __version__ = "0.1.0"
