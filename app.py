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

file_input = ui.input_file(
    id='filein',
    label='Data file',
    multiple=False,
    accept='.csv',
)

main_tabs = ui.navset_card_tab(
    ui.nav_panel(
        'Home',
        ui.markdown(
            """
            # Hello World
            Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
            incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
            exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure 
            dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
            Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt 
            mollit anim id est laborum.
            ## How to use the app
            1. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
            incididunt ut labore et dolore magna aliqua. 
            2. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip 
            ex ea commodo consequat. 
            3. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
            4. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt 
            mollit anim id est laborum.
            ## References
            - Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
            incididunt ut labore et dolore magna aliqua. 
            - Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip 
            ex ea commodo consequat. 
            - Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
            - Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt 
            mollit anim id est laborum.
            """
        ),
    ),
    ui.nav_panel(
        'Input',
        ui.row(
            ui.column(
                4,
                ui.panel_conditional(
                    'input.ptest',
                    ui.input_numeric(
                        id='static_level',
                        label='Static Water Level [mbd]',
                        value=10.0,
                        min=0,
                        # width='75%'
                    ),
                ),
                ui.panel_conditional(
                    'input.ptest === "step_drawdown"',
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
                    ui.input_numeric(
                        id='end_of_pumping',
                        label='End of Pumping [min]',
                        value=600.0,
                        min=0,
                        # width='75%'
                    ),
                ),
            ),
            ui.column(
                4,
                ui.input_text(
                    id='bh_name',
                    label='Borehole Name',
                    placeholder='BHxx'
                ),
                ui.input_date(
                    id='test_date',
                    label='Date of Test',
                    min='1970-01-01',
                    weekstart=1
                ),
            ),
            ui.column(
                4,
                ui.input_text(
                    id='bh_location',
                    label='Borehole Location (name)',
                    placeholder='Chefe Donsa, Oromia, Ethiopia'
                ),
                ui.input_text(
                    id='bh_gps',
                    label='Borehole Location (GPS)',
                    placeholder='latitude, longitude',
                    # value='0.0, 0.0'
                ),
                ui.input_text(
                    id='operator_name',
                    label='Name of the Operator',
                    placeholder='Jane Doe'
                )
            ),
        ),
    ),
    # ui.panel_conditional(
    #     'output.load_df_from_csv',
    #     ui.nav_panel(
    #         'Data Preview',
    #         ui.row(
    #             ui.column(
    #                 4,
    #                 ui.output_data_frame('show_df'),
    #             ),
    #             ui.column(
    #                 8,
    #                 ui.output_plot('plot_preview')
    #             ),
    #         ),
    #     ),
    #     ui.nav_panel(
    #         'Analysis',
    #         ui.row(
    #             ui.column(
    #                 3,
    #                 ui.panel_conditional(
    #                     'input.ptest === "constant" || input.ptest === "recovery"',
    #                     ui.input_slider(
    #                         id='guess',
    #                         label='Linear fit',
    #                         min=2,
    #                         max=100,# max length of df
    #                         value=15# half length of df
    #                     ),
    #                 ),
    #                 ui.panel_conditional(
    #                     'input.ptest === "step_drawdown"',
    #                 ),
    #                 ui.output_text_verbatim('txt'),
    #             ),
    #             ui.column(
    #                 9,
    #                 ui.panel_conditional(
    #                     'input.ptest === "step_drawdown"',
    #                     ui.output_plot('plot_step'),
    #                 ),
    #                 ui.panel_conditional(
    #                     'input.ptest === "constant" || input.ptest === "recovery"',
    #                     ui.output_plot('plot'),
    #                 ),
    #             ),
    #         ),
    #     ),
    # ),
    ui.nav_panel(
        'Data Preview',
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
                    ),
                    ui.output_text_verbatim('txt'),
                ),
                ui.column(
                    9,
                    ui.panel_conditional(
                        'input.ptest === "step_drawdown"',
                        ui.output_plot('plot_step'),
                    ),
                    ui.panel_conditional(
                        'input.ptest === "constant" || input.ptest === "recovery"',
                        ui.output_plot('plot'),
                    ),
                ),
            ),
        ),
    )
)

app_ui = ui.page_fluid(
    shinyswatch.theme.united(),
    ui.panel_title(title='Pumping Test Analysis for Humanitarians', window_title='Pumping Test Buddy'),
    ui.layout_sidebar(
        ui.sidebar(
            ptest_select,
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
            ),
        ),
        main_tabs,
    ),
)


