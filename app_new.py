import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import json
import numpy as np
from dash.dependencies import State, Input, Output
from dash.exceptions import PreventUpdate
from pymongo import MongoClient
import pandas as pd
import os
import re
from copy import deepcopy

PAGE_SIZE = 30

app = dash.Dash(
    __name__,
    meta_tags=[{
        "name":
        "viewport",
        "content":
        "width=device-width, initial-scale=1, maximum-scale=1.0, user-scalable=no",
    }],
)
server = app.server

app.config["suppress_callback_exceptions"] = True

#############################
# Database connect
#############################

with open('./secrets/db_info.json') as json_file:
    db_login = json.load(json_file)
client = MongoClient(
        db_login['host'],
        username=db_login['username'],
        password=db_login['password'],
        authSource=db_login['database'],
        authMechanism='SCRAM-SHA-1')
mongo_coll = client[db_login['database']][db_login['collection']]

show_fields = ['battid', 'average_voltage', 'working_ion',
               'capacity_grav', 'energy_grav',
               'formula_charge',
               'formula_discharge', 'id_charge', 'id_discharge',
               'max_instability']

#############################
# Components
#############################

# Filters
select_working_ion= html.Div([
        html.P(
            className="section-title",
            children=
            "Choose the working ion you are interested in",
        ),
        dcc.Dropdown(value=['Li'],
                     options=[{
                         'label': i,
                         'value': i
                     } for i in ['Li', 'Mg', 'Ca', 'Zn']],
                     multi=True,
                     id='working_ion_select'),
        html.H3(id='output')
    ])

# Scatter plot
scatter_layout = go.Layout(plot_bgcolor="#171b26",
                           paper_bgcolor="#171b26",
                           title="Average Voltage vs. Capacity",
                           xaxis=dict(range=[0, 700],
                                      title='Gravimetric Capacity (mAh/g)'),
                           yaxis=dict(range=[0.9, 5], title='Voltage (V)'),
                           height = 700,
                           showlegend=False,
                           clickmode="event+select",
                           font=dict(family='Courier New, monospace',
                                     size=20,
                                     color='white'),
                           hovermode='closest')

scatter_plot = html.Div(
    className="nine columns",
    children=[
        html.Div(
            children=[
                dcc.Loading(
                    children=dcc.Graph(
                        id="voltage_vs_cap",
                        figure={
                            "data": [],
                            "layout": scatter_layout},
                    ),
                )
            ],
        ),
    ],
)

# Material info


# TODO Table select
table = dash_table.DataTable(
    style_header={
        "fontWeight": "bold",
        "color": "inherit"
    },
    style_as_list_view=True,
    id='table',
    page_size=10,
    page_action='native',
    columns=[{
        "name": i,
        "id": i
    } for i in show_fields],
    data=[],
    style_cell={
        "backgroundColor": "#1e2130",
        "fontFamily": "Open Sans",
        "padding": "0 2rem",
        "color": "darkgray",
        "border": "none",
    },
    css=[
        {
            "selector": "tr:hover td",
            "rule": "color: #91dfd2 !important;"
        },
        {
            "selector": "td",
            "rule": "border: none !important;"
        },
        {
            "selector": ".dash-cell.focused",
            "rule": "background-color: #1e2130 !important;",
        },
        {
            "selector": "table",
            "rule": "--accent: #1e2130;"
        },
        {
            "selector": "tr",
            "rule": "background-color: transparent"
        },
    ],
)


table_load = html.Div(
    className="twelve columns",
    children=[
        html.Div(
            children=[
                dcc.Loading(
                    children=table
                )
            ],
        ),
    ],
)

query_information = html.Div(
    id="query-info",
    className="three columns",
    children=[select_working_ion],
)


# more complex function
def generate_scatter_plot(scatter_data):
    colors = [
        'rgb(67,67,67)', 'rgb(115,115,115)', 'rgb(49,130,189)',
        'rgb(189,189,189)'
    ]
    xx = np.linspace(1, 1000, 100)
    yy_600 = 600 / xx
    yy_900 = 900 / xx

    hover_text = [
        re.sub(r"([A-Za-z\(\)])([\d\.]+)", r"\1<sub>\2</sub>",
               f"{bid}, {fc} -> {fd}") for bid, fc, fd in zip(
                   scatter_data['battid'], scatter_data['formula_charge'],
                   scatter_data['formula_discharge'])
    ]
    data = [
        go.Scatter(mode='markers',
                   x=scatter_data['capacity_grav'],
                   y=scatter_data['average_voltage'],
                   text=hover_text,
                   hoverinfo='text',
                   marker=dict(
                       size=10,
                       color=scatter_data['max_instability'],
                       cmax=0.2,
                       cmin=0,
                       colorscale='Viridis',
                       colorbar=dict(title='E<sub>Hull</sub>'),
                   )),
        go.Scatter(mode='lines',
                   hoverinfo='none',
                   x=xx,
                   y=yy_600,
                   line=dict(color=colors[1], dash='dash')),
        go.Scatter(mode='lines',
                   hoverinfo='none',
                   x=xx,
                   y=yy_900,
                   line=dict(color=colors[1], dash='dash'))
    ]
    return dict(data=data, layout=scatter_layout)


############################
# Application layout
############################
app.layout = html.Div(
    className="container scalable",
    children=[
        # stores
        dcc.Store(id='master_query', storage_type='memory'),
        dcc.Store(id='scatter_data', storage_type='memory'),
        html.Div(
            id="banner",
            className="banner",
            children=[
                html.H6("Matterials Project Battery Explorer"),
                html.Img(src=app.get_asset_url("plotly_logo_white.png")),
            ],
        ),
        html.Div(children=[query_information, scatter_plot], ),
        html.Div(children=[table_load], ),
        #### for debugging
        html.Div(id="query_show"),
    ],
)
############################
# callbacks
############################


@app.callback(Output('master_query',
                     'data'), [Input('working_ion_select', 'value')],
              [State('master_query', 'data')])
def update_callback(value, data):
    print(value, data)
    query = data or {}
    query.update({'working_ion': {"$in": value}})
    return query


@app.callback(Output('scatter_data', 'data'), [Input('master_query', 'data')])
def update_callback(query):
    res_list = list(mongo_coll.find(query, show_fields))
    [ii.pop('_id') for ii in res_list]
    return res_list


@app.callback(Output('voltage_vs_cap', 'figure'),
              [Input('scatter_data', 'data')])
def update_callback(data):
    filtered_data = dict()
    for field_name in show_fields:
        filtered_data[field_name] = [cc[field_name] for cc in data]
    return generate_scatter_plot(filtered_data)


@app.callback(Output('table', 'data'), [Input('scatter_data', 'data')])
def update_callback(data):
    df = pd.DataFrame(data)
    if len(data) == 0:
        return []
    for name_col in ['average_voltage', 'capacity_grav', 'energy_grav', 'max_instability']:
        df[name_col]=df[name_col].map('{:0.2f}'.format)
    return df.to_dict('records')

if __name__ == "__main__":
    app.run_server(debug=True)
