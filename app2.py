import dash

from dash.dependencies import Output, Input, State

import dash_html_components as html
import dash_core_components as dcc
from dash.exceptions import PreventUpdate

app = dash.Dash(__name__)
app.scripts.config.serve_locally = True

app.layout = html.Div([
    # Default storage is memory, lost on page reload.
    dcc.Store(id='memory'),
    # local storage_type is only removed manually.
    dcc.Store(id='local', storage_type='local'),
    # session storage_type is cleared when the browser exit.
    dcc.Store(id='session', storage_type='session'),
    html.Button('click me', id='btn'),
    html.Div(id='output')
])


@app.callback(Output('local', 'data'),
              [Input('btn', 'n_clicks')], [State('local', 'data')])
def init_data(n_clicks, data):
    if n_clicks is None:
        raise PreventUpdate

    data = data or {}

    return {'clicked': data.get('clicked', 0) + 1}


@app.callback(Output('output', 'children'),
              [Input('local', 'modified_timestamp')],
              [State('local', 'data')])
def output(ts, data):
    if ts is None:
        raise PreventUpdate

    data = data or {}

    return 'Clicked: {}'.format(data.get('clicked', 0))


if __name__ == '__main__':
    app.run_server()

