import dash
import dash_table
import dash_auth
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
import crystal_toolkit.components as ctc
from pymatgen import MPRester
from pymatgen.core.structure import Structure
from migration_graph import migration_graph
from pymatgen.core.composition import Composition



## for testing
PAGE_SIZE = 30
DEFAULT_CATION='Li'
DEFAULT_STRUCT='65041_Li'

app = dash.Dash(
    __name__,
    meta_tags=[{
        "name":
        "viewport",
        "content":
        "width=device-width, initial-scale=1, maximum-scale=1.0, user-scalable=no",
    }],
    url_base_pathname='/basf/',
    assets_url_path='/basf'
)
server = app.server

app.config["suppress_callback_exceptions"] = True

#############################
# Database connect
#############################

with open('./secrets/db_info.json') as json_file:
    db_login = json.load(json_file)
# app_login 
VALID_USR_PASS = {
            db_login["dash_name"]: db_login["dash_pass"]
}
auth = dash_auth.BasicAuth(
        app,
        VALID_USR_PASS,
        )
# database login
client = MongoClient(
        db_login['host'],
        username=db_login['username'],
        password=db_login['password'],
        authSource=db_login['database'],
        authMechanism='SCRAM-SHA-1')
mongo_coll = client[db_login['database']][db_login['collection']]
mongo_coll_path = client[db_login['database']][db_login['collection2']]
mongo_coll_mat = client[db_login['database']][db_login['collection3']]
mongo_coll_task = client[db_login['database']][db_login['collection4']]

show_fields = ['battid', 'average_voltage', 'working_ion',
               'capacity_grav', 'energy_grav',
               'formula_charge',
               'formula_discharge', 'id_charge', 'id_discharge',
               'max_instability', 'capacity_vol', 'energy_vol']
info_fields = ['formula_discharge', 'average_voltage', 'capacity_grav', 'capacity_vol', 'energy_grav', 'energy_vol']
name_change = {'formula_discharge': 'Formula',
              'average_voltage': 'Average Voltage',
              'capacity_grav': 'Gravimetric Capacity (mAh/g)',
              'capacity_vol': 'Volumetric Capactiy (Ah/L)',
              'energy_grav': 'Specific Energy (Wh/kg)',
              'energy_vol': 'Energy Density (Wh/L)'}
info_name = ['Formula', 'Average Voltage', 'Gravimetric Capacity (mAh/g)', 'Volumetric Capactiy (Ah/L)', 'Specific Energy (Wh/kg)', 'Energy Density (Wh/L)']
all_element_list = list(mongo_coll.distinct('framework.elements'))
element_select_list = all_element_list.copy()
element_select_list.sort()
element_select_list.insert(0, 'All Elements')


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
        dcc.Dropdown(value=[DEFAULT_CATION],
                     options=[{
                         'label': i,
                         'value': i
                     } for i in ['Li', 'Mg', 'Ca', 'Zn']],
                     multi=True,
                     id='working_ion_select'),
    ])

element_select= html.Div([
        html.P(
            className="section-title",
            children=
            "Choose the element you are interested in",
        ),
        dcc.Dropdown(value=['All Elements'],
                     options=[{
                         'label': i,
                         'value': i
                     } for i in element_select_list],
                     multi=True,
                     id='element_select'),
    ])

formula_query= html.Div([
        html.P(
            className="section-title",
            children=
            "Type in chemical formula",
        ),
        html.Div([
            dcc.Input(id='formula_query', type='text', style={'display':'inline-block'}),
            html.Button(id='query_button_formula', n_clicks=0, children='Query')],
            ),
    ], )

