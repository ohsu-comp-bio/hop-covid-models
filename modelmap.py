
import pandas as pd
import json
import gripql
import datetime
import dash_core_components as dcc
import dash_html_components as html
from app import app
import dash
import plotly.express as px
import plotly.graph_objects as go

# https://towardsdatascience.com/build-an-interactive-choropleth-map-with-plotly-and-dash-1de0de00dce0

conn = gripql.Connection("http://localhost:8201")
G = conn.graph("covid")


with open("geojson-counties-fips.json") as handle:
    counties = json.loads(handle.read())

countiesSub = {"type" : "FeatureCollection", "features":[]}
for c in counties['features']:
    if c['properties']['STATE'] == "41":
        countiesSub['features'].append(c)

curDate = "2020-04-14 23:33:31"

q = G.query().V().hasLabel("SummaryLocation").has(gripql.eq("province_state", "OR")).as_("a")
q = q.out("summary_reports").has(gripql.eq("date", curDate)).as_("b")
q = q.render(["$a._gid", "$b.confirmed", "$b.deaths", "$b.recovered"])

mapData = {}
for i in q:
    mapData[i[0]] = {"fips" : i[0], "confirmed" : i[1], "deaths" : i[2], "recovered" : i[3]}
mapDF = pd.DataFrame(mapData).transpose()

fig = px.choropleth_mapbox(mapDF, geojson=countiesSub, locations='fips', color='confirmed',
                           color_continuous_scale="Viridis",
                           range_color=(0, 12),
                           mapbox_style="carto-positron",
                           zoom=6, center = {"lat": 44.15, "lon": -120.490556},
                           opacity=0.5
                          )


q = G.query().V().hasLabel("SummaryLocation").has(gripql.eq("province_state", "OR"))
q = q.render(["$._gid", "$.county"])

countyOptions = list( { "label" : a[1], "value" : a[0] } for a in q )

countyDropDown = dcc.Dropdown(
    id='county-dropdown',
    options=countyOptions,
    value=countyOptions[0]['value']
)

historyGraph = dcc.Graph(id='history-graph')

@app.callback(
    dash.dependencies.Output('history-graph', 'figure'),
    [dash.dependencies.Input('county-dropdown', 'value')])
def update_county_history(value):
    q = G.query().V(value).out("summary_reports")
    q = q.render(["$.date", "$.confirmed", "$.deaths", "$.recovered"])
    data = {}
    for row in q:
        d = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        data[d] = { "confirmed" : row[1], "deaths" : row[2], "recovered" : row[3] }
    dates = sorted(data.keys())
    return {
        "data" : [{
            "x" : dates,
            "y" : list( data[d]["confirmed"] for d in dates )
        }]
    }


ModelMap = html.Div([
    #dcc.Graph(figure=fig),
    countyDropDown,
    historyGraph
])
