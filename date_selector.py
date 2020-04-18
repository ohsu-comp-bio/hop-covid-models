
import gripql
import datetime
import dash_core_components as dcc
import dash_html_components as html
from app import app
import dash

conn = gripql.Connection("http://localhost:8201")
G = conn.graph("covid")

q = G.query().V().hasLabel("SummaryLocation").has(gripql.eq("province_state", "OR")).as_("a")
q = q.out("summary_reports").distinct("date").render("date")
dates = sorted(list( datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S") for d in q ))
labels = list( d.strftime("%Y-%m-%d") for d in dates  )
marks = {}
keys = {}
for i, d in enumerate(labels):
    marks[i] = {'label' : d}
    keys[i] = dates[i].strftime("%Y-%m-%d %H:%M:%S")


DateSelector = html.Div([
    html.Div(id='slider-output-container'),
    dcc.Slider(
        id='date-slider',
        min=0,
        max=len(dates)-1,
        value=len(dates)-1,
        marks=marks,
        included=False
    )
])

@app.callback(
    dash.dependencies.Output('slider-output-container', 'children'),
    [dash.dependencies.Input('date-slider', 'value')])
def update_output(value):
    print(marks)
    return keys[value]
