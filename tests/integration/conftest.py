"""Shared fixtures for the browser suite (T-012).

The suite drives the demo app in a real browser. It does not start the server:
that is the caller's job (`cd flow_demo && uv run reflex run`) or CI's, because a
per-test server start would dominate the runtime and hide flakiness behind
retries. If no server is reachable, the whole suite skips rather than failing —
a missing environment is not a broken contract.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

import pytest

DEMO_URL = os.environ.get("RRF_DEMO_URL", "http://localhost:3210")
BACKEND_URL = os.environ.get("RRF_DEMO_BACKEND_URL", "http://localhost:8210")


def _reachable(url: str, timeout: float = 2.0) -> bool:
    """Return True when `url` answers an HTTP request."""
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except (TimeoutError, urllib.error.URLError, ConnectionError):
        return False


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Give the browser a window tall enough to hold the whole canvas.

    The demo canvas is 560 px tall and sits below a heading and nav, so at
    Playwright's default 1280x720 its lower half — including the controls and
    minimap — falls outside the viewport and the page intercepts pointer events
    aimed at it.
    """
    return {**browser_context_args, "viewport": {"width": 1600, "height": 1200}}


@pytest.fixture(scope="session")
def demo_url() -> str:
    """Base URL of the running demo app, or skip the suite."""
    if not _reachable(DEMO_URL):
        pytest.skip(
            f"demo app not reachable at {DEMO_URL} — "
            "start it with `cd flow_demo && uv run --project .. reflex run`"
        )
    return DEMO_URL


@pytest.fixture
def canvas_page(page, demo_url: str):
    """Open the quickstart page with the canvas mounted and hydrated."""
    page.goto(demo_url, wait_until="networkidle")
    page.wait_for_selector(".react-flow__node", timeout=30_000)
    return page


@pytest.fixture
def debug_page(page, demo_url: str):
    """Open the debug page and reset the event ledger."""
    page.goto(f"{demo_url}/debug", wait_until="networkidle")
    page.wait_for_selector(".react-flow__node", timeout=30_000)
    page.click("[data-testid='reset-counts']")
    return page
