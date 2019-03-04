import dash, dash_auth
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd
import numpy as np
import json
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate
from pymongo import MongoClient
import dash_table
import flask
from flask_cors import CORS

import os

#src_dir = os.path.dirname(os.path.abspath(__file__))

with open('./secrets/db_info.json') as json_file:
    db_login = json.load(json_file)
client = MongoClient(
        db_login['host'],
        username=db_login['username'],
        password=db_login['password'],
        authSource=db_login['database'],
        authMechanism='SCRAM-SHA-1')
mongo_coll = client[db_login['database']][db_login['collection']]

show_fields = ['batt_id', 'average_voltage',
               'capacity_grav',
               'formula_charge',
               'formula_discharge', 'id_charge', 'id_discharge',
               'max_instability']

query = {'working_ion' : {'$in': ['Ca', 'Mg']}}

# Make a query to the specific DB and Collection
cursor = mongo_coll.find(query, show_fields)

# Expand the cursor and construct the DataFrame
df = pd.DataFrame(list(cursor))

app = dash.Dash('Battery Explorer', url_base_pathname='/vw/')

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
                          figure=draw_figure()),
            ], className='nine  columns')
        ]),
        #     html.Div([
        #         dcc.RadioItems(
        #             id='charts_radio',
        #             options=[
        #                 dict(label='3D Scatter', value='scatter3d'),
        #                 dict(label='2D Scatter', value='scatter'),
        #             ],
        #             labelStyle=dict(display='inline'),
        #             value='scatter'
        #         ),
        #         dcc.Graph(id='clickable-graph',
        #                   style=dict(width='600px'),
        #                   hoverData=dict(points=[dict(pointNumber=0)]),
        #                   figure=FIGURE),
        #     ], className='nine columns', style=dict(textAlign='center'))
        # ]),
        # Row: Table
        html.Div([
            html.Div([
                html.Div(id = 'tab_selected'),
                #html.Div(id = 'hidden-div'),
                html.Div(id = 'hidden-div', style = {'display': 'none'}),
            ], className='twelve columns')
        ], className='row'),
    ], className='container')


##########################################################################
# The different dynamic elements in the app each writen as a function
##########################################################################
def draw_figure():
    """
    Return the figure data based on some filters
    :param selected_idx:
    :return:
    """
    dff = df
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
                       size = 13,
                       color='rgb(231, 99, 250)',
                   )
                ),
        go.Scatter(mode = 'markers',
            x = dff['capacity_grav'],
            y = dff['average_voltage'],
            text = dff['batt_id'],
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
        hovermode = 'closest'
    )
    return dict(data=data, layout=layout)

def draw_dropdown():
    return dcc.Dropdown(
        id='chem_dropdown',
        multi=True,
        value=[STARTING_ID],
        options=[{'label': i, 'value': i} for i in (df['batt_id']).tolist()])


#def draw_table():
#    return dash_table.DataTable(
#            id='table-selection',
#            columns=[
#                {"name": i, "id": i} for i in df.columns
#            ],
#            pagination_mode='be',
#            pagination_settings={
#                'current_page': 0,
#                'page_size': PAGE_SIZE
#            },
#
#            filtering='be',
#            filtering_settings='',
#
#            sorting='be',
#            sorting_type='multi',
#            sorting_settings=[],
#            data=df.to_dict('rows'),
#            row_selectable='multi',
#            selected_rows=[],
            # We don't need the data field here since it will be populated in the callback
#        )


def draw_table(dataframe=pd.DataFrame(), max_rows=16):
        if not dataframe.empty:
            df_disp= df.iloc[dataframe['pointIndex'].values]
            # show_fields = ['batt_id', 'average_voltage', 'capacity_grav', 'max_instability', 'text', 'delith_id',
            #    'formula_discharge', 'formula_charge', 'spg_symbol', 'mineral', 'dimensionality']
            col_titles = ['Charged', 'Discharged', 'Stability (eV)',
                          'Avg. Voltage (V)', 'Capacity (mAh/g)']
            col_names = [ 'max_instability',
                         'average_voltage', 'capacity_grav']

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

def dfRowFromHover(hoverData):
    ''' Returns row for hover point as a Pandas Series '''
    if hoverData is not None:
        if 'points' in hoverData:
            firstPoint = hoverData['points'][0]
            if 'pointNumber' in firstPoint:
                point_number = firstPoint['pointNumber']
                # molecule_name = str(
                #     FIGURE['data'][0]['text'][point_number]).strip()
                return df.iloc[point_number]
    return pd.Series()

##########################################################################
#  Connections between the various interactive components
##########################################################################

