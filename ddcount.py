#!/usr/bin/python

import pickle
import copy
import sys
import math
import pygame
import numpy
import os
import shutil
from collections import defaultdict

#===================================================================
# read in a list of vertices in format (row, column, x, y).  (row, column) just
# functions as a key.  Store in a dictionary keyed by the above tuple.
def read_vertices(filename):
    coords = {}
    f = open(filename, 'r')
    for line in f:
        (row,col,x,y) = line.strip().split(',')
        coords[int(row),int(col)] = (float(x),float(y))
    f.close()
    return coords

#===================================================================
# Read in a list of edges.  Store in a dictionary.  Each edge is a "frozen set" 
# which is an immutable, unordered tuple
def read_edges(filename):
    edges = {}
    f = open(filename, 'r')
    for line in f:
        (r1,c1,r2,c2) = line.strip().split(',')
        e = frozenset([(int(r1),int(c1)),(int(r2),int(c2))])
        edges[e] = 1
    f.close()
    return edges

def write_edges(edges, filename):
    f = open(filename, 'w')
    for e in edges:
        ends = [point for point in e]  
        outputlist = [str(i) for i in (ends[0][0], ends[0][1], ends[1][0], ends[1][1])]
        output =  outputlist[0] + "," + outputlist[1] + "," 
        output += outputlist[2] + "," + outputlist[3] + "\n"  
        f.write(output)
    f.close()

#===============================================================
# Read in a list of hexagons.  Store in a list.
def read_hexagons(filename):
    hexagons = []
    f = open(filename, 'r')
    for line in f:
        n = [int(s) for s in line.strip().split(',')]
        hexagons.append((
                (n[0],n[1]), (n[2],n[3]), (n[4],n[5]),
                (n[6],n[7]), (n[8],n[9]), (n[10],n[11])
            ))
    f.close()
    return hexagons

# read in a list of rhombi.  Store in a list.
def read_rhombi(filename):
    rhombi = {}
    f = open(filename, 'r')
    for line in f:
        n = [int(s) for s in line.strip().split(',')]
        edge = frozenset([(n[0], n[1]), (n[2],n[3])])
        rhombus = [(n[4],n[5]),(n[6],n[7]),(n[8],n[9]),(n[10],n[11])]
        rhombi[edge] = rhombus
    f.close()
    return rhombi


#===================================================================
# Load a dimerpaint configuration.
# Lifted from Dimerpaint.  Needs modification before using.
def load(basename):
    if not os.path.isdir(basename):
        exit("Can't find "+basename)

    coords = read_vertices(basename + "full.vertex")
    unscaled_coords = copy.deepcopy(coords)
    background = read_edges(basename + "full.edge")
    hexagons = read_hexagons(basename + "full.hexagon")
    dualcoords = read_vertices(basename + "full.dualvertex")
    unscaled_dualcoords = copy.deepcopy(dualcoords)
    rhombi = read_rhombi(basename + "full.rhombus")

    matching_A = read_edges(basename + "A.edge")
    matching_B = read_edges(basename + "B.edge")
    matchings = [matching_A, matching_B]

    if os.path.isfile(basename + "show.pkl"):
        showfile = open(basename + "show.pkl", "rb")
        show = pickle.load(showfile)
        showfile.close()
    else:
        show = {
            "A": True,
            "B": True,
            "Center": True,
            "Highlight": True,

            "A_background": True,
            "A_matching": True,
            "A_tiling": False,
            "A_boundary": False,
            "A_centers": True,
            "A_boxes": False,

            "B_background": True,
            "B_matching": True,
            "B_tiling": False,
            "B_boundary": False,
            "B_centers": True,
            "B_boxes": False,

            "center_background": False,
            "center_A_matching": True,
            "center_B_matching": True,
            "center_A_boundary": True,
            "center_B_boundary": True,
            "center_doubled_edges": True,
        }
    if os.path.isfile(basename + "lengths.pkl"):
        lengthsfile = open(basename + "lengths.pkl", "rb")
        lengths = pickle.load(lengthsfile)
        lengthsfile.close()
        if "old_screen_size" in lengths:
           del lengths["old_screen_size"]
    else:
        lengths = {}

    default_lengths = {
        "button_height": 20,
        "dimer_width":3,
        "hex_flipper_radius":4,
        "overlay_offset":0,
        "tile_edge_width":2,
        "shading_intensity":1,
        "randomize_steps":500,
        "y": 45,
        }

    for param in default_lengths.keys():
        if param not in lengths:
            lengths[param] = default_lengths[param]
    # this allows us to add new keys
    show_default_dict = defaultdict(bool)
    show_default_dict.update(show)

    renderables = {"highlight":[{},{}], # highlighted edges on left and right
                   "background":background, 
                   "matchings":matchings, 
                   "hexagons":hexagons, 
                   "rhombi": rhombi,
                   "coords": coords,
                   "unscaled_coords": coords,
                   "dualcoords":dualcoords,
                   "unscaled_dualcoords":dualcoords,
                   "show":show_default_dict,
                   "lengths":lengths}
