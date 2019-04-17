from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.analysis.defects.utils import ChargeDensityAnalyzer
from pymatgen.analysis.defects.utils import logger as defect_utils_logger
from pymatgen import Structure
from pymatgen.analysis.graphs import StructureGraph
from pymatgen.analysis.local_env import MinimumDistanceNN
from pymatgen.analysis.local_env import VoronoiNN
from copy import copy
import numpy as np
import operator
import pandas as pd
import networkx as nx
import logging


# logger.basicConfig(filename='defect_utils.log')
defect_utils_logger.setLevel(logging.WARNING)
alpha = list('abcdefghijklmnopqrstuvwxyz')
sm = StructureMatcher()


def generic_groupby(list_in, comp=operator.eq, lab_num=True):
    '''
    Group a list of unhasable objects
    Return a list of labels that represent which group the entry is in
    '''
    list_out = ['TODO'] * len(list_in)
    cnt = 0
    for i1, ls1 in enumerate(list_out):
        if ls1 != 'TODO':
            continue

        if not lab_num:
            list_out[i1] = alpha[cnt]
        else:
            list_out[i1] = cnt
        cnt += 1
        for i2, ls2 in enumerate(list_out):
            if comp(list_in[i1], list_in[i2]):
                list_out[i2] = list_out[i1]
    return list_out