# @app.callback(
#     Output('table-selection', "data"),
#     [Input('table-selection', "pagination_settings"),
#      Input('table-selection', "sorting_settings"),
#      Input('table-selection', "filtering_settings")])
# def update_table(pagination_settings, sorting_settings, filtering_settings):
#     filtering_expressions = filtering_settings.split(' && ')
#     dff = df
#     for filter in filtering_expressions:
#         if ' eq ' in filter:
#             col_name = filter.split(' eq ')[0]
#             filter_value = filter.split(' eq ')[1]
#             dff = dff.loc[dff[col_name] == filter_value]
#         if ' > ' in filter:
#             col_name = filter.split(' > ')[0]
#             filter_value = float(filter.split(' > ')[1])
#             dff = dff.loc[dff[col_name] > filter_value]
#         if ' < ' in filter:
#             col_name = filter.split(' < ')[0]
#             filter_value = float(filter.split(' < ')[1])
#             dff = dff.loc[dff[col_name] < filter_value]
#
#     if len(sorting_settings):
#         dff = dff.sort_values(
#             [col['column_id'] for col in sorting_settings],
#             ascending=[
#                 col['direction'] == 'asc'
#                 for col in sorting_settings
#             ],
#             inplace=False
#         )
#
#     rows_dict = dff.iloc[
#            pagination_settings['current_page']*pagination_settings['page_size']:
#            (pagination_settings['current_page'] + 1)*pagination_settings['page_size']
#            ].to_dict('rows')
#     # we only need to shown these points right before
#     rows_dict = [sigfigsdict(d) for d in rows_dict]
#     return rows_dict


@app.callback(
    Output('mat_info', 'children'),
    [Input('clickable-graph', 'hoverData')])
def diplay_info(hoverData):
    if hoverData:
        hover_df = dfRowFromHover(hoverData)
        try:
            mineral_type = hover_df['mineral']['type']
        except:
            mineral_type = 'N/A'
        try:
            dimension = int(hover_df['dimensionality'])
        except:
            dimension = 'N/A'
        return [
            html.Div([
                "Charged: {}".format(hover_df['formula_charge']),
            ]),
            html.Div([
                "Discharged: {}".format(hover_df['formula_discharge']),
            ]),
            html.Div([
                "Dimension: {}".format(dimension),
            ]),
            ]
    else:
        return None

@app.callback(
    Output('hidden-div', 'children'),
    [Input('clickable-graph', 'clickData')],
    [State('hidden-div', 'children')])
def get_selected_data(clickData, hidden):
    if clickData is not None:
        result = clickData['points']
        #print('prv', hidden)
        if result[0]['curveNumber'] != 1:
            hidden = json.loads(hidden)
            return json.dumps(hidden)

        if hidden:
            hidden = json.loads(hidden)
            if hidden is not None:
                for pt in result:
                    if pt in hidden:
                        # remove
                        hidden.remove(pt)
                        result = hidden
                    else:
                        #add
                        result = hidden + result
        return json.dumps(result)

@app.callback(
    Output('clickable-graph', 'figure'),
    [Input('clickable-graph', 'clickData')],
    [State('clickable-graph', 'figure'),
     State('hidden-div', 'children')]
)

def add_new_point(clickData, figure, hidden):
    if not clickData:
        raise PreventUpdate
    result = clickData['points']
    if result[0]['curveNumber'] != 1:
        raise PreventUpdate
    #print('figure', figure['data'][0]['x'])
    if hidden:
        hidden=json.loads(hidden)
    else:
        hidden=[]

    if hidden==[]:
        figure['data'][0]['x']=[result[0]['x']]
        figure['data'][0]['y']=[result[0]['y']]
        return figure

    for pt in result:
        if pt in hidden:
            figure['data'][0]['x'].remove(pt['x'])
            figure['data'][0]['y'].remove(pt['y'])
        else:
            figure['data'][0]['x'].append(pt['x'])
            figure['data'][0]['y'].append(pt['y'])
    return figure


    #print('hidden', hidden)
    #raise PreventUpdate
    # if not hidden:
    #     figure['data'][0]['x'].append(result[0]['x'])
    #     figure['data'][0]['y'].append(result[0]['y'])
    #     return figure
    # figure['data'][0]['x']=[pt['x'] for pt in hidden]
    # figure['data'][0]['y']=[pt['y'] for pt in hidden]
    # return figure


@app.callback(
    Output('tab_selected', 'children'),
    [Input('hidden-div', 'children')]
)
def display_selected_data(points):
    if points:
        result = json.loads(points)
        try:
            df_tab = pd.DataFrame(result)
        except:
            return None
        if result is not None:
            #print(pd.DataFrame(result))
            return draw_table(pd.DataFrame(result))


external_css = [
    "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
    "//fonts.googleapis.com/css?family=Dosis:Medium",
    "https://cdn.rawgit.com/plotly/dash-app-stylesheets/0e463810ed36927caf20372b6411690692f94819/dash-drug-discovery-demo-stylesheet.css"]

for css in external_css:
    app.css.append_css({"external_url": css})

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
