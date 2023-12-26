# Pumping test functions

### General imports
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit

### Chart imports
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px



def import_data_from_file(filename):
    # limit to csv files for now
    df = pd.read_csv(filename)
    return df

def calc_drawdown(level:pd.Series):
    ds = level - level[0]
    return ds

def linear(x, a, b):
    """
    x: independent variable
    a,b: parameters
    """
    return a * x + b

def normal_drawdown_plot(t:pd.Series, ds:pd.Series, reverse_y=True, title='Your title here', log_x=False, guess=15, t0=10):
    """
    t: time elapsed
    ds: drawdown in m
    """
    plt.figure(figsize=(20,15))
    
    # t_crop, ds_crop = t[guess:], ds[guess:]
    # popt, pcov = curve_fit(linear, t_crop, ds_crop)
    # m, c = popt[0], popt[1]
    
    # y_fit = m * t + c
    
    ax = sns.scatterplot(
        x=t,
        y=ds
    )
    
    # sns.lineplot(
    #     x=t,
    #     y=y_fit,
    #     color='red',
    #     linewidth=1
    # )

    if reverse_y:
        plt.gca().invert_yaxis()
        plt.xlim(0)
        plt.ylim(top=0)
    else:
        plt.xlim(0)
        plt.ylim(0)
    
    if log_x:
        plt.xscale('log')
        plt.minorticks_on()
        plt.xlim(0)
        # ylim = ax.get_ylim()[1]
        # xlim = np.log(ax.get_xlim()[1])
    
    plt.xlabel('Elapsed time [min]', size=16)
    plt.ylabel('Drawdown [m]', size=16)
    plt.title(f'{title}', size=24)
    
    plt.tight_layout()
    plt.grid()
    
    # plt.savefig(f'{bh_name}_Constant.png')
    # plt.show()
    return ax

def normal_drawdown_plotly(t:pd.Series, ds:pd.Series, reverse_y=True, title='Your title here', log_x=False, guess=15, t0=10):
    """
    t: time elapsed
    ds: drawdown in m
    """
    t = t.astype('float')
    t_crop, ds_crop = np.log(t[1:guess+1]), ds[1:guess+1]
    popt, pcov = curve_fit(linear, t_crop, ds_crop)
    m, c = popt[0], popt[1]
    
    y_fit = m * np.log(t) + c

    fig = px.scatter(
        x=t,
        y=ds,
        labels=dict(x='Elapsed time semi-log [min]' if log_x else 'Elapsed time [min]', y='Drawdown [m]'),
        title=title,
        width=800,
        height=600,
        log_x=log_x
    )

    if log_x:
        fig.add_trace(
            px.line(
                x=t,
                y=y_fit,
                # color='red',
                # linewidth=1
            )
        )

    if reverse_y:
        fig.update_yaxes(
            autorange='reversed',   
        )
    fig.update_yaxes(rangemode='tozero')
    fig.update_xaxes(rangemode='tozero')

    return fig

### TESTING
    
# fname = 'test.csv'
# data = import_data_from_file(fname)
# data['drawdown_m'] = calc_drawdown(data.level_m)
# print(data)

# normal_drawdown_plotly(data.time_min, data.drawdown_m)