class intsitecomp(ChargeDensityAnalyzer):
    def __init__(self, chgcar, wion='Li'):
        self.working_ion = wion
        super().__init__(chgcar)
        self.get_local_extrema()
        if len(self._extrema_df) > 1:
            self.cluster_nodes(tol=0.6)
        self.sort_sites_by_integrated_chg()
        # self._extrema_df[['site_label']] = self._extrema_df[['site_label']].astype(str)
        # mask_not_dense = np.array(self._extrema_df.avg_charge_den < 0.5)
        # self._extrema_df = self._extrema_df.iloc[mask_not_dense]
        inserted_structs = []
        for itr, li_site in self._extrema_df.iterrows():
            tmp_struct = chgcar.structure.copy()
            li_site = self._extrema_df.iloc[itr]
            tmp_struct.insert(-1, self.working_ion, [li_site['a'],li_site['b'],li_site['c']], properties = {})
            tmp_struct.sort()
            inserted_structs.append(tmp_struct)
        self._extrema_df['inserted_struct'] = inserted_structs

    def get_labels(self):
        site_labels = generic_groupby(self._extrema_df.inserted_struct, comp=sm.fit, lab_num=False)
        self._extrema_df['site_label'] = site_labels
        # generate the structure with only Li atoms for NN analysis
        self.allsites_struct = Structure(self.structure.lattice , np.repeat(self.working_ion, len(self._extrema_df)),
                             self._extrema_df[['a', 'b', 'c']].values,
                             site_properties= {'label' : self._extrema_df[['site_label']].values.flatten()})
        # iterate and make sure that the sites in the allsites_struct are in the same order as the _extrema_df
        self.get_graph()

    def get_graph(self):
        # Generate the graph edges between these sites
        self.gt = StructureGraph.with_local_env_strategy(self.allsites_struct, MinimumDistanceNN(tol=0.8, cutoff=10))
        self.gt.set_node_attributes()


    def compare_edges(self, edge1, edge2):
        #
        p0=nx.get_node_attributes(self.gt.graph, 'properties')[edge1[0]]['label']
        p1=nx.get_node_attributes(self.gt.graph, 'properties')[edge1[1]]['label']
        pp0=nx.get_node_attributes(self.gt.graph, 'properties')[edge2[0]]['label']
        pp1=nx.get_node_attributes(self.gt.graph, 'properties')[edge2[1]]['label']
        #print(edge1, '{}->{}'.format(p0, p1), '{}->{}'.format(pp0, pp1), edge2)
        temp_struct1 = self._extrema_df.iloc[edge1[0]]['inserted_struct'].copy()
        new_site = self._extrema_df[['a', 'b', 'c']].values[edge1[1]]
        #print(new_site)
        temp_struct1.insert(0, self.working_ion, new_site, properties = {})
        temp_struct1.sort()

        temp_struct2 = self._extrema_df.iloc[edge2[0]]['inserted_struct'].copy()
        new_site = self._extrema_df[['a', 'b', 'c']].values[edge2[1]]
        #print(new_site)
        temp_struct2.insert(0, self.working_ion, new_site, properties = {})
        temp_struct2.sort()
        #print(sm.fit(temp_struct1, temp_struct2))
        return sm.fit(temp_struct1, temp_struct2)

    def get_edges_labels(self, mask_file=None):
        pos_list_0=[]
        pos_list_1=[]
        to_jimage=[]
        for u, v, k, d in self.gt.graph.edges(keys=True, data=True):
            pos_list_0.append(self._extrema_df[['a', 'b', 'c']].values[u])
            to_jimage.append(d['to_jimage'])
            pos_list_1.append(self._extrema_df[['a', 'b', 'c']].values[v] + np.array(d['to_jimage']))
        pos_list_0= np.array(pos_list_0)
        pos_list_1= np.array(pos_list_1)
        self._edgelist = pd.DataFrame.from_dict({'edge_tuple' : list(self.gt.graph.edges())})
        edge_lab = generic_groupby(self._edgelist['edge_tuple'], comp = self.compare_edges)
        self._edgelist['edge_label'] = edge_lab
        self._edgelist['to_jimage'] = to_jimage
        self._edgelist['pos0x'] = pos_list_0[:,0]
        self._edgelist['pos0y'] = pos_list_0[:,1]
        self._edgelist['pos0z'] = pos_list_0[:,2]
        self._edgelist['pos1x'] = pos_list_1[:,0]
        self._edgelist['pos1y'] = pos_list_1[:,1]
        self._edgelist['pos1z'] = pos_list_1[:,2]
        # write the image
        self.unique_edges = self._edgelist.drop_duplicates('edge_label', keep='first')


        # set up the grid
        aa = np.linspace(0, 1, len(self.chgcar.get_axis_grid(0)),
                         endpoint=False)
        bb = np.linspace(0, 1, len(self.chgcar.get_axis_grid(1)),
                         endpoint=False)
        cc = np.linspace(0, 1, len(self.chgcar.get_axis_grid(2)),
                         endpoint=False)
        AA, BB, CC = np.meshgrid(aa, bb, cc, indexing='ij')
        fcoords = np.vstack([AA.flatten(), BB.flatten(), CC.flatten()]).T

        IMA, IMB, IMC = np.meshgrid([-1, 0, 1], [-1, 0, 1], [-1, 0, 1], indexing='ij')
        images = np.vstack([IMA.flatten(), IMB.flatten(), IMC.flatten()]).T

        # get the charge density masks for each hop (for plotting and sanity check purposes)
        idx_pbc_mask = np.zeros_like(AA)
        surf_idx=0
        total_chg=[]
        if mask_file:
            mask_out = copy(self.chgcar)
            mask_out.data['total'] = np.zeros_like(AA)

        for _, row in self.unique_edges.iterrows():
            pbc_mask = np.zeros_like(AA).flatten()
            e0 = row[['pos0x', 'pos0y', 'pos0z']].astype('float64').values
            e1 = row[['pos1x', 'pos1y', 'pos1z']].astype('float64').values

            cart_e0 = np.dot(e0, self.chgcar.structure.lattice.matrix)
            cart_e1 = np.dot(e1, self.chgcar.structure.lattice.matrix)
            pbc_mask = np.zeros_like(AA,dtype=bool).flatten()
            for img in images:
                grid_pos = np.dot(fcoords + img, self.chgcar.structure.lattice.matrix)
                proj_on_line = np.dot(grid_pos - cart_e0, cart_e1 - cart_e0) / (np.linalg.norm(cart_e1 - cart_e0))
                dist_to_line = np.linalg.norm(
                    np.cross(grid_pos - cart_e0, cart_e1 - cart_e0) / (np.linalg.norm(cart_e1 - cart_e0)), axis=-1)

                mask = (proj_on_line >= 0) * (proj_on_line < np.linalg.norm(cart_e1 - cart_e0)) * (dist_to_line < 0.5)
                pbc_mask = pbc_mask + mask
            pbc_mask = pbc_mask.reshape(AA.shape)
            if mask_file:
                mask_out.data['total'] = pbc_mask
                mask_out.write_file('{}_{}.vasp'.format(mask_file,row['edge_tuple']))


            total_chg.append(self.chgcar.data['total'][pbc_mask].sum()/self.chgcar.ngridpts/self.chgcar.structure.volume)

        self.complete_mask=idx_pbc_mask
        self.unique_edges = self.unique_edges.assign(chg_total=total_chg)
        #self._edgelist['total_chg_masks'] = total_chg_mask

    def find_next_index(self, ini_index, direction):
        fin_frac_coords = self.exp_sgo.structure.frac_coords[ini_index]
        fin_frac_coords[direction] += 0.5
        for n in range(0,len(self.exp_sgo.structure.frac_coords)):
            if np.allclose(self.exp_sgo.structure.frac_coords[n], fin_frac_coords) == 1:
                return n

    def trace_index(self, exp_index):
        coords = np.around(self.exp_sgo.structure.frac_coords[exp_index],4)
        ori_coords = (coords*2)%1
        for n in range(0,len(self.sgo.structure.frac_coords)):
            if np.allclose(self.sgo.structure.frac_coords[n], ori_coords, rtol=0, atol=0.0002) == 1:
                ori_index = n
        ori_image = (int(coords[0]*2//1), int(coords[1]*2//1), int(coords[2]*2//1))
        return ori_index, ori_coords, ori_image

    def convert_one_path(self, path_in_exp_index):
        converted_path = []
        for n in path_in_exp_index:
            converted_one_step = [self.trace_index(n)[0], self.trace_index(n)[2]]
            converted_path.append(converted_one_step)
        return converted_path

    def reduce_sgo(self):
        self.trimmed_edgelist = copy(self._edgelist)
        self.cut_list = copy(self.unique_edges)

        #get list of qualified edges
        for n in range(0,len(self.cut_list)): # filter out labels with too high charge total
            chg_list = self.cut_list['chg_total']
            del_list = [n for n in range(0,len(chg_list)) if chg_list.iloc[n] > 20*min(self.cut_list['chg_total'])] #can use more dselfussion on this threshold
        self.cut_list = self.cut_list.drop(self.cut_list.index[del_list])
        valid_label = list(self.cut_list.iloc[:]['edge_label'])

        n = 0
        while n < len(self.trimmed_edgelist):
            if self.trimmed_edgelist.iloc[n]['edge_label'] not in valid_label:
                self.trimmed_edgelist = self.trimmed_edgelist.drop(self.trimmed_edgelist.index[n])
            else:
                n = n + 1

        #modify the structure graph object
        del_edges = []
        for n in range(0,len(self._edgelist)):
            if self._edgelist.iloc[n]['edge_label'] not in valid_label:
                del_edges.append(self._edgelist.iloc[n])

        self.sgo = copy(self.gt)
        for n in del_edges:
            self.sgo.break_edge(n['edge_tuple'][0],n['edge_tuple'][1],to_jimage=n['to_jimage'])

        self.exp_sgo = self.sgo*[2,2,2] # get the expanded cell
        all_info = self.exp_sgo.as_dict()
        adjacency_info = all_info['graphs']['adjacency']
        outb_edges = [] # obtain list of out-of-bound edges for the expanded cell
        for index in range(0,len(adjacency_info)):
            one_index = adjacency_info[index]
            for one_edge in one_index:
                if one_edge['to_jimage'] != (0, 0, 0):
                    outb_edges.append([index, one_edge['id'], one_edge['to_jimage']])
        for n in outb_edges: # trim the expanded cell
            self.exp_sgo.break_edge(n[0], n[1], n[2])

    def lowest_chg_path(self, simple_paths):
        if simple_paths:
            chg_list = []
            for one_path in simple_paths:
                path = self.convert_one_path(one_path)
                path_chg = 0
                for i in range(0,len(path)-1):
                    step_edge = (path[i][0], path[i+1][0])
                    for n in range(0, len(self.trimmed_edgelist)):
                        if step_edge == self.trimmed_edgelist.iloc[n]['edge_tuple'] or step_edge[::-1] == self.trimmed_edgelist.iloc[n]['edge_tuple']:
                            l = self.trimmed_edgelist.iloc[n]['edge_label']
                    step_chg = self.unique_edges.iloc[l]['chg_total']
                    path_chg += step_chg
                chg_list.append(path_chg)

            index = chg_list.index(min(chg_list))
            path_in_exp = simple_paths[index]
            return path_in_exp
        else:
            print('No Simple Path available')
            return None

    def get_primary_path(self, ini_index, direction):
        self.reduce_sgo()
        simple_paths = list(nx.all_simple_paths(self.exp_sgo.graph, ini_index, self.find_next_index(ini_index, direction)))
        primary_path = self.lowest_chg_path(simple_paths)
        return primary_path

    def get_converted_primary_path(self, ini_index, direction):
        return self.convert_one_path(self.get_primary_path(ini_index, direction))

    def get_converted_index_only(self, ini_index, direction):
        path = self.get_converted_primary_path(ini_index, direction)
        return [n[0] for n in path]
