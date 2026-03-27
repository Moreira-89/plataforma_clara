import reflex as rx

config = rx.Config(
    app_name="plataforma_clara",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)