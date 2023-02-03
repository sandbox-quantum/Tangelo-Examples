"""Script to perform the graph-|q><c| problem decomposition method on dihydrogen
clusters.

Ref:
Zhang, J. H. & Iyengar, S. S.
Graph-|Q⟩⟨C|, a Graph-Based Quantum/Classical Algorithm for Efficient Electronic
Structure on Hybrid Quantum/Classical Hardware Systems: Improved Quantum Circuit
Depth Performance. J. Chem. Theory Comput. (2022) DOI:10/gqk8xq.
"""

from itertools import combinations

import numpy as np
from scipy.spatial.distance import pdist
import networkx as nx

from tangelo import SecondQuantizedMolecule
from tangelo.algorithms.classical import CCSDSolver
from tangelo.algorithms.variational import BuiltInAnsatze
from tangelo.problem_decomposition import ONIOMProblemDecomposition
from tangelo.problem_decomposition.oniom import Fragment


# Drawn with Avogadro.
h2_cluster = [
    ("H", (-0.34544, 0.69378, -0.04015)), ("H", (0.23022, 0.34448, -0.25894)),
    ("H", (-1.58611, -1.78881, -0.46674)), ("H", (-1.90971, -1.58284, -1.06167)),
    ("H", (0.55704, 2.76197, -2.63723)), ("H", (0.664, 2.59442, -1.95773)),
    ("H", (-0.87134, 0.30758, -2.87158)), ("H", (-1.41817, 0.69715, -2.64693)),
    ("H", (1.37563, 1.78484, 1.9478)), ("H", (1.49692, 2.2646, 1.44144)),
    ("H", (-1.37382, -2.55666, 2.19738)), ("H", (-0.94698, -2.01344, 2.35222))
]

# Compute the centroids.
centroids = list()
for i in range(0, 12, 2): #  12 hydrogen atoms, 2 atoms per molecule.
    h2_xyz = np.array([
        h2_cluster[i][1],
        h2_cluster[i+1][1]
    ])
    centroid = np.mean(h2_xyz, axis=0)
    centroids.append(centroid)
centroids = np.array(centroids)

# Distances between the centroids.
distances = pdist(centroids, metric="euclidean")

# Creating a graph.
G = nx.Graph()
G.add_nodes_from([i for i in range(6)])
for i, j in combinations(range(6), 2):

    # m = total number of observations (atoms)
    # atom i, j (labels)
    # m * i + j - ((i + 2) * (i + 1)) // 2
    index = (6 * i) + j - ((i + 2) * (i + 1)) // 2

    if distances[index] <= 4.0:
        G.add_edge(i, j)

# List of rank-0, -1 and -2 simplexes.
fragments = [list(clique) for clique in nx.enumerate_all_cliques(G) if len(clique) <= 3]

# Level 0 (Hartree-Fock) options.
level0_options = {"basis": "sto-3g"}
# Level 1 (VQE-UCCSD) options.
level1_options = {"basis": "sto-3g", "qubit_mapping": "scbk", "ansatz": BuiltInAnsatze.UCCSD}

# Getting the full-system level-0 energy.
system = SecondQuantizedMolecule(h2_cluster, q=0, spin=0, basis=level0_options["basis"])
e = system.mf_energy

# Computing the Graph-|Q><C| energy.
for molecule_ids in fragments:

    # Overcounting correction.
    correction = 0
    for frag_ids in fragments:
        if len(frag_ids) < len(molecule_ids):
            continue

        if all(i in frag_ids for i in molecule_ids):
            correction += (-1)**(len(frag_ids)-1)

    if correction == 0:
        continue

    # Converting molecule_ids (0-5) to atom ids (0-11). This is system
    # dependent.
    atoms_ids = list()
    for molecule_id in molecule_ids:
        atoms_ids.extend([2*molecule_id, 2*molecule_id+1])

    # (-1)^r factor in eq 4.
    prefactor_r = (-1)**(len(molecule_ids) - 1)

    # Construction of the ONIOM solver.
    frag = Fragment(solver_low="hf", options_low=level0_options,
                    solver_high="vqe", options_high=level1_options)
    oniom_solver = ONIOMProblemDecomposition({
        "geometry": [h2_cluster[i] for i in atoms_ids],
        "fragments": [frag]
    })
    e_oniom = oniom_solver.simulate()

    # Right part of eq 4.
    e += prefactor_r * e_oniom * correction

# Computing the all-system CCSD energy (for comparison).
e_ccsd = CCSDSolver(system).simulate()

print(f"Graph-|Q><C| energy: {e}")
print(f"Hartree-Fock energy: {system.mf_energy}")
print(f"CCSD energy: {e_ccsd}")
