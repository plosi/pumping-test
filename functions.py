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

# def calc_drawdown(level:pd.Series):
#     ds = level - level[0]
#     return ds

def linear(x, a, b):
    """
    x: independent variable
    a,b: parameters
    """
    return a * x + b

def cooper_jacob(Q:float, ds:float, recovery=False):
    """
    Q: average pumping flowrate [m^3/day]
    ds: drawdown from semi-log chart [m]
    
    Return the aquifer's transmissivity in m^2/day according to Cooper-Jacob's
    formula (semplification of Theis' method):
    T = 0.180*Q/ds
    """
    if not recovery:
        return 0.180 * Q / ds
    else:
        return 0.183 * Q / ds

def calc_estimated_yield(T:float):
    """
    T: transmissivity [m^2/day]
    
    Return the estimated yield of the aquifer in m^3/day, based on MacDonald et al (2005):
    for a borehole supplying 5,000 litres per day, the transmissivity value of the aquifer 
    should be at least 1 m^2/day. An aquifer with a transmissivity of 10 m^2/day would be
    capable of yielding around 40,000 litres per day.
    """
    return 40 * T / 10

def step_test_plot(Q:pd.Series, spec_ds:pd.Series, title=None):
    """
    Q: yield, as input by user
    spec_ds: specific drawdown, calculated as s/Q
    """
    fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(20,15))
    fig.tight_layout()

    Q = Q.astype('float')
    popq, _ = curve_fit(linear, Q, spec_ds)
    c, b = popq[0], popq[1]
    
    y_fit = c * Q + b

    BQ = [b * q for q in Q]
    CQ2 = [c * q**2 for q in Q]
    BQ_CQ2 = [bq+cq2 for bq,cq2 in zip(BQ,CQ2)]

    sns.scatterplot(
        ax=ax[0],
        x=Q,
        y=spec_ds
    )

    sns.lineplot(
        ax=ax[0],
        x=Q,
        y=y_fit,
        color='red',
        linewidth=1,
    )

    sns.lineplot(
        ax=ax[1],
        x=Q,
        y=BQ_CQ2,
        color='blue',
        linewidth=1,
        label='BQ + CQ\u00b2'
    )

    sns.lineplot(
        ax=ax[1],
        x=Q,
        y=BQ,
        color='orange',
        linewidth=1,
        label='BQ'
    )
    
    ax[0].set_xlabel('Yield [m\u00b3/h]', size=14)
    ax[0].set_ylabel('Specific Drawdown [m\u00b2/h]', size=14)
    ax[0].set_title(f'Specific Drawdown Vs. Yield, {title}' if title else 'Specific Drawdown Vs. Yield', size=22)

    ax[1].set_xlabel('Yield [m\u00b3/h]', size=14)
    ax[1].set_ylabel('Drawdown [m]', size=14)
    ax[1].set_title(f'Linear Vs. Non-linear Head Losses, {title}' if title else 'Linear Vs. Non-linear Head Losses', size=22)
    ax[1].legend(loc='best')

    # text = f'{m:.3f}\u00b7t + {c:.3f}'
    # plt.text(x=1.2, y=.2, s=text, horizontalalignment='left', size='large')

    ax[0].grid()
    ax[1].grid()

    d = {
        'B': b,
        'C': c,
        'BQ': BQ,
        'CQ2': CQ2
        }

    return fig, d


def preview_plot(t:pd.Series, ds:pd.Series, reverse_y=True, title='Your title here', vlines=[]):
    """
    t: time elapsed
    ds: drawdown in m
    """
    plt.figure(figsize=(20,15))

    ax = sns.scatterplot(
        x=t,
        y=ds
    )

    if reverse_y:
        plt.gca().invert_yaxis()
        plt.xlim(0)
        plt.ylim(top=0)
    else:
        plt.xlim(0)
        plt.ylim(0)
    
    for x in vlines:
        plt.axvline(x=x, color='red', linestyle='--')
    
    plt.xlabel('Elapsed time [min]', size=14)
    plt.ylabel('Water level [m]', size=14)
    plt.title(f'{title}', size=22)
    
    plt.tight_layout()
    plt.grid()
    
    # plt.savefig(f'{bh_name}_Constant.png')
    # plt.show()
    return ax


