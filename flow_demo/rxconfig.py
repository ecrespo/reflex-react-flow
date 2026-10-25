"""Reflex configuration for the reflex-react-flow demo app.

The demo doubles as living documentation and as the target for the Playwright
integration suite (Tech Design §8).
"""

import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="flow_demo",
    # The demo pages are built from Radix Themes components; Reflex 0.10 wants that
    # declared rather than detected (implicit enablement is removed in 1.0).
    plugins=[rx.plugins.RadixThemesPlugin()],
    disable_plugins=[SitemapPlugin],
    frontend_port=3210,
    backend_port=8210,
)
