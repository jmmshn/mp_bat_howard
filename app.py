import dash, dash_auth
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd
import numpy as np
import json
import plotly.graph_objs as go
from pymongo import MongoClient
import yaml
import crystal_toolkit.components as ctc
from fetch_path import fetch_path
import warnings


with open('.:secrets:db_info.json') as json_file:
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


app = dash.Dash(__name__, url_base_pathname='/vw/')
app.config['suppress_callback_exceptions']=True

# Authentication
VALID_UP = [
    [db_login['dash_name'],  db_login['dash_pass']],
]
auth = dash_auth.BasicAuth(app, VALID_UP)

server = app.server

PAGE_SIZE = 20

doris_dict = {  'position': 'relative',
                'top': '0px',
                'left': '10px',
                'font-family': 'Dosis',
                'display': 'inline',
                'font-size': '6.0rem',
                'color': '#4D637F'
             }



# General formatting of the app
def get_app_layout():
    return html.Div([
        # Row: Header and Intro text
        html.Div([
            html.Img(src="https://discuss.materialsproject.org/uploads/default/original/1X/a896ccafffcaac1a50c18818e0e3a2462423149e.png",
                     style={
                         'height': '150px',
                         'float': 'right',
                         'position': 'relative',
                         'bottom': '40px',
                         'left': '50px'
                     },
                     ),
            html.H2('Dash ',
                    style=doris_dict),
            html.H2('for',
                    style=doris_dict),
            html.H2(' Battery Discovery',
                    style=doris_dict),
        ], className='row twelve columns', style={'position': 'relative', 'right': '15px'}),
        # Row: Description
        html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        'Please Eneter Query Here:',
                        dcc.Input(id='query_string', value='''{'working_ion' : {'$in': ['Li']}}''', type='text', size='30'),
                        html.Button(id='query_button', n_clicks=0, children='Query'),
                        html.Button(id='graph_button', n_clicks=0, children='Update/Clear Graph')
                    ]),
                    html.P(
                        'HOVER over a point in the graph to see its basic information. CLICK on a point in the graph to display it in the table below.'),
                    html.P(
                        'The oxidation states predicted belows is a "best guess" bases on common oxidation state.')
                ], style={'margin-left': '10px'}),
                #draw_dropdown(),  # DROPDOWN  #####
            ], className='twelve columns')
        ], className='row'),
        # Row: Figure
        html.Div(
            [html.Div(
                style = {'alignVertical': 'center'},
                id='mat_info',
                children='PlaceHolder',
                className='three columns'),
            html.Div([
                dcc.Graph(id='clickable-graph',
                          style=dict(width='900px'),
                          hoverData=dict(points=[dict(pointNumber=0)]),
                          figure=draw_figure(get_df({'working_ion' : {'$in': ['Li']}}))),
            ], className='nine  columns')
        ], className='row'),
        #Row: Path graph
        html.Div(
            [html.Div(children='Migration Path Graph')
        ], className='row'),
        html.Div(
            [html.Div(get_path_graph('439_Li'), id='path-graph', style = {"width": "75vw", "height": "75vh"})
        ], className='row'),
        #ids should work: 12240_Li, 439_Li
        #tables and hidden divs
        html.Div([
            html.Div([
                html.Div(id = 'tab_selected', style={'display': 'none'}),
                #html.Div(id = 'hidden-div'),
                html.Div(id = 'hidden-div',
                         #, style = {'display': 'none'}),
                         ),
                html.Div(id='hidden_df', children=get_df({'working_ion' : {'$in': ['Li']}}), style= {'display': 'none'}),
                html.Div(id='current_selection',
                         )
            ], className='twelve columns')
        ], className='row'),
    ], className='container')


html.Div(
    id='df'
)