def normal_drawdown_plot(t:pd.Series, ds:pd.Series, reverse_y=True, title='Your title here', log_x=False, guess=15, t0=10):
    """
    t: time elapsed
    ds: drawdown in m
    """
    plt.figure(figsize=(20,15))
    
    t = t.astype('float')
    t_crop, ds_crop = np.log(t[1:guess+1]), ds[1:guess+1]
    popt, _ = curve_fit(linear, t_crop, ds_crop)
    m, c = popt[0], popt[1]
    
    y_fit = m * np.log(t) + c

    ax = sns.scatterplot(
        x=t,
        y=ds
    )
    
    sns.lineplot(
        x=t,
        y=y_fit,
        color='red',
        linewidth=1
    )

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
    
    y0 = m * np.log(t0) + c
    y1 = m * np.log(t0*10) + c
    
    ylim = ax.get_ylim()[1]
    xlim = np.log(ax.get_xlim()[1])
    
    plt.axvline(x=t0, ymax=y0/ylim, color='blue', linestyle='--')
    plt.axvline(x=t0*10, ymax=y1/ylim, color='blue', linestyle='--')
    
    plt.axhline(y=y0, xmax=np.log(t0)/xlim, color='blue', linestyle='--')
    plt.axhline(y=y1, xmax=np.log(t0*10)/xlim, color='blue', linestyle='--')
    
    ds = y1 - y0
    
    plt.xlabel('Elapsed time [min]', size=14)
    plt.ylabel('Drawdown [m]', size=14)
    plt.title(f'{title}', size=22)

    # text = f'{m:.3f}\u00b7t + {c:.3f}'
    # plt.text(x=1.2, y=.2, s=text, horizontalalignment='left', size='large')

    plt.tight_layout()
    plt.grid()
    
    d = {
        'ds': ds,
        'y_fit_m': m,
        'y_fit_c': c
        }
    
    # plt.savefig(f'{bh_name}_Constant.png')
    # plt.show()
    return ax, d

# def normal_drawdown_plotly(t:pd.Series, ds:pd.Series, reverse_y=True, title='Your title here', log_x=False, guess=15, t0=10):
#     """
#     t: time elapsed
#     ds: drawdown in m
#     """
#     t = t.astype('float')
#     t_crop, ds_crop = np.log(t[1:guess+1]), ds[1:guess+1]
#     popt, pcov = curve_fit(linear, t_crop, ds_crop)
#     m, c = popt[0], popt[1]
    
#     y_fit = m * np.log(t) + c

#     fig = px.scatter(
#         x=t,
#         y=ds,
#         labels=dict(x='Elapsed time semi-log [min]' if log_x else 'Elapsed time [min]', y='Drawdown [m]'),
#         title=title,
#         width=800,
#         height=600,
#         log_x=log_x
#     )

#     if log_x:
#         fig.add_trace(
#             px.line(
#                 x=t,
#                 y=y_fit,
#                 # color='red',
#                 # linewidth=1
#             )
#         )

#     if reverse_y:
#         fig.update_yaxes(
#             autorange='reversed',   
#         )
#     fig.update_yaxes(rangemode='tozero')
#     fig.update_xaxes(rangemode='tozero')

#     return fig

### TESTING
    
# fname = 'test.csv'
# fname = 'step_test.csv'
# data = import_data_from_file(fname)
# data['drawdown_m'] = data.level_m - 20.95
# print(data)

# normal_drawdown_plotly(data.time_min, data.drawdown_m)

# def get_specific_drawdown(data, no_steps=4):
#     time = [120,240,360,480]
#     avg_q = [4.2,9.8,17.5,22.1]
#     ds = []#[3.2,8,14.7,19]
#     for t in time:
#         ds.append((data.loc[data.time_min == t, 'drawdown_m'].item()))
#     spec_ds = [i / j for i,j in zip(ds, avg_q)]
#     spec_c = [j*24 / i for i,j in zip(ds, avg_q)]
#     return pd.DataFrame(list(zip(time,ds,avg_q,spec_ds,spec_c)), columns=['time_min','ds_m','Q_m3/h','s/Q_h/m2', 'Q/s_m2/d'])

# print(get_specific_drawdown(data))