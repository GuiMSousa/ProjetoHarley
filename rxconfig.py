import reflex as rx

from Projeto_HarleyStore.styles.theme import theme_config

config = rx.Config(
    app_name="Projeto_HarleyStore",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(theme=theme_config),
    ]
)