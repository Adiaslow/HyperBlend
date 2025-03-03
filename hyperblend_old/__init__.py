"""
HyperBlend - A Natural Compound Database Management System.

This package provides tools for managing and analyzing natural compounds,
their sources, targets, and interactions.
"""

__version__ = "0.1.0"
__author__ = "HyperBlend Team"
__license__ = "MIT"

from hyperblend_old.core.exceptions import HyperBlendError, ValidationError
from hyperblend_old.core.config import Settings

__all__ = ["HyperBlendError", "ValidationError", "Settings"]
