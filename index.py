#!/usr/bin/env python

# from https://towardsdatascience.com/how-to-build-a-complex-reporting-dashboard-using-dash-and-plotl-4f4257c18a7f

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

# see https://community.plot.ly/t/nolayoutexception-on-deployment-of-multi-page-dash-app-example-code/12463/2?u=dcomfort
from app import server
from app import app
#from layouts import layout_birst_category, layout_ga_category, layout_paid_search, noPage, layout_display, layout_publishing, layout_metasearch
#import callbacks

#from date_selector import DateSelector
#from modelmap import ModelMap
from optimize_panel import OptimizeParams
from on_off_model import OnOffModel

# see https://dash.plot.ly/external-resources to alter header, footer and favicon

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Testing COVID Analysis</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <div>This software is in testing.</div>
    </body>
</html>
'''

app.layout = html.Div([
    dcc.Tabs(id='tabs-example', value='tab-1', children=[
        dcc.Tab(label='Model/Report Comparison', value='tab-1'),
        dcc.Tab(label='On/Off Strategy Modelling', value='tab-2'),
    ]),
    html.Div(id='tabs-example-content')
])

@app.callback(Output('tabs-example-content', 'children'),
              [Input('tabs-example', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            html.H3('Parameter Optimization'),
            OptimizeParams
        ])
    elif tab == 'tab-2':
        return html.Div([
            OnOffModel,
        ])


# # # # # # # # #
external_css = []

#for css in external_css:
#    app.css.append_css({"external_url": css})

external_js = []

#for js in external_js:
#    app.scripts.append_script({"external_url": js})

if __name__ == '__main__':
    app.run_server(debug=True)
