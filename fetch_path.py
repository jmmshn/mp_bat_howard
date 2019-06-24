from pymatgen import MPRester, Structure
from crystal_toolkit.components.structure import StructureMoleculeComponent
from crystal_toolkit.helpers.pythreejs_adapter import display_struct, display_StructureMoleculeComponent
from pymatgen_diffusion.neb.full_path_mapper import ComputedEntryPath
from matplotlib import pyplot as plt
from maggma.stores import MongoStore
from maggma.advanced_stores import MongograntStore
from pymatgen.entries.computed_entries import ComputedStructureEntry
from pymatgen.entries.compatibility import MaterialsProjectCompatibility
import matplotlib
from crystal_toolkit.helpers.scene import Spheres, Cylinders, Cubes
from matplotlib.colors import rgb2hex
import gridfs
import zlib
import json
from monty.serialization import MontyDecoder
import numpy as np
import networkx as nx
from icecream import ic
import warnings

with open('.:secrets:db_info.json') as json_file:
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
colors = [[0.21568627, 0.47058824, 0.74901961],
      [0.99607843, 0.70196078, 0.03137255],
      [0.65882353, 0.64313725, 0.58431373],
      [0.48235294, 0.69803922, 0.45490196],
      [0.50980392, 0.37254902, 0.52941176],
      [0.39607843, 0.        , 0.12941176]]
colors_hex = [rgb2hex(itr) for itr in colors]
compat = MaterialsProjectCompatibility('Advanced')

