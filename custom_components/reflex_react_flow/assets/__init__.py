"""Packaged front-end assets (Tech Design DD-004).

This loader lives *inside* the assets directory on purpose: ``rx.asset`` resolves
paths relative to the calling module and creates only that module's folder in the
host app, so a path containing a directory component would symlink into a parent
that was never created.
"""

from __future__ import annotations

import reflex as rx

__all__ = ["event_utils_path"]


def event_utils_path() -> str:
    """Return the served URL of the packaged event helpers.

    Must be called during app compilation: the symlink target lives inside the host
    app's ``assets/`` directory, which does not exist at package import time.

    Returns:
        The public path of ``event_utils.js``, content-hashed by Reflex.
    """
    return rx.asset("event_utils.js", shared=True)
