import json
from pymongo import MongoClient
import pandas as pd
import pprint
from pymatgen.core.structure import Structure
import numpy as np
from crystal_toolkit.core.scene import Spheres, Cylinders
from crystal_toolkit.core.scene import Scene
from crystal_toolkit.components.structure import StructureMoleculeComponent


def migration_graph(intercalating_paths, hops, fss, bs):
    '''
    Obtain the migration graph as an smc with given info
    '''
    m_path, last_step = get_modified_path(intercalating_paths)
    last_info = last_point_info(hops, last_step)
    last_jump = fss.frac_coords[last_info[1]] + np.array(last_info[2] + np.array([-0.5, -0.5, -0.5]))
    pairs = get_pairs(m_path, fss, last_jump)
    extra_scene = get_extra_scene(pairs)
    smc = get_combined_scene(bs, extra_scene)
    return smc


def get_modified_path(intercalating_paths):
    path = intercalating_paths[0]
    last_step = path[0]
    path = path[::-1]
    ie = ['isite', 'esite']
    m_path=[]

    if set([path[0]['isite'], path[0]['esite']]) == set([path[1]['isite'], path[1]['esite']]):
        if path[1]['isite'] == path[0]['esite']:
            m_path = [[path[0]['isite'], path[0]['esite']], [path[1]['isite'], path[1]['esite']]]
        else:
            m_path = [[path[0]['esite'], path[0]['isite']], [path[1]['isite'], path[1]['esite']]]

    else:
        start = list(set([path[0][x] for x in ie]) & set([path[-1][x] for x in ie]))[0]
        previous_point=start
        for one_hop_info in path:
            one_hop = [one_hop_info[x] for x in ie]
            if one_hop[0] == previous_point:
                m_path.append(one_hop[0:2])
            elif one_hop[1] == previous_point:
                i_point, e_point = one_hop[1], one_hop[0]
                m_path.append([i_point, e_point]) 

            previous_point = m_path[-1][1]
    return m_path, last_step


def last_point_info(hops, last_step):
    ie = ['isite', 'esite']
    for one_hop in hops:
        if set([last_step[x] for x in ie]) == set([one_hop['iindex'], one_hop['eindex']]):
            if one_hop['to_jimage'] != [0,0,0]:
                if one_hop['hop_label'] == last_step['hop_label']:
                    the_hop = one_hop
    if last_step['isite'] == the_hop['iindex']:
        last_info = [last_step['isite'], last_step['esite'], tuple(the_hop['to_jimage'])]
    else:
        new_jimage = tuple([-u for u in the_hop['to_jimage']])
        last_info = [last_step['isite'], last_step['esite'], new_jimage]
    return last_info


def get_pairs(m_path, fss, last_jump):
    frac_pairs = []
    for i in m_path:
        one_pair = [fss.frac_coords[i[0]]+ np.array([-0.5, -0.5, -0.5]), fss.frac_coords[i[1]]+ np.array([-0.5, -0.5, -0.5])]
        frac_pairs.append(one_pair)
    frac_pairs[-1][1] = last_jump
    cart_pairs = []
    for one_frac_pair in frac_pairs:
        one_cart_pair = [fss.lattice.get_cartesian_coords(u) for u in one_frac_pair]
        cart_pairs.append(one_cart_pair)
    return cart_pairs


def get_extra_scene(pairs, s_radius=0.5, c_radius=0.4):
    '''
    Takes in position pairs and draw a path
    '''
    extra_scene=[]

    [ini_color, final_color]=[[240, 240, 240], [0, 0, 0]]
    div = len(pairs) - 1
    if div == 0:
        rgb_list =  [tuple(ini_color), tuple(final_color)]
    else:
        step_size = [int((final_color[i] - ini_color[i])/(div+1)) for i in range(0,3)]
        rgb_list = [(ini_color[0] + u*step_size[0], ini_color[1] + u*step_size[1], ini_color[2] + u*step_size[2]) for u in range(1, div+1)]
        rgb_list.insert(0, tuple(ini_color))
        rgb_list.append(tuple(final_color))
    rgb_to_html = lambda rgb: '#%02x%02x%02x' % rgb
    html_colors = [rgb_to_html(i) for i in rgb_list]

    extra_scene.append(Spheres(positions=[pairs[0][0]], radius=s_radius, color='#00ff88')) #for now all colors are designated as Li light green
    for i in range(0, len(pairs)):
        extra_scene.append(Spheres(positions=[pairs[i][1]], radius=s_radius, color='#00ff88'))
        extra_scene.append(Cylinders(positionPairs=[pairs[i]], radius=c_radius, color='black'))
    return extra_scene


def get_combined_scene(bs, extra_scene):
    smc = StructureMoleculeComponent(bs, scene_additions=extra_scene)
    return smc