### Server ###

def server(input, output, session):
    @output
    @render.text
    def txt():
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
            s_Q =dff['s/Q_h/m2']
            tmp = step_test_plot(dff['Q_m3/h'], dff['s/Q_h/m2'])[1]
            B = tmp['B']
            C = tmp['C']
            BQ = tmp['BQ']
            CQ2 = tmp['CQ2']
            dff['eff'] = [round(100*(bq/(bq+cq2)), 2) for bq,cq2 in zip(BQ,CQ2)]

            ## Make a copy of the df to rename the columns for better display
            ## If you don't make a copy it will mess with the reference for the charts --> raise error
            step_df = dff.copy()  
            step_df.columns = ['Time [min]', 'Drawdown [m]', 'Flowrate [m\u00b3/h]', 's/Q [h/m\u00b2]', 'Q/s [m\u00b2/d]', 'Efficiency [%]']
            res = f'y = {C:.3f}\u00b7Q + {B:.3f}\n\n{step_df}\n\ns/Q: Specific Drawdown\nQ/s: Specific Capacity'
        return res

    @reactive.Calc
    def load_df_from_csv():
        fname: list[FileInfo] = input.filein()
        if not fname:
            df = pd.DataFrame(columns=['time_min', 'level_m'])
        else:
            df = import_data_from_file(fname[0]['datapath'])
        df['drawdown_m'] = df.level_m - input.static_level()
        if input.ptest() == 'recovery':
            time = input.end_of_pumping() + df.time_min
            df['t/t\''] = time / df.time_min
        return df
    
    @reactive.Calc
    def get_specific_drawdown():
        df = load_df_from_csv()
        df['drawdown_m'] = df.level_m - input.static_level()
        time = [input[f'end_s{step}']() for step in range(1, input.no_steps()+1)]
        avg_q = [input[f'flowrate_s{step}']() for step in range(1, input.no_steps()+1)]
        ds = []
        for t in time:
            ds.append(df.loc[df.time_min == t, 'drawdown_m'].item())
        spec_ds = [i / j for i,j in zip(ds, avg_q)] # Specific drawdown
        spec_c = [j*24 / i for i,j in zip(ds, avg_q)] # Specific capacity
        return pd.DataFrame(list(zip(time,ds,avg_q,spec_ds,spec_c)), columns=['time_min','ds_m','Q_m3/h','s/Q_h/m2', 'Q/s_m2/d'])

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
        df = load_df_from_csv()
        return render.DataGrid(df)
    
    @output
    @render.plot()
    def plot_preview():
        df = load_df_from_csv()
        bh_name = input.bh_name()
        title = f'Water Level Vs. Time, {bh_name}' if bh_name else 'Water Level Vs. Time'
        vlines = []
        if input.ptest() == 'step_drawdown':
            for step in range(1, input.no_steps()+1):
                vlines.append(input[f'end_s{step}']())
        return preview_plot(df.time_min, df.level_m, reverse_y=input.reverse_y(), title=title, vlines=vlines)
    
    @output
    @render.plot(width=800, height=800)
    def plot_step():
        # df = load_df_from_csv()
        bh_name = input.bh_name()
        if input.ptest() == 'step_drawdown':
            dff = get_specific_drawdown()
            return step_test_plot(dff['Q_m3/h'], dff['s/Q_h/m2'], title=bh_name)[0]
        else:
            return

    @output
    @render.plot()
    def plot():
        df = load_df_from_csv()
        bh_name = input.bh_name()
        title_constant = f'Constant-rate Test, {bh_name}' if bh_name else 'Constant-rate Test'
        title_recovery = f'Recovery Test, {bh_name}' if bh_name else 'Recovery Test'
        guess = input.guess()
        if input.ptest() == 'constant':
            return normal_drawdown_plot(df.time_min, df.drawdown_m, reverse_y=input.reverse_y(), title=title_constant, log_x=True, guess=guess)[0]
        elif input.ptest() == 'recovery':
            return normal_drawdown_plot(df['t/t\''], df.drawdown_m, reverse_y=input.reverse_y(), title=title_recovery, log_x=True, guess=guess)[0]

app = App(app_ui, server, debug=True)