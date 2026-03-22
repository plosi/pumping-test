from shiny import ui
import shinyswatch

# ----------------------------
# Sidebar components
# ----------------------------

_borehole_inputs = ui.div(
    ui.h6("Borehole Info"),
    ui.input_text("borehole_name", "Borehole name", placeholder="BH01"),
    ui.input_numeric("static_level", "Static water level [mbd]", value=10.0, min=0.0),
    ui.input_date("test_date", "Date of test"),
    ui.input_text("operator", "Operator", placeholder="Jane Doe"),
)

_constant_rate_inputs = ui.panel_conditional(
    "input.test_type === 'constant_rate'",
    ui.h6("Constant-Rate Parameters"),
    ui.input_file("cr_file", "Data file (.csv)", accept=".csv"),
    ui.input_numeric("cr_flowrate", "Pumping flowrate [m³/h]", value=1.0, min=0.01),
)

_recovery_inputs = ui.panel_conditional(
    "input.test_type === 'recovery'",
    ui.h6("Recovery Parameters"),
    ui.input_file("r_file", "Data file (.csv)", accept=".csv"),
    ui.input_numeric("r_flowrate", "Pumping flowrate [m³/h]", value=1.0, min=0.01),
    ui.input_numeric("r_end_of_pumping", "End of pumping [min]", value=600.0, min=1.0),
)

_step_drawdown_inputs = ui.panel_conditional(
    "input.test_type === 'step_drawdown'",
    ui.h6("Step-Drawdown Parameters"),
    ui.input_file("sd_file", "Data file (.csv)", accept=".csv"),
    ui.output_ui("step_inputs"),  # dynamic step rows, rendered server-side
    ui.input_action_button(
        "add_step", "Add step",
        class_="btn-outline-secondary btn-sm mt-1 w-100"
    ),
)

_sidebar = ui.sidebar(
    ui.input_select(
        "test_type",
        "Test type",
        choices={
            "constant_rate": "Constant-rate",
            "recovery": "Recovery",
            "step_drawdown": "Step-drawdown",
        },
        selected="constant_rate",
    ),
    ui.hr(),
    _borehole_inputs,
    ui.hr(),
    _constant_rate_inputs,
    _recovery_inputs,
    _step_drawdown_inputs,
    ui.hr(),
    ui.input_action_button(
        "run", "Run Analysis",
        class_="btn-primary w-100"
    ),
    width=320,
)

# ----------------------------
# Main panel tabs
# ----------------------------

_tabs = ui.navset_card_tab(
    ui.nav_panel(
        "Data Preview",
        ui.output_ui("preview_plot"),
    ),
    ui.nav_panel(
        "Analysis",
        ui.layout_columns(
            ui.card(
                ui.card_header("Fit controls"),
                ui.panel_conditional(
                    "input.test_type === 'constant_rate' || input.test_type === 'recovery'",
                    ui.input_slider("fit_start", "Fit start (index)", min=1, max=50, value=1),
                    ui.input_slider("fit_end", "Fit end (index)", min=2, max=100, value=20),
                ),
                ui.output_ui("fit_quality_indicator"),
            ),
            ui.card(
                ui.card_header("Fit plot"),
                ui.output_ui("analysis_plot"),
                ui.panel_conditional(
                    "input.test_type === 'step_drawdown'",
                    ui.output_ui("losses_vs_q_plot")
                )
            ),
            col_widths=[3, 9],
        ),
    ),
    ui.nav_panel(
        "Results",
        ui.output_ui("results_table"),
        ui.hr(),
        ui.output_ui("interpretation_text"),
    ),
    ui.nav_panel(
        "Export",
        ui.card(
            ui.card_header("Download results"),
            ui.download_button("dl_csv", "Download results CSV", class_="btn-outline-primary w-100 mb-2"),
            ui.download_button("dl_plots", "Download plots (.html)", class_="btn-outline-primary w-100 mb-2"),
            ui.download_button("dl_report", "Download report (PDF)", class_="btn-outline-primary w-100"),
        ),
    ),
    id="main_tabs",
)

# ----------------------------
# Top-level layout
# ----------------------------

app_ui = ui.page_sidebar(
    _sidebar,
    _tabs,
    title="Pumping Test Analysis",
    window_title="Pumping Test",
    theme=shinyswatch.theme.united
)