json_query= html.Div([
        html.P(
            className="section-title",
            children=
            "Type in standard json query",
        ),
        html.Div([
            dcc.Input(id='json_query', type='text', style={'display':'inline-block'}),
            html.Button(id='query_button_json', n_clicks=0, children='Query')],
            ),
    ], )

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
    #className="eight columns",
    children=[
        html.Div(
            children=[
                dcc.Loading(
                    children=dcc.Graph(
                        id="voltage_vs_cap",
                        figure={
                            "data": [],
                            "layout": scatter_layout},
                            style={'height': '875px'},
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
    filter_action="native",
    sort_action="native",
    sort_mode="multi",
    # column_selectable="single",
    columns=[{
        "name": i,
        "id": i
    } for i in show_fields[0:10]],
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

property_table = dash_table.DataTable(
    style_header={
        "fontWeight": "bold",
        "color": "inherit"  
    },
    style_as_list_view=True,
    id='property_table',
    page_size=6,
    columns=[{
        "name": i,
        "id": i
    } for i in info_name],
    data=[],
    style_cell={
        "backgroundColor": "#1e2130",
        "fontFamily": "Open Sans",
        "padding": "0 2rem",
        "color": "darkgray",
        "border": "none",
        'maxWidth': '120px',
        'height': '30px',
        'whiteSpace': 'normal',
        'minWidth': '65px',
        #'width': '75px'
        'overflow': 'hidden'
    },
    style_table={
        'overflowX':'scroll'
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



def render_graph(batt_id):
    query_path = {'battid' : batt_id}
    result = list(mongo_coll_path.find(query_path))
    if result and result[0]['intercalating_paths']:
        intercalating_paths = result[0]['intercalating_paths']
        hops = result[0]['hops']
        fss = Structure.from_dict(result[0]['full_sites_struct'])
        bs = Structure.from_dict(result[0]['base_structure'])
        graph_result = migration_graph(intercalating_paths, hops, fss, bs)
    else:
        print('No intercalating path available')
        id_discharge = int(list(mongo_coll.find(query_path))[0]['id_discharge'])
        struct_dict = list(mongo_coll_mat.find({'task_id' : id_discharge}))[0]['structure']
        graph_result = ctc.StructureMoleculeComponent(Structure.from_dict(struct_dict), static=True)
    return graph_result.struct_layout

def formula_query_dict(query_string):
    query_comp = Composition(query_string)
    comp_dict = query_comp.as_dict()
    if 'Li' in comp_dict:
        comp_dict.pop('Li')
    query_comp = Composition.from_dict(comp_dict)
    query_elements = [ielement.name for ielement in query_comp.elements]
    query_regex = [f"(?=.*{query_elements[i]})" for i in range(len(query_elements))]
    query_regex.append('.*')
    query_regex = ''.join(query_regex)
    form_list = mongo_coll.find({"formula_charge": {"$regex" : query_regex}}).distinct("formula_charge")
    result_list = [*filter(lambda x : comp_comp(query_comp, Composition(x)), form_list)]
    return {"formula_charge": {"$in": result_list}}

def comp_comp(comp1, comp2):
    comp_dict_1 = comp1.as_dict()
    if 'Li' in comp_dict_1:
        comp_dict_1.pop('Li')
    comp1_p = Composition.from_dict(comp_dict_1)
    comp_dict_2 = comp2.as_dict()
    if 'Li' in comp_dict_2:
        comp_dict_2.pop('Li')
    comp2_p = Composition.from_dict(comp_dict_2)
    return comp2_p.reduced_formula == comp1_p.reduced_formula

############################
# Application layout
############################
app.layout = html.Div(
    className="container scalable",
    children=[
        # stores
        dcc.Store(id='master_query', storage_type='memory'),
        dcc.Store(id='scatter_data', storage_type='memory'),
        dcc.Store(id='current_click', storage_type='memory'),
        html.Div(
            id="banner",
            className="banner",
            children=[
                html.H6("Matterials Project Battery Explorer"),
                html.Img(src=app.get_asset_url("plotly_logo_white.png")),
            ],
        ),
        html.Div([
            html.Div(className='six columns', style={'height': '900px'},children=[
                html.Div(children=[html.Div([select_working_ion], style={'z-index':'5', 'position': 'relative'})]),
                html.Div(children=[html.Div([element_select])], style={'z-index':'4', 'position': 'relative'}),
                html.Div(children=[html.Div([formula_query], style={'z-index':'3', 'position': 'relative'})]),
                html.Div(children=[html.Div([json_query], style={'z-index':'2', 'position': 'relative'})]),
                html.Div(children=[
                    html.Div(children=[render_graph(DEFAULT_STRUCT)], id='path-graph',
                    style={'height': '400px', 'width': '600px', 'z-index':'1', 'position': 'absolute'}),
                    html.Div(style={'background-color':'#FFFFFF', 'height':'400px', 'width':'600px', 'z-index':'0', 'position':'relative'})
                    ]),
                html.Div(children=[property_table], className='twelve columns',
                style={'display': 'inline-block'})
                ]),
            html.Div(className='six columns', children=[scatter_plot])
            ]),
        html.Div(children=[
            
            
                ]),
        html.Div(children=[table_load], ),
        #### for debugging
        html.Div(id="query_show"),

    ],
)
############################
# callbacks
############################


@app.callback(Output('master_query','data'), 
            [Input('working_ion_select', 'value'),
            Input('element_select', 'value'),
            Input('query_button_formula', 'n_clicks'),
            Input('query_button_json', 'n_clicks')],
            [State('master_query', 'data'),
            State('formula_query', 'value'),
            State('json_query', 'value')])
def update_callback(wi_value, e_value, formula_query_nclicks, json_query_nclicks, data, formula_query_value, json_query_value):
    query = data or {}
    update_list = []

    if wi_value:
        update_list.append({"working_ion": {"$in": wi_value}})

    if e_value:
        if 'All Elements' in e_value:
            e_value = all_element_list
            update_list.append({"framework.elements": {"$in": e_value}})
        else:
            update_list.append({"framework.elements": {"$in": e_value}})

    if formula_query_nclicks and formula_query_value:
        update_list.append(formula_query_dict(formula_query_value))

    if json_query_nclicks and json_query_value:
        update_list.append(eval(json_query_value))
    
    query.update({"$and": update_list})
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
    for field_name in show_fields[0:10]:
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


@app.callback([
                Output('path-graph', 'children'),
                Output('current_click', 'data')
            ],
            [Input('voltage_vs_cap', 'selectedData'),
            Input('voltage_vs_cap', 'clickData'),
            Input('scatter_data', 'data')],
            [State('current_click', 'data')])
def update_migration_path(selectedData, clickData, data, current_click):
    if data:
        if selectedData:
            if clickData != current_click:
                now_click = clickData
                graph_choice = re.findall(r'\d+_[\w]{2}', clickData['points'][0]['text'])[0]
            else:
                now_click = current_click
                graph_choice = re.findall(r'\d+_[\w]{2}', selectedData['points'][0]['text'])[0]
            return render_graph(graph_choice), now_click
        else:
            print('Nothing selected yet')
            return render_graph(DEFAULT_STRUCT), current_click
    else:
        return render_graph(DEFAULT_STRUCT), False


@app.callback(Output('property_table', 'data'), 
            [Input('scatter_data', 'data'),
            Input('voltage_vs_cap', 'selectedData'),
            Input('voltage_vs_cap', 'clickData')])
def update_info_table(data, selectedData, clickData):
    if data:
        if selectedData:
            df = pd.DataFrame(data)
            for name_col in ['average_voltage', 'capacity_grav', 'energy_grav', 'capacity_vol', 'energy_vol']:
                df[name_col]=df[name_col].map('{:0.2f}'.format)
            info_ids = []
            for i in range(0, min(6, len(selectedData['points']))):
                info_choice = re.findall(r'\d+_[\w]{2}', selectedData['points'][i]['text'])[0]
                info_ids.append(info_choice)
            info_dict = df[df['battid'].isin(info_ids)][info_fields].rename(columns=name_change).to_dict('record')
            return info_dict
        else:
            return []
    else:
        return []


if __name__ == "__main__":
    app.run_server(debug=True, port=8000)
