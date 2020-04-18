
import datetime
import gripql
import pandas

import numpy as np
from scipy.integrate import odeint
from scipy.optimize import minimize

from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

from app import app


conn = gripql.Connection("http://localhost:8201")
G  = conn.graph("covid")

#get Oregon Counties
q = G.query().V().hasLabel("SummaryLocation").has(gripql.eq("province_state", "OR"))
q = q.render(["$._gid", "$.county"])

countyOptions = list( { "label" : a[1], "value" : a[0] } for a in q )

countyDropDown = dcc.Dropdown(
    id='opt-county-dropdown',
    options=countyOptions,
    value=countyOptions[0]['value']
)

def getCountySummaryReports(fips):
    q = G.query().V(fips).out("summary_reports").render(["date", "confirmed", "deaths", "recovered"])
    return list(q)

def getCountyPopulation(fips):
    q = G.query().V(fips).out("census").has(gripql.eq("gender", None)).render(["population"])
    population = sum(list(a[0] for a in q))
    return population

# Based on model found at https://github.com/omerka-weizmann/2_day_workweek/blob/master/code.ipynb
def SEIR_model(y,t,config):
    """
    SEIR model
    @y,t: - variables for the differential equations
    @config: include - rates beta,gamma for differential equations
    """
    S,E,I,R = y
    Tinc,Tinf = config["Tinc"],config["Tinf"]
    Rt = config["Rt"]
    dydt = [-Rt/Tinf * (I*S),
            Rt/Tinf * (I*S) - (1/Tinc)*E,
            (1/Tinc)*E - (1/Tinf)*I,
            (1/Tinf)*I]
    return dydt

def calc_delta(df, R=3.0, Tinc=3, Tinf=15, startI=0.00005, beta=0.25, gamma=0.25, Toffset=0):
    """
    calc_delta
    @df: county summary report
    @R: replication value
    @Tinc: time-incubation
    @Tinf: time-infection
    @startI: starting infection
    @Toffset: offset of observations (missing days from actual begining)
    """
    tmax = df['days'].max()+1+Toffset
    t = np.linspace(1,tmax,tmax)
    config = {'Rt' : R, 'Tinc': Tinc, 'Tinf': Tinf, 'beta': 0.25, 'gamma': 0.25}
    SEIR_y0 = [1-startI,startI/2,startI/2,0]

    modelOutput = odeint(SEIR_model, SEIR_y0, t, args=(config,), atol=1e-12, rtol=1e-12)
    # exposed + infected + recovered
    modelSums = pandas.DataFrame(modelOutput[:,[1,2,3]]).sum(axis=1)
    # compare to confirmed numbers
    delta = np.sum(np.power(df['confirmed'].values - (modelSums[df['days']+Toffset] * population),2))

    return delta


def optimize_R(df, config):
    return minimize(lambda x: calc_delta(df, R=x[0], **config), (3), bounds=((1,7),), method="L-BFGS-B", options={"ftol":1e-12})



def summaryReportDataFrame(summary_reports):
    data = {}
    for row in summary_reports:
        d = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        data[d] = {"confirmed":int(row[1]), "deaths" : int(row[2]), "recovered":int(row[3])}
    df = pandas.DataFrame(data).transpose().sort_index()
    delta = pandas.Series( (df.index - df.index[0]).round("D").astype('timedelta64[D]'), index=df.index, name="days")
    return df.join(delta)

optimizeGraph = dcc.Graph(id='optimize-graph')

@app.callback(Output('county-data', 'data'),
              [Input('opt-county-dropdown', 'value')])
def updateCountData(value):
    print("Updating counts")
    summary_reports = getCountySummaryReports(value)
    population = getCountyPopulation(value)
    return { "summary_reports" : summary_reports, "population" : population }

