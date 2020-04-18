
import numpy as np
from scipy.integrate import odeint
import threading

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

from app import app

from datetime import datetime as dt

from plotly.subplots import make_subplots
import plotly.graph_objects as go


threadLock = threading.Lock()

# Based on model found at https://github.com/omerka-weizmann/2_day_workweek/blob/master/code.ipynb
def SEIR_model(y,t,config,rfunc):
    """
    SEIR model
    @y,t: - variables for the differential equations
    @config: include - rates beta,gamma for differential equations
    @rfunuc: a function that maps time to viral reproduction rate
    """
    S,E,I,R = y
    Tinc,Tinf = config["Tinc"],config["Tinf"]
    Rt = rfunc(t)
    dydt = [-Rt/Tinf * (I*S),
            Rt/Tinf * (I*S) - (1/Tinc)*E,
            (1/Tinc)*E - (1/Tinf)*I,
            (1/Tinf)*I]
    return dydt


OnOffModel = html.Div(children=[
    html.H1(
        children='COVID On/Off Modeling',
        style={
            'textAlign': 'center',
        }
    ),
    html.Div(children=[
        html.P([
            html.Label("Infection Start %: "),
            dcc.Input(
                id='infection-start',
                type="number",
                min=0.0,
                max=1.0,
                step=0.002,
                value=0.002)
        ]),
        html.P([
            html.Label("Incubation Days: "),
            dcc.Input(
                id='incubation-days',
                type="number",
                min=1,
                max=30,
                step=1,
                value=3)
        ]),
        html.P([
            html.Label("Infectious Days: "),
            dcc.Input(
                id='infectious-days',
                type="number",
                min=1,
                max=30,
                step=1,
                value=4)
        ]),
        html.P([
            html.Div(id='lockdown-slider-output-container'),
            dcc.RangeSlider(
                id='lockdown-slider',
                min=0,
                max=14,
                step=1,
                value=[2, 7],
                updatemode="drag")
        ]),
        html.P([
            html.Div(id='rw-slider-output-container'),
            dcc.Slider(
                id='rw-slider',
                min=0,
                max=7.0,
                step=0.05,
                value=2.3,
                updatemode="mouseup"
            )
        ]),
        html.P([
            html.Div(id='rl-slider-output-container'),
            dcc.Slider(
                id='rl-slider',
                min=0,
                max=5.0,
                step=0.05,
                value=1.3,
                updatemode="mouseup"
            )
        ])
    ], style={"width":'200px'}),
    dcc.Graph(id='Graph1')
])


@app.callback(
    dash.dependencies.Output('lockdown-slider-output-container', 'children'),
    [dash.dependencies.Input('lockdown-slider', 'value')])
def update_lockdown_output(value):
    return html.Label('Work days %s, Cycle Days %s' % (value[0], value[1]))

@app.callback(
    dash.dependencies.Output('rw-slider-output-container', 'children'),
    [dash.dependencies.Input('rw-slider', 'value')])
def update_rw_output(value):
    return html.Label('R-Work = "{}"'.format(value))

@app.callback(
    dash.dependencies.Output('rl-slider-output-container', 'children'),
    [dash.dependencies.Input('rl-slider', 'value')])
def update_rl_output(value):
    return html.Label('R-lockdown = "{}"'.format(value))

@app.callback(
    dash.dependencies.Output('Graph1', 'figure'),
    [
        dash.dependencies.Input('infection-start', 'value'),
        dash.dependencies.Input('incubation-days', 'value'),
        dash.dependencies.Input('infectious-days', 'value'),
        dash.dependencies.Input('rw-slider', 'value'),
        dash.dependencies.Input('rl-slider', 'value'),
        dash.dependencies.Input('lockdown-slider', 'value')
    ])

def update_graph_output(startI, Tinc, Tinf, rwValue, rlValue, lockdownValue):
    lockdown = lockdownValue[0]
    period = lockdownValue[1]
    if lockdown == 0:
        rfunc = lambda t: rlValue
    else:
        rfunc = lambda t:  rlValue-(rlValue-rwValue)*((int(t)%period) < lockdown)

    tmax = 30*6
    t = np.linspace(1,tmax,tmax)
    config = {'Tinc': Tinc, 'Tinf': Tinf, 'beta': 0.25, 'gamma': 0.25}
    SEIR_y0 = [1-startI,startI/2,startI/2,0]

    # odeint gets angry is multiple server threads try to do the calculation at the same time
    threadLock.acquire()
    modelOutput = odeint(SEIR_model, SEIR_y0, t, args=(config,rfunc), atol=1e-12, rtol=1e-12)
    threadLock.release()


    fig = make_subplots(rows=4, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.08,
                        subplot_titles=("Susceptible","Exposed", "Infected", "Resistant"))


    fig.add_trace(go.Scatter(x=t, y=modelOutput[:,0]),
                  row=1, col=1)

    fig.add_trace(go.Scatter(x=t, y=modelOutput[:,1]),
                  row=2, col=1)

    fig.add_trace(go.Scatter(x=t, y=modelOutput[:,2]),
                  row=3, col=1)

    fig.add_trace(go.Scatter(x=t, y=modelOutput[:,3]),
                  row=4, col=1)

    fig.update_layout(height=600, width=800,
                      title_text="Projection (Days)")
    return fig
