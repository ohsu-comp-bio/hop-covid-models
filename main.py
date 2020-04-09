#!/usr/bin/env python

import numpy as np
from scipy.integrate import odeint

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

import threading
from datetime import datetime as dt

app = dash.Dash('Covide On/Off Modeling')

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


app.layout = html.Div(children=[
    html.H1(
        children='COVID On/Off Modeling',
        style={
            'textAlign': 'center',
        }
    ),
    html.Div(children=[
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
                max=5.0,
                step=0.05,
                value=2.3,
                updatemode="drag"
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
                updatemode="drag"
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
        dash.dependencies.Input('rw-slider', 'value'),
        dash.dependencies.Input('rl-slider', 'value'),
        dash.dependencies.Input('lockdown-slider', 'value')
    ])

def update_graph_output(rwValue, rlValue, lockdownValue):
    lockdown = lockdownValue[0]
    period = lockdownValue[1]
    if lockdown == 0:
        rfunc = lambda t: rlValue
    else:
        rfunc = lambda t:  rlValue-(rlValue-rwValue)*((int(t)%period) < lockdown)

    tmax = 30*4
    t = np.linspace(1,tmax,tmax)
    config = {'Tinc': 3, 'Tinf': 4, 'beta': 0.25, 'gamma': 0.25}
    INIT_SUSCEPTIBLE = 0.002
    SEIR_y0 = [1-INIT_SUSCEPTIBLE,INIT_SUSCEPTIBLE/2,INIT_SUSCEPTIBLE/2,0]

    # odeint gets angry is multiple server threads try to do the calculation at the same time
    threadLock.acquire()
    modelOutput = odeint(SEIR_model, SEIR_y0, t, args=(config,rfunc), atol=1e-12, rtol=1e-12)
    threadLock.release()

    return {
        'data': [
            {'x': t, 'y': modelOutput[:,0], 'type': 'line', 'name': 'Susceptible'},
            {'x': t, 'y': modelOutput[:,1], 'type': 'line', 'name': 'Exposed'},
            {'x': t, 'y': modelOutput[:,2], 'type': 'line', 'name': 'Infected'},
            {'x': t, 'y': modelOutput[:,3], 'type': 'line', 'name': 'Resistant'},
        ],
        'layout': {
            'title': 'Model'
        }
    }


if __name__ == '__main__':
    app.run_server()
