from shiny import App, render, reactive, ui
from shiny.types import FileInfo
from shinywidgets import output_widget, render_widget
import shinyswatch

import pandas as pd

from functions import import_data_from_file, calc_drawdown, normal_drawdown_plot

### UI ###

ptest_select = ui.input_selectize(
    id='ptest',
    label='Type of Pumping Test',
    choices=dict(step_drawdown='Step drawdown', constant='Constant', recovery='Recovery'),
    selected=None,
    multiple=False,
)

plot_select = ui.input_selectize(
    id='plot',
    label='Type of Plot',
    choices=dict(normal_dd='Normal Drawdown', semilog_dd='Semi-log Drawdown', normal_wl='Time x Water Level'),
    selected=None,
    multiple=False,
)

file_input = ui.input_file(
    id='filein',
    label='Data file',
    multiple=False,
    accept='.csv',
)

main_tabs = ui.navset_card_tab(
    ui.nav_panel(
        'Data',
        ui.row(
            ui.column(
                6,
                ui.output_data_frame('show_df'),
            ),
            # ui.panel_conditional(
            #     'output.filein',
            #     ui.column(
            #         6,
            #         ui.output_data_frame('show_df')
            #     )
            # ),
            ui.column(
                6,
                ui.panel_conditional(
                    'output.show_df',
                    ui.output_plot('plot_preview')
                ),
            ),
        ),
    ),
    ui.nav_panel(
        'Test',
        ui.panel_conditional(
            'output.show_df',
            ui.row(
                ui.column(
                    3,
                    plot_select,
                    ui.input_switch(
                        id='reverse_y',
                        label='Reverse y-axis',
                        value=True,
                    ),
                    ui.input_text(
                        id='plot_title',
                        label='Chart title',
                        placeholder='Your title here'
                    )
                ),
                # ui.column(
                #     9,
                #     ui.output_plot('plot')
                # ),
            ),
        ),
    )
)

app_ui = ui.page_fluid(
    shinyswatch.theme.united(),
    ui.panel_title(title='HumPumpTest', window_title='Pumping Test App'),
    ui.layout_sidebar(
        ui.sidebar(
            # ptest_select,
            ui.input_radio_buttons(
                id='data_source',
                label='Load data',
                choices=dict(f='From file', m='Manually'),
                selected='f',
            ),
            ui.panel_conditional(
                'input.data_source === "f"',
                file_input,
            ),
            ui.panel_conditional(
                'input.data_source === "m"',
                ui.p('Add your data directly in the table')
            )
        ),
        ui.output_text_verbatim('txt'),
        main_tabs
    ),
)


### Server ###

def server(input, output, session):
    @output
    @render.text
    def txt():
        return f'Plot: {input.plot()}'
    
    @reactive.Calc
    def load_df_from_csv():
        fname: list[FileInfo] = input.filein()
        if not fname:
            return
        df = import_data_from_file(fname[0]['datapath'])
        df['drawdown_m'] = calc_drawdown(df.level_m)
        return df
    
    @output
    @render.data_frame
    def show_df():
        # fname: list[FileInfo] = input.filein()
        # if not fname:
        #     return
        # df = import_data_from_file(fname[0]['datapath'])
        # # if input.ds_toggle:
        # #     df['drawdown_m'] = calc_drawdown(df.level_m)
        # df['drawdown_m'] = calc_drawdown(df.level_m)
        # df.to_csv('_df.csv')

        df = load_df_from_csv()
        return render.DataGrid(df)
    
    @output
    @render.plot()
    def plot_preview():
        # df = pd.read_csv('_df.csv')
        df = load_df_from_csv()
        title = input.plot_title()
        return normal_drawdown_plot(df.time_min, df.level_m, reverse_y=input.reverse_y(), title=title)
        # if input.plot() == 'normal_dd':
        #     return normal_drawdown_plot(df.time_min, df.drawdown_m, reverse_y=input.reverse_y(), title=title)
        # elif input.plot() == 'semilog_dd':
        #     return normal_drawdown_plot(df.time_min, df.drawdown_m, reverse_y=input.reverse_y(), title=title, log_x=True)
        # elif input.plot() == 'normal_wl':
        #     return normal_drawdown_plot(df.time_min, df.level_m, reverse_y=input.reverse_y(), title=title)
    
    @output
    @render.plot()
    def plot():
        # df = pd.read_csv('_df.csv')
        df = load_df_from_csv()
        title = input.plot_title()
        if input.plot() == 'normal_dd':
            return normal_drawdown_plot(df.time_min, df.drawdown_m, reverse_y=input.reverse_y(), title=title)
        elif input.plot() == 'semilog_dd':
            return normal_drawdown_plot(df.time_min, df.drawdown_m, reverse_y=input.reverse_y(), title=title, log_x=True)
        elif input.plot() == 'normal_wl':
            return normal_drawdown_plot(df.time_min, df.level_m, reverse_y=input.reverse_y(), title=title)

    # @output
    # @render.text
    # def df_txt():
    #     fname: list[FileInfo] = input.filein()
    #     if not fname:
    #         return
    #     df = import_data_from_file(fname[0]['datapath'])
    #     return f'Columns: {df.columns}'

app = App(app_ui, server, debug=True)