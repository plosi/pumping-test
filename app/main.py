from shiny import App
from layout import app_ui
from server import server

app = App(app_ui, server)