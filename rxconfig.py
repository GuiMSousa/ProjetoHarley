import reflex as rx

from Projeto_HarleyStore.styles.theme import theme_config

config = rx.Config(
    app_name="Projeto_HarleyStore",
    # Loads XANO_* settings from .env when present (see .env.example).
    env_file=".env",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(theme=theme_config),
    ]
)