class fetch_path:

    def __init__(self, battid, w_ion='Li'):
        self.battid = battid
        self.w_ion = w_ion

    def get_aeccar_from_store(self, tstore, task_id):
        """
        Read the AECCAR grid_fs data into a Chgcar object
        :param tstore: MongoStore for the tasks database
        :param task_id: The id of the material entry
        :return: pymatgen Chrgcar object
        """
        tstore.connect()
        m_task = tstore.query_one({'task_id': task_id})
        try:
            fs_id = m_task['calcs_reversed'][0]['aeccar0_fs_id']
        except:
            logger.info('AECCAR0 Missing from task #'.format(task_id))
            return None

        fs = gridfs.GridFS(tstore.collection.database, 'aeccar0_fs')
        chgcar_json = zlib.decompress(fs.get(fs_id).read())
        aeccar0 = json.loads(chgcar_json, cls=MontyDecoder)

        try:
            fs_id = m_task['calcs_reversed'][0]['aeccar2_fs_id']
        except:
            logger.info('AECCAR2 Missing from task #'.format(task_id))
            return None

        fs = gridfs.GridFS(tstore.collection.database, 'aeccar2_fs')
        chgcar_json = zlib.decompress(fs.get(fs_id).read())
        aeccar2 = json.loads(chgcar_json, cls=MontyDecoder)
        return aeccar0 + aeccar2

    def get_mg_info(self, battid):
        mat_ids = elec.query_one({'battid': battid})['material_ids']
        mat_ids = list(map(int, mat_ids))
        base_ent = None
        insert_ent = []
        q = {'task_id': {'$in': mat_ids}}

        min_cnt = min([cc['nsites'] for cc in material.query(q)])
        for cc in material.query(q):
            struct = Structure.from_dict(cc['structure'])
            entry = ComputedStructureEntry(
                structure=struct,
                energy=cc['thermo']['energy'],
                parameters=cc['calc_settings'],
                entry_id=cc['task_id'])
            entry = compat.process_entry(entry)
            if entry.structure.num_sites == min_cnt:
                base_ent = entry
            elif entry.structure.num_sites == min_cnt + 1:
                insert_ent.append(entry)
        self.base_ent = base_ent
        t_ids = list(
            map(int,
                material.query_one({'task_id': base_ent.entry_id})['task_ids']))
        aec_id = tasks.query_one({
            'task_id': {
                '$in': t_ids
            },
            'calcs_reversed.0.aeccar0_fs_id': {
                '$exists': 1
            }
        })['task_id']
        aeccar = self.get_aeccar_from_store(tasks, aec_id)
        cep = ComputedEntryPath(
            base_ent,
            single_cat_entries=insert_ent,
            migrating_specie=self.w_ion,
            base_aeccar=aeccar,
            max_path_length=6)
        self.cep = cep
        if len(self.cep.full_sites.sites) < 2:
            warnings.warn('ComputedEntryPath only found one site!')
        cep.populate_edges_with_chg_density_info()
        ipos_epos_chg = list([(d['ipos'], d['epos'], d['chg_total'])
                              for u, v, d in cep.s_graph.graph.edges(data=True)])
        self.ipos_epos_chg = ipos_epos_chg
        uv = list([(u, v) for u, v, d in cep.s_graph.graph.edges(data=True)])
        self.uv = uv
        max_chg = np.max([itr[2] for itr in ipos_epos_chg])
        min_chg = np.min([itr[2] for itr in ipos_epos_chg])
        cmap = plt.cm.YlOrRd
        self.cmap=cmap
        norm = matplotlib.colors.Normalize(vmin=min_chg, vmax=max_chg)
        self.norm=norm
        # All paths in a given material

        self.sgo = cep.s_graph
        self.ipos_epos_chg = ipos_epos_chg

    def reduce_exp_sgo(self):
        self.exp_sgo = self.sgo * [2, 2, 2]  # get the expanded cell
        all_info = self.exp_sgo.as_dict()
        adjacency_info = all_info['graphs']['adjacency']
        outb_edges = []  # obtain list of out-of-bound edges for the expanded cell
        for index in range(0, len(adjacency_info)):
            one_index = adjacency_info[index]
            for one_edge in one_index:
                if one_edge['to_jimage'] != (0, 0, 0):
                    outb_edges.append([index, one_edge['id'], one_edge['to_jimage']])
        for n in outb_edges:  # trim the expanded cell
            self.exp_sgo.break_edge(n[0], n[1], n[2])
        return self.exp_sgo

    def find_next_index(self, ini_index, direction):
        fin_frac_coords = self.exp_sgo.structure.frac_coords[ini_index]
        fin_frac_coords[direction] += 0.5
        for n in range(0, len(self.exp_sgo.structure.frac_coords)):
            if np.allclose(self.exp_sgo.structure.frac_coords[n], fin_frac_coords) == 1:
                return n

    def trace_index(self, exp_index):
        coords = np.around(self.exp_sgo.structure.frac_coords[exp_index], 10)
        ori_coords = (coords * 2) % 1
        for n in range(0, len(self.sgo.structure.frac_coords)):
            if np.allclose(self.sgo.structure.frac_coords[n], ori_coords, rtol=0, atol=0.0002) == 1:
                ori_index = n
        ori_image = (int(coords[0] * 2 // 1), int(coords[1] * 2 // 1), int(coords[2] * 2 // 1))
        return ori_index, ori_coords, ori_image

    def convert_one_path(self, path_in_exp_index):
        converted_path = []
        for n in path_in_exp_index:
            converted_one_step = self.trace_index(n)
            converted_path.append(converted_one_step)
        return converted_path
    def get_all_simple_paths(self):
        simple_paths = []
        for ini_index in range(0, 2):
            for direction in range(0, 3):
                simple_paths.extend(
                    list(nx.all_simple_paths(self.exp_sgo.graph, ini_index, self.find_next_index(ini_index, direction))))
        return simple_paths

    def lowest_chg_path(self, simple_paths):
        if simple_paths:
            hop_info = [self.sgo, self.ipos_epos_chg]
            chg_list = []
            for one_path in simple_paths:
                path = self.convert_one_path(one_path)
                path_chg = 0
                for i in range(0, len(path) - 1):
                    step_coords = np.concatenate((path[i][1], path[i + 1][1]), axis=0)
                    for hop_data in hop_info[1]:
                        fore_order = np.concatenate((hop_data[0], hop_data[1]), axis=0)
                        reverse_order = np.concatenate((hop_data[1], hop_data[0]), axis=0)
                        if np.allclose(step_coords, fore_order) or np.allclose(step_coords, reverse_order):
                            step_chg = hop_data[2]
                            break
                    path_chg += step_chg
                chg_list.append(path_chg)
            print(chg_list)
            index = chg_list.index(min(chg_list))
            path_in_exp = simple_paths[index]
            return path_in_exp
        else:
            print('No Simple Path available')
            return None

    def get_add_scene(self):
        cep = self.cep
        base_ent = self.base_ent
        ipos_epos_chg = self.ipos_epos_chg
        uv = self.uv
        cmap = self.cmap
        norm=self.norm
        res_struct = base_ent.structure.copy()
        add_scene = []
        hop_colors = []
        hop_colors.extend(colors_hex)
        c_dict = {}
        uniq_engs = list(
            set([
                ipos.properties['inserted_energy'] for ipos in cep.full_sites.sites
            ]))
        for itr_site, ipos in enumerate(cep.full_sites.sites):
            new_pos = np.array([
                itr_dir - 1 if abs(itr_dir - 1) < 0.01 else itr_dir
                for itr_dir in ipos.frac_coords
            ])
            pos0 = np.dot(new_pos - 0.5,
                          cep.base_struct_entry.structure.lattice.matrix).tolist()
            c_val = None
            for it_c, eng in enumerate(uniq_engs):
                if eng == ipos.properties['inserted_energy']:
                    c_val = it_c
            c_dict.update({itr_site: colors_hex[c_val]})
            add_scene.append(Spheres([pos0], color=colors_hex[c_val], radius=0.6))

        for itr_hop, (ipos, epos, chg) in enumerate(ipos_epos_chg):
            pos0 = np.dot(ipos - 0.5, base_ent.structure.lattice.matrix).tolist()
            pos1 = np.dot(epos - 0.5, base_ent.structure.lattice.matrix).tolist()
            if max(ipos) >= 1 or min(ipos) <= 0:
                add_scene.append(
                    Spheres([pos0], color=c_dict[uv[itr_hop][0]], radius=0.6))
            if max(epos) >= 1 or min(epos) <= 0:
                add_scene.append(
                    Spheres([pos1], color=c_dict[uv[itr_hop][1]], radius=0.6))

            itr_color = matplotlib.colors.rgb2hex(cmap(norm(chg)))
            hop_colors.append(itr_color)
            add_scene.append(Spheres([[pos0, pos1]], radius=0.4, color=itr_color))
            res_struct.insert(0, self.w_ion, ipos)
            res_struct.insert(0, self.w_ion, epos)
        return add_scene

    def get_primary_path_info(self):
        self.get_mg_info(self.battid)
        self.reduce_exp_sgo()
        all_simple_paths = self.get_all_simple_paths()
        exp_index_path = self.lowest_chg_path(all_simple_paths)
        ori_index_path = [self.trace_index(i) for i in exp_index_path]
        add_scene = self.get_add_scene()
        return [exp_index_path, ori_index_path, add_scene]