#    compute_picture_sizes(renderables)
    return renderables

#==============================================================
# make an adjacency map from a matching. 
# Lifted from Dimerpaint.  Needs modification before using.
def adjacency_map(M): 
    adj = {}
    for edge in M:
        endpoints = [endpt for endpt in edge]
        adj[endpoints[0]] = endpoints[1]
        adj[endpoints[1]] = endpoints[0]
    return adj

#==============================================================
# Find a path in the superposition of two matchings, starting at
# a point in the first matching.  Might be a loop.
# The matchings should be given as adjacency maps (see adjacency_map)
# The path is returned as a list of vertices.  If the path is closed then
# the starting vertex is repeated.
#
# Lifted from Dimerpaint.  Needs modification before using.
def find_path(adj1, adj2, start):
    path = [start];
    p1 = start;
    try:
        p2 = adj2[p1]
        path.append(p2)
        p1 = adj1[p2]
        while(p1 != start):
            path.append(p1)
            p2 = adj2[p1]
            path.append(p2)
            p1 = adj1[p2]
        path.append(p1)
        return path
    except KeyError: 
        pass

# We fall through to here if path isn't closed.  Get the rest of the path.

    p1 = start
    try:  
        p2 = adj1[p1]
        path.insert(0,p2)
        p1 = adj2[p2]
        while(p1 != start):
            path.insert(0,p1)
            p2 = adj1[p1]
            path.insert(0,p2)
            p1 = adj2[p2]

    except KeyError: 
        pass

    return path


#===================================================================
# Highlight a path in a dimerpaint configuration
# Lifted from Dimerpaint.  Needs modification before using.
def highlight_path(renderables, m0, m1, unordered_edge):
    matchings = renderables["matchings"]
    edge = [endpoint for endpoint in unordered_edge]
    adj0 = adjacency_map(matchings[m0])
    adj1 = adjacency_map(matchings[m1])
    path = find_path(adj0, adj1, edge[0])

    #list of edges corresponding to the path
    loop = []
    all_highlighted = True

    for i in range(len(path) - 1):
        e = frozenset([path[i], path[i+1]])
        loop.append(e)
        if e not in renderables["highlight"][m0]: 
            all_highlighted = False
        if e not in renderables["highlight"][m1]:
            all_highlighted = False

    if all_highlighted:
        for e in loop:
            del renderables["highlight"][m0][e]
            del renderables["highlight"][m1][e]
    else:
        for e in loop:
            renderables["highlight"][m0][e] = 1
            renderables["highlight"][m1][e] = 1
 

#==============================================================
# Can we flip a matching around a hexagon?  We take the matching as an
# adjacency map.  To do this, count the vertices around the hexagon
# which are matched to another point on the hexagon, and see if it is 6. 
def is_active(hexagon, adj):
    acc = 0
    hexdict = {}
    for p in hexagon:
        hexdict[p] = 1
    for p in hexagon:
        if ((p in adj) and (adj[p] in hexdict)): acc += 1
    return(acc == 6)

#============================================================================
# Flip one hexagon.
def flip_hex(matching, hexagons, index):
    h = hexagons[index]
    edges = [frozenset([h[i], h[(i+1)%6]]) for i in range(6)]
    for e in edges:
        if(e in matching): 
            del matching[e]
        else:
            matching[e] = 1



#====================================================================
# Run the glauber dynamics to randomize one picture
def randomize(matching, hexlist, steps):
    for trial in range(steps):
        # Choose a random index i
        adj = adjacency_map(matching)
        activelist = []
        for i in range(len(hexlist)):
            if is_active(hexlist[i],adj):
                activelist.append(i)

        i = numpy.random.randint(len(activelist))
        if is_active(hexlist[activelist[i]], adj):
            flip_hex(matching, hexlist, activelist[i]) 



