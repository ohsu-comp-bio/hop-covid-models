#!/usr/bin/env python


import json
import datetime
import gripql
import plotly.express as px
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html


conn = gripql.Connection("http://localhost:8201")

G = conn.graph("covid")

q = G.query().V().hasLabel("SummaryLocation").has(gripql.eq("province_state", "OR")).as_("a")
q = q.out("summary_reports").as_("b").render(["$a._gid", "$b._data"])

res = list(q)
data = {}
for k, v in res:
    if k not in data:
        data[k] = {}
    date_time_str = v['date']
    try:
        d = datetime.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            d = datetime.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            d = datetime.datetime.strptime(date_time_str, "%m/%d/%y %H:%M")
    data[k][d] = ( v['confirmed'], v['deaths'], v['recovered'] )

mapData = {}
for i in data:
    m = max(data[i].keys())
    mapData[i] = {"fips" : i, "deaths" : data[i][m][0]}
mapDF = pd.DataFrame(mapData).transpose()

with open("geojson-counties-fips.json") as handle:
    counties = json.loads(handle.read())

countiesSub = {"type" : "FeatureCollection", "features":[]}
for c in counties['features']:
    if c['properties']['STATE'] == "41":
        countiesSub['features'].append(c)

fig = px.choropleth_mapbox(mapDF, geojson=countiesSub, locations='fips', color='deaths',
                           color_continuous_scale="Viridis",
                           range_color=(0, 12),
                           mapbox_style="carto-positron",
                           zoom=6, center = {"lat": 44.15, "lon": -120.490556},
                           opacity=0.5,
                           labels={'unemp':'unemployment rate'}
                          )

app = dash.Dash()
app.layout = html.Div([
    dcc.Graph(figure=fig)
])


app.run_server(debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter
