"""Local scenario RAG for Hermes skill_view routing hints."""

import os

os.environ["ANONYMIZED_TELEMETRY"] = "False"

try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass

__version__ = "0.1.0"