@app.callback(Output('model-data', 'data'),
            [Input('opt-r-value', 'value'), Input('opt-infection-start', 'value'),
            Input('opt-incubation-days', 'value'), Input('opt-infectious-days', 'value'),
            Input('opt-offset-days', 'value'),Input("opt-length-days", "value")])
def updateModel(Rt, startI, Tinc, Tinf, Toffset, Tmax):
    print("Running Model")
    t = np.linspace(1,Tmax,Tmax)
    config = {'Rt' : Rt, 'Tinc': Tinc, 'Tinf': Tinf, 'beta': 0.25, 'gamma': 0.25}
    SEIR_y0 = [1-startI,startI/2,startI/2,0]
    modelOutput = odeint(SEIR_model, SEIR_y0, t, args=(config,), atol=1e-12, rtol=1e-12)
    modelSums = pandas.DataFrame(modelOutput[:,[1,2,3]]).sum(axis=1)
    return modelSums.to_list()

@app.callback(Output("optimize-graph", "figure"),
            [Input('county-data', "data"), Input('model-data', "data"),
            Input('opt-offset-days', "value")])
def renderGraph(countyData, modelData, tOffset):
    print("Doing Model Render")
    report = {}
    if countyData is None or modelData is None:
        return {}

    for row in countyData['summary_reports']:
        d = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        report[d] = { "confirmed" : row[1], "deaths" : row[2], "recovered" : row[3] }

    reportDF = pandas.DataFrame(report).transpose().sort_index()
    reportDates = reportDF.index.to_list()

    modelDF = pandas.Series(modelData) * countyData['population']
    modelDates = (pandas.to_timedelta(modelDF.index - tOffset, unit="D") + reportDF.index[0]).to_list()

    return {
        "data" : [{
            "x" : reportDates,
            "y" : list( report[d]["confirmed"] for d in reportDates ),
            "name" : "Total Reported"
        },{
            "x" : modelDates,
            "y" : modelDF.to_list(),
            "name" : "Projection"
        }]
    }


@app.callback(Output("county-population-text", "children"),
            [Input('county-data', "data")])
def renderCountyPopulationText(data):
    p = data.get('population', 0)
    if p is None:
        p = 0
    return html.Label('Population: %d' % (p))

@app.callback(Output("county-infection-text", "children"),
            [Input('opt-infection-start', 'value'), Input('county-data', "data")])
def renderInfectionRate(value, countyData):
    p = countyData.get('population', 0)
    if p is None:
        p = 0
    return html.Label("Starting with %f individuals in county" % (value * p))

inputs = html.Div([
    html.P([
        html.Label("Infection Start %: "),
        dcc.Input(
            id='opt-infection-start',
            type="number",
            min=0.0,
            max=1.0,
            step=0.0000001,
            value=0.00002),
        html.Div(id="county-infection-text")
    ]),
    html.P([
        html.Label("Incubation Days: "),
        dcc.Input(
            id='opt-incubation-days',
            type="number",
            min=1,
            max=30,
            step=1,
            value=3)
    ]),
    html.P([
        html.Label("Infectious Days: "),
        dcc.Input(
            id='opt-infectious-days',
            type="number",
            min=1,
            max=30,
            step=1,
            value=4)
    ]),
    html.P([
        html.Label("R: "),
        dcc.Input(
            id='opt-r-value',
            type="number",
            min=0,
            max=20,
            step=0.1,
            value=2.5)
    ]),
    html.P([
        html.Label("Model Offset Days: "),
        dcc.Input(
            id='opt-offset-days',
            type="number",
            min=0,
            max=30,
            step=1,
            value=0)
    ]),
    html.P([
        html.Label("Model Length: "),
        dcc.Input(
            id='opt-length-days',
            type="number",
            min=10,
            max=360,
            step=1,
            value=30)
    ])
])

OptimizeParams = html.Div([
    dcc.Store("model-data"),
    dcc.Store("county-data"),
    countyDropDown,
    html.Div(id="county-population-text"),
    inputs,
    optimizeGraph
])