##########################################################################
# The different dynamic elements in the app each writen as a function
##########################################################################
def draw_figure(df):
    """
    Return the figure data based on some filters
    :param selected_idx:
    :return:
    """
    dff = pd.read_json(df)
    colors = ['rgb(67,67,67)', 'rgb(115,115,115)', 'rgb(49,130,189)', 'rgb(189,189,189)']
    xx = np.linspace(1,1000,100)
    yy_600 = 600/xx
    yy_900 = 900/xx
    data = [
        #First layer is the selected data for halo effect
        go.Scatter(mode = 'markers',
                   x = [],
                   y = [],
                   hoverinfo = 'none',
                   marker = dict(
                       size = 15,
                       #color='rgb(231, 99, 250)',
                       color='rgb(0, 0, 0)'
                   )
                ),
        go.Scatter(mode = 'markers',
            x = dff['capacity_grav'],
            y = dff['average_voltage'],
            text = dff['battid'],
            customdata = ['info'],
            hoverinfo = 'text',
            marker = dict(
                size = 10,
                color = dff['max_instability'],
                cmax=0.2,
                cmin=0,
                colorscale='Viridis',
                colorbar=dict(
                    title='E<sub>Hull</sub>'
                ),
            )
        ),
        go.Scatter(mode = 'lines', hoverinfo='none',
            x = xx,
            y = yy_600, line=dict(color = colors[0], dash='dash')
            ),
        go.Scatter(mode = 'lines', hoverinfo='none',
            x = xx,
            y = yy_900, line=dict(color = colors[0], dash='dash'))
    ]

    layout = go.Layout(
        width = 700,
        height = 700,
        title = "Average Voltage vs. Capacity",
        xaxis = dict(
            range=[0,700],title='Gravimetric Capacity (mAh/g)'
        ),
        yaxis = dict(
            range=[0.9,5], title='Voltage (V)'
        ),
        showlegend=False,
        hovermode = 'closest',
    )
    return dict(data=data, layout=layout)

def draw_dropdown():
    return dcc.Dropdown(
        id='chem_dropdown',
        multi=True,
        value=[STARTING_ID],
        options=[{'label': i, 'value': i} for i in (df['battid']).tolist()])

def get_path_graph(batt_id):
    path = fetch_path(batt_id)
    path_info = path.get_primary_path_info()
    add_scene = path_info[2]
    base_ent = path.base_ent
    smc = ctc.StructureMoleculeComponent(
        base_ent.structure,
        hide_incomplete_bonds=True,
        bonded_sites_outside_unit_cell=False,
        scene_additions=add_scene)
    return smc.all_layouts["struct"]

def get_df(query):
    if isinstance(query, str):
        query_dict = yaml.load(query, Loader=yaml.FullLoader)
    elif isinstance(query, dict):
        query_dict = query
    cursor = mongo_coll.find(query_dict, show_fields)
    up_df = pd.DataFrame(list(cursor))
    if not up_df.empty:
        red_df = up_df.drop(columns='_id')
        return red_df.to_json()
    else:
        warnings.warn('Query had no results!')

def draw_table(df, dataframe=pd.DataFrame(), max_rows=16):
        if not dataframe.empty:
            df_disp= df.iloc[dataframe['pointIndex'].values]
            col_titles = ['Charged', 'Discharged', 'Stability (eV)',
                          'Avg. Voltage (V)', 'Capacity (mAh/g)', 'Energy (mW/g)']
            col_names = ['max_instability',
                         'average_voltage', 'capacity_grav', 'energy_grav']

            return html.Table(
                # # Header
                [html.Tr([html.Th(col) for col in col_titles])]+
                [html.Tr(
                    [html.Td(
                        html.A(disp_variable(df_disp.iloc[i]['formula_charge']),
                               href='https://materialsproject.org/materials/{}/'.format(
                                   disp_variable(df_disp.iloc[i]['id_charge'])),
                               target="_blank")
                    ),
                    html.Td(
                        html.A(disp_variable(df_disp.iloc[i]['formula_discharge']),
                               href='https://materialsproject.org/materials/{}/'.format(
                                   disp_variable(df_disp.iloc[i]['id_discharge'])),
                               target="_blank")
                        )
                    ]+
                    [html.Td(disp_variable(df_disp.iloc[i][col])) for col in col_names]) for i in range(min(len(df_disp), max_rows))]
            )

##########################################################################
#  Draw the initial app
##########################################################################

app.layout = get_app_layout()

##########################################################################
#  Useful functions
##########################################################################

def disp_variable(v):
    if type(v) == float or isinstance(v, np.float32) or isinstance(v, np.float64):
        return '{:0.2f}'.format(v)
    else:
        return v

def sigfigsdict(d):
    for k, v in d.items():
        if type(v) == float:
            d[k] = round(v, 2)
    return d

#def dfRowFromHover(hoverData):
#    ''' Returns row for hover point as a Pandas Series '''
#    if hoverData is not None:
#        if 'points' in hoverData:
#            firstPoint = hoverData['points'][0]
#            if 'pointNumber' in firstPoint:
#                point_number = firstPoint['pointNumber']
#
#                return df.iloc[point_number]
#    return pd.Series()

#callback functions


