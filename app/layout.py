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
        "Introduction",
        ui.div(
            ui.h3("Pumping Test Analysis Tool"),
            ui.p(
                "This tool supports the interpretation of single-well pumping tests "
                "following the ICRC guidelines (2011). It is intended for use by "
                "hydrogeologists and field engineers analysing borehole test data."
            ),
            ui.h4("Supported Test Types"),
            ui.tags.ul(
                ui.tags.li(ui.tags.b("Constant-rate test — "), "Cooper-Jacob straight-line method"),
                ui.tags.li(ui.tags.b("Recovery test — "), "Theis recovery method"),
                ui.tags.li(ui.tags.b("Step-drawdown test — "), "Hantush-Bierschenk method"),
            ),
            ui.h4("How to Use"),
            ui.tags.ol(
                ui.tags.li("Select the test type from the sidebar."),
                ui.tags.li("Enter borehole information (name and static water level are required)."),
                ui.tags.li("Upload your CSV data file. The file must contain columns: time_min and level_m."),
                ui.tags.li("For step-drawdown tests, define the flowrate and end time for each step."),
                ui.tags.li("Click Run Analysis."),
                ui.tags.li("Review the data preview to confirm the file loaded correctly."),
                ui.tags.li("On the Analysis tab, adjust the fit window if needed — aim for R² > 0.95."),
                ui.tags.li("Review the Results and Interpretation tabs."),
                ui.tags.li("Download the report from the Export tab."),
            ),
            ui.h4("CSV File Format"),
            ui.p("Your data file must be a comma-separated CSV with the following columns:"),
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(ui.tags.th("Column"), ui.tags.th("Description"))
                ),
                ui.tags.tbody(
                    ui.tags.tr(ui.tags.td("time_min"), ui.tags.td("Elapsed time since start of test [minutes]")),
                    ui.tags.tr(ui.tags.td("level_m"), ui.tags.td("Water level measured from datum [m below datum]")),
                ),
                class_="table table-bordered w-auto"
            ),
            ui.h4("Reference"),
            ui.p(
                "ICRC (2011). Technical Review — Practical Guidelines for Test Pumping in Water Wells. "
                "International Committee of the Red Cross, Geneva."
            ),
            class_="p-4",
            style="max-width: 800px;"
        ),
        ui.hr(),
        ui.p(
            "Developed by Paolo Losi. "
            "Source code available on ",
            ui.tags.a("GitHub", href="https://github.com/plosi/pumping-test", target="_blank"),
            ". Licensed under MIT.",
            class_="text-muted small"
        ),
    ),
    ui.nav_panel(
        "Data Preview",
        ui.input_switch("preview_scale_plot", "Scale y-axis"),
        ui.output_ui("preview_plot"),
        ui.hr(),
        ui.output_ui("preview_table"),

    ),
    ui.nav_panel(
        "Analysis",
        ui.layout_columns(
            ui.card(
                ui.panel_conditional(
                    "input.test_type === 'constant_rate' || input.test_type === 'recovery'",
                    # First fit
                    ui.p("Fit 1", class_="fw-bold mb-1 text-primary"),
                    ui.input_slider("fit_start", "Start (index)", min=1, max=50, value=1),
                    ui.input_slider("fit_end", "End (index)", min=2, max=100, value=20),
                    ui.hr(),
                    # Second fit toggle + controls
                    ui.panel_conditional(
                        "input.test_type !=='recovery'",
                        ui.input_switch("use_fit2", "Add second fit", value=False),
                        ui.panel_conditional(
                            "input.use_fit2",
                            ui.p("Fit 2", class_="fw-bold mb-1 text-warning"),
                            ui.input_slider("fit2_start", "Start (index)", min=1, max=50, value=1),
                            ui.input_slider("fit2_end", "End (index)", min=2, max=100, value=20),
                        ),
                    ),   
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
            # ui.download_button("dl_csv", "Download results CSV", class_="btn-outline-primary w-100 mb-2"),
            # ui.download_button("dl_plots", "Download plots (.html)", class_="btn-outline-primary w-100 mb-2"),
            ui.download_button("dl_report", "Download report (.docx)", class_="btn-outline-primary w-100"),
        ),
    ),
    id="main_tabs",
)

_footer = ui.div(
    ui.p(
        "Developed by Paolo Losi | ",
        ui.tags.a(
            "github.com/plosi/pumping-test",
            href="https://github.com/plosi/pumping-test",
            target="_blank"
        ),
        " | Based on ICRC (2011) guidelines",
        class_="text-muted small mb-0"
    ),
    class_="text-center py-2 border-top mt-3"
)

# ----------------------------
# Top-level layout
# ----------------------------

app_ui = ui.page_fillable(
    ui.tags.style(
        """
        .navbar, .bslib-sidebar-layout > .sidebar-title {
            background-color: #D32B2B !important;
        }
        .navbar-brand, .navbar-text {
            color: #FFFFFF !important;
        }
        """
    ),
    ui.page_sidebar(
        _sidebar,
        _tabs,
        title="Pumping Test Analysis",
        window_title="Pumping Test",
        theme=shinyswatch.theme.united,
    ),
    _footer,
)
# app_ui = ui.page_sidebar(
#     _sidebar,
#     _tabs,
#     title="Pumping Test Analysis",
#     window_title="Pumping Test",
#     theme=shinyswatch.theme.united
# )