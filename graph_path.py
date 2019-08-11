import dash, dash_auth
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
from pymatgen_diffusion.utils.get_db_data import get_ent_from_db, get_aeccar_from_store, get_deviation_from_optimal_cell_shape
import json
from maggma.stores import MongoStore

with open('.db_info.json') as json_file:
    db_login = json.load(json_file)

elec = MongoStore("js_cathodes", "concat_elec_basf",
                  host=db_login['host'],
                  username=db_login['username'],
                  password=db_login['password'],
                  lu_field="last_updated")

material = MongoStore("js_cathodes", "materials_js",
                  host=db_login['host'],
                  username=db_login['username'],
                  password=db_login['password'],
                  lu_field="last_updated")

tasks = MongoStore("js_cathodes", "tasks",
                    host=db_login['host'],
                    username=db_login['username'],
                    password=db_login['password'],
                    lu_field="last_updated")
elec.connect()
material.connect()
tasks.connect()

app = dash.Dash(__name__, url_base_pathname='/vw/')
app.config['suppress_callback_exceptions']=True

def get_app_layout():
    return html.Div(
            [html.Div(get_path_graph('11990_Li'), id='path-graph')#, style={"width": "75vw", "height": "75vh"})
        ]
    )

def get_path_graph(batt_id):
    grouped_entries = get_ent_from_db(elec, material, tasks, batt_id=batt_id)
    return 'this is a test'


app.layout = get_app_layout()

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8000)