#@app.callback(
#    Output('mat_info', 'children'),
#    [Input('clickable-graph', 'hoverData')]
#)
#def diplay_info(hoverData):
#    if hoverData:
#        hover_df = dfRowFromHover(hoverData)
#        try:
#            mineral_type = hover_df['mineral']['type']
#        except:
#            mineral_type = 'N/A'
#        try:
#            dimension = int(hover_df['dimensionality'])
#        except:
#            dimension = 'N/A'
#        return [
#            html.Div([
#                "Charged: {}".format(hover_df['formula_charge']),
#            ]),
#            html.Div([
#                "Discharged: {}".format(hover_df['formula_discharge']),
#            ]),
#            ]
#    else:
#        return None

@app.callback(
    Output('current_selection', 'children'),
    [Input('clickable-graph', 'clickData')]
)
def update_current_selection(clickData):
    if clickData:
        return json.dumps(clickData)

@app.callback(
    Output('hidden-div', 'children'),
    [Input('clickable-graph', 'clickData')],
    [State('hidden-div', 'children')
     ]
)

def get_selected_data(clickData, hidden):
    if clickData:
        click = clickData['points'][0]
        #print('prv', hidden)
        if not hidden:
            result_list = [click]
            return json.dumps(result_list)

        if hidden:
            result_list = json.loads(hidden)
            if click in result_list:
                # remove
                result_list.remove(click)
            else:
                #add
                result_list.append(click)
            return json.dumps(result_list)


@app.callback(
    Output('hidden_df', 'children'),
    [Input('query_button', 'n_clicks')],
    [State('query_string', 'value'),
     State('hidden_df', 'children')]
)
def update_dataframe(n_clicks, query_string, hidden_df):
    return get_df(query_string)

@app.callback(
    Output('clickable-graph', 'figure'),
    [Input('clickable-graph', 'clickData'),
    Input('graph_button', 'n_clicks')],
    [State('clickable-graph', 'figure'),
     State('hidden-div', 'children'),
     State('hidden_df', 'children'),
     ]
)
def update_figure(clickData, n_clicks, figure, hidden, df_string):
    dataframe_json = df_string
    dataframe = pd.read_json(dataframe_json)
    new_figure = {}
    new_figure['data'] = draw_figure(dataframe_json)['data']
    new_figure['layout'] = draw_figure(dataframe_json)['layout']
    new_figure['layout']['uirevision'] = df_string

    if clickData:
        click = clickData['points'][0]

        if hidden:
            table = json.loads(hidden)
            # filter table so that only those in the current hidden_df get graphed
            for element in table:
                print(element)
                if element['text'] not in dataframe['battid'].unique():
                    table.remove(element)
        else:
            table=[]


        if click not in table:
            new_figure['layout']['shapes'] = [
                {
                'type': 'line',
                'x0': click['x'] - 7,
                'y0': click['y'],
                'x1': click['x'] + 7,
                'y1': click['y'],
                'line': {
                    'width': 3,
                    'color': 'rgb(360, 360, 360)'
                }
            },
                {
                'type': 'line',
                'x0': click['x'],
                'y0': click['y'] + 0.05,
                'x1': click['x'],
                'y1': click['y'] + 0.05,
                'line': {
                    'width': 3,
                    'color': 'rgb(360, 360, 360)'
                },
            },
        ]
            table.append(click)
            for all_selected in table:
                new_figure['data'][0]['x']+=tuple([all_selected['x']])
                new_figure['data'][0]['y']+=tuple([all_selected['y']])

        elif click in table:
            print('cancelled click', click)
            table.remove(click)
            print(table)
            for others in table:
                new_figure['data'][0]['x']+=tuple([others['x']])
                new_figure['data'][0]['y']+=tuple([others['y']])

    else:
        print('No clickData')
    return new_figure



@app.callback(
    Output('tab_selected', 'children'),
    [Input('hidden-div', 'children')],
    [State('hidden_df', 'children')]
)
def display_selected_data(points, df_string):
    if points:
        result = json.loads(points)
        try:
            df_tab = pd.DataFrame(result)
        except:
            return None
        if result is not None:
            #print(pd.DataFrame(result))
            df = pd.read_json(df_string)
            return draw_table(df, pd.DataFrame(result))

#@app.callback(
#    Output('path-graph', 'children'),
#    [Input('clickable-graph', 'clickData')]
#)
#def graph_path(clickData):
#    if clickData:
#        selectionInfo = clickData['points'][0]
#        battid = selectionInfo['text']
#        return get_path_graph(battid)


external_css = [
    "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
    "//fonts.googleapis.com/css?family=Dosis:Medium",
    "https://cdn.rawgit.com/plotly/dash-app-stylesheets/0e463810ed36927caf20372b6411690692f94819/dash-drug-discovery-demo-stylesheet.css"]

for css in external_css:
    app.css.append_css({"external_url": css})


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8000)
