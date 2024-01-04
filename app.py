from shiny import App, render, reactive, ui
from shiny.types import FileInfo
from shinywidgets import output_widget, render_widget
import shinyswatch

import pandas as pd

from functions import import_data_from_file, step_test_plot, normal_drawdown_plot, preview_plot, cooper_jacob, calc_estimated_yield

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
                4,
                ui.output_data_frame('show_df'),
            ),
            ui.column(
                8,
                ui.panel_conditional(
                    'output.show_df',
                    ui.output_plot('plot_preview')
                ),
            ),
        ),
    ),
    ui.nav_panel(
        'Analysis',
        ui.panel_conditional(
            'output.show_df',
            ui.row(
                ui.column(
                    3,
                    # ptest_select,
                    # ui.input_switch(
                    #     id='reverse_y',
                    #     label='Reverse y-axis',
                    #     value=True,
                    # ),
                    # ui.input_text(
                    #     id='plot_title',
                    #     label='Chart title',
                    #     placeholder='Your title here'
                    # ),
                    ui.panel_conditional(
                        'input.ptest === "constant" || input.ptest === "recovery"',
                        ui.input_slider(
                            id='guess',
                            label='Linear fit',
                            min=2,
                            max=100,# max length of df
                            value=15# half length of df
                        ),
                    ),
                    ui.panel_conditional(
                        'input.ptest === "step_drawdown"',
                        # ui.input_numeric(
                        #     id='static_level',
                        #     label='Static Level [mbd]',
                        #     value=10.0,
                        #     min=0,
                        #     width='75%'
                        # ),
                    ),
                    ui.output_text_verbatim('txt'),
                ),
                ui.column(
                    9,
                    ui.output_plot('plot')
                ),
            ),
        ),
    )
)

app_ui = ui.page_fluid(
    shinyswatch.theme.united(),
    ui.panel_title(title='HumPumpTest', window_title='Pumping Test App'),
    ui.layout_sidebar(
        ui.sidebar(
            ptest_select,
            ui.panel_conditional(
                'input.ptest',
                ui.input_numeric(
                    id='static_level',
                    label='Static Level [mbd]',
                    value=10.0,
                    min=0,
                    # width='75%'
                ),
            ),
            ui.panel_conditional(
                'input.ptest === "step_drawdown"',
                # ui.input_numeric(
                #     id='static_level',
                #     label='Static Level [mbd]',
                #     value=10.0,
                #     min=0,
                #     width='75%'
                # ),
                ui.input_slider(
                    id='no_steps',
                    label='Number of Steps',
                    min=2,
                    max=6,
                    value=4
                ),
                ui.output_ui('steps_flow_time'),
            ),
            ui.panel_conditional(
                'input.ptest === "constant" || input.ptest === "recovery"',
                ui.input_numeric(
                    id='flowrate',
                    label='Average Pumping Flowrate [m\u00b3/day]',
                    value=24.0,
                    # width='75%'
                ),
            ),
            ui.panel_conditional(
                'input.ptest === "recovery"',
                # ui.input_numeric(
                #     id='static_level',
                #     label='Static Level [mbd]',
                #     value=10.0,
                #     min=0,
                #     width='75%'
                # ),
                 ui.input_numeric(
                    id='end_of_pumping',
                    label='End of Pumping [min]',
                    value=600.0,
                    min=0,
                    # width='75%'
                ),
            ),
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
            ),
            ui.panel_conditional(
                'output.show_df',
                ui.input_switch(
                    id='reverse_y',
                    label='Reverse y-axis',
                    value=True,
                ),
                ui.input_text(
                    id='plot_title',
                    label='Chart title',
                    placeholder='Your title here'
                ),
            ),
        ),
        main_tabs,
        # ui.output_text_verbatim('txt'),
    ),
)


### Server ###

