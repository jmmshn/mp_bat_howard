from chgden_fetcher import chgden_fetcher
import intsitecomp
import crystal_toolkit as ct
import crystal_toolkit.components as ctc
import numpy as np
from skimage import measure
from crystal_toolkit.helpers.scene import *


class path_grapher():
    def __init__(self, battid):
        self.battid = battid
        cgf = chgden_fetcher(battid)
        chgden = cgf.get_aeccar_from_store()
        self.cc = chgden

    def get_mesh(self, chgcar, data_tag='total', isolvl=2.0, step_size=4):
        cc = self.cc
        tmp_chg = chgcar.data[data_tag]
        tmp_chg = np.concatenate((tmp_chg, tmp_chg[:1, :, :]), axis=0)
        tmp_chg = np.concatenate((tmp_chg, tmp_chg[:, :1, :]), axis=1)
        tmp_chg = np.concatenate((tmp_chg, tmp_chg[:, :, :1]), axis=2)
        vertices, faces, normals, values = measure.marching_cubes_lewiner(tmp_chg,
                                                                          level=isolvl,
                                                                          step_size=step_size)
        vertices = vertices / (tmp_chg.shape - np.array([1, 1, 1]))  # transform to fractional coordinates
        vertices = np.dot(vertices - 0.5, cc.structure.lattice.matrix)  # transform to cartesian
        return vertices, faces

    def get_pos(self, struct, pos):
        # TODO make this return a list of lists
        ans = np.dot(np.array(pos) - 0.5 * np.ones_like(pos), struct.lattice.matrix)  # transform to cartesian
        for itr in ans:
            yield itr.tolist()

    def get_path_graph(self):
        cc = self.cc
        vertices, faces = self.get_mesh(cc, isolvl=2.5, step_size=3)
        pos = [vert for triangle in vertices[faces].tolist() for vert in triangle]

        exp_struct = cc.structure * [2, 2, 2]

        # Insertion sites
        isc = intsitecomp.intsitecomp(cc)
        isc.get_labels()
        isc.get_graph()
        isc.get_edges_labels()
        idx = 0
        last_site = "None"
        unique_lab = []
        for site in isc._extrema_df.site_label.values:
            if site == last_site:
                idx += 1
            else:
                idx = 1
            last_site = site
            unique_lab.append("{}{}".format(site, idx))

        isc.get_primary_path(0, 0)
        path_frac_coords = isc.exp_sgo.structure.frac_coords[isc.get_primary_path(2, 1)]

        site_pos = list(path_frac_coords[:])
        site_lab = unique_lab

        site_pos = list(self.get_pos(exp_struct, site_pos))

        add_content = []
        colormap = {'a': '#1B98D1', 'b': '#EF7135', 'c': '#6B7782'}

        for n in range(0, len(site_pos)):
            current_pos = site_pos[n]
            if n != len(site_pos) - 1:
                next_pos = site_pos[n + 1]
            else:
                next_pos = current_pos
            add_content.append(Cubes(positions=[current_pos], color='yellow', width=0.5))
            add_content.append(Cylinders(positionPairs=[[current_pos, next_pos]], color='yellow', radius=1.0))

        test_scene = [Scene("test", contents=add_content)]

        struct_component = ctc.StructureMoleculeComponent(
            exp_struct, scene_additions=test_scene, hide_incomplete_bonds=True
        )

        return struct_component.standard_layout