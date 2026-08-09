"""Reflex configuration for the reflex-react-flow demo app.

The demo doubles as living documentation and as the target for the Playwright
integration suite (Tech Design §8).
"""

import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="flow_demo",
    disable_plugins=[SitemapPlugin],
    frontend_port=3210,
    backend_port=8210,
)