def server(input, output, session):
    @output
    @render.text
    def txt():
        # return f'Plot: {input.plot()}'
        return get_test_results()

    @reactive.Calc
    def get_test_results():
        res = 'results'
        df = load_df_from_csv()
        guess = input.guess()
        Q = input.flowrate()
        if input.ptest() == 'constant':
            ds = normal_drawdown_plot(df.time_min, df.drawdown_m, guess=guess)[1]['ds']
            T = cooper_jacob(Q, ds)
            y = calc_estimated_yield(T)
            m, c = normal_drawdown_plot(df.time_min, df.drawdown_m, guess=guess)[1]['y_fit_m'], normal_drawdown_plot(df.time_min, df.drawdown_m, guess=guess)[1]['y_fit_c']
            res = f'ds = {m:.3f}\u00b7t + {c:.3f}\n\nQ: {Q:.2f} m\u00b3/day\nds: {ds:.2f} m\nT: {T:.2f} m\u00b2/day\nYield: {y:.2f} m\u00b3/day'
        elif input.ptest() == 'recovery':
            ds = normal_drawdown_plot(df['t/t\''], df.drawdown_m, guess=guess)[1]['ds']
            T = cooper_jacob(Q, ds, recovery=True)
            y = calc_estimated_yield(T)
            m, c = normal_drawdown_plot(df['t/t\''], df.drawdown_m, guess=guess)[1]['y_fit_m'], normal_drawdown_plot(df['t/t\''], df.drawdown_m, guess=guess)[1]['y_fit_c']
            res = f'ds = {m:.3f}\u00b7t + {c:.3f}\n\nQ: {Q:.2f} m\u00b3/day\nds: {ds:.2f} m\nT: {T:.2f} m\u00b2/day\nYield: {y:.2f} m\u00b3/day'
        elif input.ptest() == 'step_drawdown':
            dff = get_specific_drawdown()
            s_Q =dff['s/Q']
            tmp = step_test_plot(dff.Q, dff['s/Q'], reverse_y=input.reverse_y())[1]
            B = tmp['B']
            C = tmp['C']
            BQ = tmp['BQ']
            CQ2 = tmp['CQ2']
            dff['eff'] = [bq/(bq+cq2) for bq,cq2 in zip(BQ,CQ2)]
            res = f'y = {C:.3f}\u00b7Q + {B:.3f}\n\nEffiency: ' + str([round(e*100,2) for e in dff.eff])
        return res

    @reactive.Calc
    def load_df_from_csv():
        fname: list[FileInfo] = input.filein()
        if not fname:
            return
        df = import_data_from_file(fname[0]['datapath'])
        df['drawdown_m'] = df.level_m - input.static_level()#calc_drawdown(df.level_m)
        if input.ptest() == 'recovery':
            # df['residual_ds'] = df.level_m - input.static_level()
            time = input.end_of_pumping() + df.time_min
            df['t/t\''] = time / df.time_min
        return df
    
    @reactive.Calc
    def get_specific_drawdown():
        df = load_df_from_csv()
        time = [input[f'end_s{step}']() for step in range(1, input.no_steps()+1)]
        avg_q = [input[f'flowrate_s{step}']() for step in range(1, input.no_steps()+1)]
        ds = [3.2,8,14.7,19]
        # for t in time:
        #     ds.append(df[df.time_min == t][['drawdown_m']])
        spec_ds = [i / j for i,j in zip(ds, avg_q)]
        return pd.DataFrame(list(zip(time,ds,avg_q,spec_ds)), columns=['time','ds','Q','s/Q'])

    @output
    @render.ui
    def steps_flow_time():
        input_block = []
        ucode = ['\u2081', '\u2082', '\u2083', '\u2084', '\u2085', '\u2086']
        for step in range(1, input.no_steps()+1):
            input_block.append(
                ui.row(
                    ui.column(
                        6,
                        ui.input_numeric(
                            id=f'flowrate_s{step}',
                            label=f'Q{ucode[step-1]} [m\u00b3/h]',
                            value=5.0,
                        ),
                    ),
                    ui.column(
                        6,
                        ui.input_numeric(
                            id=f'end_s{step}',
                            label=f't{ucode[step-1]} [min]',
                            value=120
                        ),
                    )
                )
            )
        return input_block

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
        title = 'Water Level Vs. Time'#input.plot_title()
        vlines = []
        if input.ptest() == 'step_drawdown':
            for step in range(1, input.no_steps()+1):
                vlines.append(input[f'end_s{step}']())
        return preview_plot(df.time_min, df.level_m, reverse_y=input.reverse_y(), title=title, vlines=vlines)
    
    @output
    @render.plot(width=800, height=800)
    def plot():
        # df = pd.read_csv('_df.csv')
        df = load_df_from_csv()
        title = input.plot_title()
        guess = input.guess()
        if input.ptest() == 'step_drawdown':
            dff = get_specific_drawdown()
            return step_test_plot(dff.Q, dff['s/Q'], reverse_y=input.reverse_y(), title=title)[0]
        elif input.ptest() == 'constant':
            return normal_drawdown_plot(df.time_min, df.drawdown_m, reverse_y=input.reverse_y(), title=title, log_x=True, guess=guess)[0]
        elif input.ptest() == 'recovery':
            # df['residual_ds'] = df.level_m - input.static_level()
            return normal_drawdown_plot(df['t/t\''], df.drawdown_m, reverse_y=input.reverse_y(), title=title, log_x=True, guess=guess)[0]

    # @output
    # @render.text
    # def df_txt():
    #     fname: list[FileInfo] = input.filein()
    #     if not fname:
    #         return
    #     df = import_data_from_file(fname[0]['datapath'])
    #     return f'Columns: {df.columns}'

app = App(app_ui, server, debug=True)