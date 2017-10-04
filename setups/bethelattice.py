import numpy as np, itertools as itt
from scipy.linalg import expm, eigh

from bethe.setups.generic import CycleSetupGeneric
from bethe.operators.hubbard import Site, TriangleMomentum, PlaquetteMomentum, Triangle, TriangleAIAO, TriangleSpinOrbitCoupling, PlaquetteMomentumNambu
from bethe.operators.kanamori import Dimer as KanamoriDimer, MomentumDimer as KanamoriMomentumDimer
from bethe.schemes.bethe import GLocal, WeissField, SelfEnergy, GLocalAFM, WeissFieldAFM, GLocalWithOffdiagonals, WeissFieldAIAO, WeissFieldAFM, GLocalInhomogeneous, WeissFieldInhomogeneous, GLocalAIAO, GLocalNambu, WeissFieldNambu
from bethe.transformation import MatrixTransformation

from pytriqs.gf.local import iOmega_n, inverse


class SingleBetheSetup(CycleSetupGeneric):

    def __init__(self, beta, mu, u, t_bethe, n_iw = 1025, afm = False):
        up = "up"
        dn = "dn"
        spins = [up, dn]
        sites = range(1)
        hubbard = Site(u)
        t_loc = {up: np.zeros([1, 1]), dn: np.zeros([1, 1])}
        blocknames = spins
        blocksizes = [len(sites), len(sites)]
        gf_struct = [[s, sites] for s in spins]
        self.h_int = hubbard
        self.gloc = GLocalWithOffdiagonals(t_bethe, t_loc, blocknames, blocksizes, beta, n_iw)
        #self.gloc = GLocal(t_bethe, t_loc, w1, w2, n_mom, blocknames, blocksizes, beta, n_iw)
        if afm:
            self.g0 = WeissFieldAFM(blocknames, blocksizes, beta, n_iw)
        else:
            self.g0 = WeissField(blocknames, blocksizes, beta, n_iw)
        self.se = SelfEnergy(blocknames, blocksizes, beta, n_iw)
        self.mu = mu
        self.global_moves = {"spin-flip": {("up", 0): ("dn", 0), ("dn", 0): ("up", 0)}}
        self.quantum_numbers = [hubbard.get_n_tot(), hubbard.get_n_per_spin(up)]


class TriangleBetheSetup(CycleSetupGeneric):
    """
    Contributions by Kristina Klafka
    """
    def __init__(self, beta, mu, u, t_triangle, t_bethe, orbital_labels = ["E", "A2", "A1"],
                 symmetric_orbitals = ["A2", "A1"],
                 site_transformation = np.array([[1/np.sqrt(3),1/np.sqrt(3),1/np.sqrt(3)],[0,-1/np.sqrt(2),1/np.sqrt(2)],[-np.sqrt(2./3.),1/np.sqrt(6),1/np.sqrt(6)]]),
                 n_iw = 1025, afm = False):
        up = "up"
        dn = "dn"
        spins = [up, dn]
        sites = range(3)
        blocknames = [s+"-"+k for s in spins for k in orbital_labels]
        blocksizes = [1] * len(blocknames)
        gf_struct = [[n, range(s)] for n, s in zip(blocknames, blocksizes)]
        gf_struct_site = [[s, sites] for s in spins]
        transfbmat = dict([(s, site_transformation) for s in spins])
        transf = self.transf = MatrixTransformation(gf_struct_site, transfbmat, gf_struct)
        a = t_triangle
        t_loc_per_spin = np.array([[0,a,a],[a,0,a],[a,a,0]])
        t_loc = {up: t_loc_per_spin, dn: t_loc_per_spin}
        t_loc = transf.transform_matrix(t_loc)
        hubbard = TriangleMomentum(u, spins, orbital_labels, transfbmat)
        xy = symmetric_orbitals
        self.h_int = hubbard
        if afm:
            self.g0 = WeissFieldAFM(blocknames, blocksizes, beta, n_iw)
        else:
            self.g0 = WeissField(blocknames, blocksizes, beta, n_iw)
        self.gloc = GLocalWithOffdiagonals(t_bethe, t_loc, blocknames, blocksizes, beta, n_iw)
        self.se = SelfEnergy(blocknames, blocksizes, beta, n_iw)
        self.mu = mu
        self.global_moves = {}#{"spin-flip": dict([((s1+"-"+k, 0), (s2+"-"+k, 0)) for k in orbital_labels for s1, s2 in itt.product(spins, spins) if s1 != s2]), "A1A2-flip": dict([((s+"-"+k1, 0), (s+"-"+k2, 0)) for s in spins for k1, k2 in itt.product(xy, xy) if k1 != k2])}
        self.quantum_numbers = [hubbard.get_n_tot(), hubbard.get_n_per_spin(up)]


class TwoOrbitalDimerBetheSetup(CycleSetupGeneric):
    """
    TODO
    """
    def __init__(self, beta, mu, u, j, tc_perp, td_perp, tc_bethe, td_bethe, density_density_only = False, orbitals = ["c", "d"], symmetric_orbitals = [], n_iw = 1025):
        up = "up"
        dn = "dn"
        spins = [up, dn]
        sites = range(2)
        blocknames = [s+"-"+o for s, o in itt.product(spins, orbitals)]
        blocksizes = [2] * 4
        gf_struct = [[n, range(s)] for n, s in zip(blocknames, blocksizes)]
        tc_loc = np.array([[0,tc_perp,],[tc_perp,0]])
        td_loc = np.array([[0,td_perp,],[td_perp,0]])
        t_loc = {bn: t_loc for bn, t_loc in zip(blocknames, [tc_loc, td_loc, tc_loc, td_loc])}
        tc_b = np.array([[tc_bethe, 0],[0, tc_bethe]])
        td_b = np.array([[td_bethe, 0],[0, td_bethe]])
        t_bethe = {bn: t_b for bn, t_b in zip(blocknames, [tc_b, td_b, tc_b, td_b])}
        self.h_int = KanamoriDimer(u, j, spins, orbitals, density_density_only = density_density_only)
        self.g0 = WeissFieldInhomogeneous(blocknames, blocksizes, beta, n_iw)
        self.gloc = GLocalInhomogeneous(t_bethe, t_loc, blocknames, blocksizes, beta, n_iw)
        self.se = SelfEnergy(blocknames, blocksizes, beta, n_iw)
        self.mu = mu
        self.global_moves = {}
        self.quantum_numbers = [self.h_int.n_tot(), self.h_int.sz_tot()]


class TwoOrbitalMomentumDimerBetheSetup(TwoOrbitalDimerBetheSetup):
    def __init__(self, beta, mu, u, j, tc_perp, td_perp, tc_bethe, td_bethe, density_density_only = False, orbitals = ["c", "d"], symmetric_orbitals = [], n_iw = 1025, site_transformation = np.array([[1/np.sqrt(2), 1/np.sqrt(2)],[1/np.sqrt(2), -1/np.sqrt(2)]])):
        spins = ["up", "dn"]
        sites = range(2)
        momenta = ["G", "X"]
        blocknames = [s+"-"+o+"-"+k for s, o, k in itt.product(spins, orbitals, momenta)]
        blocksizes = [1] * 8
        gf_struct = [[n, range(s)] for n, s in zip(blocknames, blocksizes)]
        blocknames_site = [s+"-"+o for s, o in itt.product(spins, orbitals)]
        blocksizes_site = [2] * 4
        gf_struct_site = [[n, range(s)] for n, s in zip(blocknames_site, blocksizes_site)]
        tc_loc_site = np.array([[0,tc_perp,],[tc_perp,0]])
        td_loc_site = np.array([[0,td_perp,],[td_perp,0]])
        t_loc_site = {bn: t_loc_site for bn, t_loc_site in zip(blocknames_site, [tc_loc_site, td_loc_site, tc_loc_site, td_loc_site])}
        site_transformation = {bn: site_transformation for bn in blocknames_site}
        self.transf = MatrixTransformation(gf_struct_site, site_transformation, gf_struct)
        t_loc = self.transf.transform_matrix(t_loc_site)
        t_bethe = {} # diagonal, invariant under site_transformation
        for bn in blocknames:
            if "-"+orbitals[0] in bn:
                t_bethe[bn] = np.array([[tc_bethe]])
            elif "-"+orbitals[1] in bn:
                t_bethe[bn] = np.array([[td_bethe]])
            else:
                assert False, "neither "+orbitals[0]+" nor "+orbitals[1]+" in "+bn
        self.h_int = KanamoriMomentumDimer(u, j, spins, orbitals, density_density_only = density_density_only, momenta = momenta, transf = site_transformation)
        self.g0 = WeissFieldInhomogeneous(blocknames, blocksizes, beta, n_iw)
        self.gloc = GLocalInhomogeneous(t_bethe, t_loc, blocknames, blocksizes, beta, n_iw)
        self.se = SelfEnergy(blocknames, blocksizes, beta, n_iw)
        self.mu = mu
        self.global_moves = {}
        self.quantum_numbers = [self.h_int.n_tot(), self.h_int.sz_tot()]
        


class TriangleAIAOBetheSetup(CycleSetupGeneric):
    """
    merges spin and sitespaces
    space hierarchy: spin, site
    """
    def __init__(self, beta, mu, u , t_triangle, t_bethe, n_iw = 1025, force_real = True,
                 site_transformation = np.array([[1/np.sqrt(3),1/np.sqrt(3),1/np.sqrt(3)],[0,-1/np.sqrt(2),1/np.sqrt(2)],[-np.sqrt(2./3.),1/np.sqrt(6),1/np.sqrt(6)]]),
                 momentum_labels = ["E", "A2", "A1"]):
        self.site_transf = site_transformation
        sites = range(3)
        bn = 'spin-mom'
        self.spins = ['up', 'dn']
        gf_struct = [[bn, range(6)]]
        gf_struct_site = [[s, range(3)] for s in self.spins]
        self.blocknames = [bn]
        blocksizes = [len(sites)*2]
        blocknames_paramag = [s+"-"+k for s in self.spins for k in momentum_labels]
        gf_struct_paramag = [[n, range(1)] for n in blocknames_paramag]
        self.paramag_to_aiao = MatrixTransformation(gf_struct = gf_struct_paramag, gf_struct_new = gf_struct)
        self.momentum_labels = momentum_labels
        t = t_triangle
        hop = np.array([[0,t,t],[t,0,t],[t,t,0]])
        t_loc = {s: hop for s in self.spins}
        site_transformation = {s: site_transformation for s in self.spins}
        transf = MatrixTransformation(gf_struct_site, site_transformation, gf_struct)
        self.t_loc = transf.transform_matrix(t_loc)
        self.h_int = TriangleSpinOrbitCoupling(bn, u, transf = site_transformation)
        self.mu = mu
        self.gloc = GLocalAIAO(t_bethe, self.t_loc, self.blocknames, blocksizes, beta, n_iw)
        self.se = SelfEnergy(self.blocknames, blocksizes, beta, n_iw)
        self.g0 = WeissFieldAIAO(self.blocknames, blocksizes, beta, n_iw)
        self.global_moves = {"spin-flip": dict([((bn, i), (bn, (i+3)%6)) for i in range(6)]), "reflection": dict([((bn, 1), (bn, 2)), ((bn, 2), (bn, 1)), ((bn, 4), (bn, 5)), ((bn, 5), (bn, 4))])}
        self.quantum_numbers = [self.h_int.n_tot()]

    def superindex(self, spin_index, site_index):
        return spin_index * 3 + site_index

    def spin_index(self, superindex):
        return superindex / 3

    def site_index(self, superindex):
        return superindex % 3

    def spin_transf_mat(self, theta, phi = 0):
        py = np.matrix([[0,complex(0,-1)],[complex(0,1),0]])
        pz = np.matrix([[1,0],[0,-1]])
        return expm(complex(0,-1)*theta*py*.5).dot(expm(complex(0,-1)*phi*pz*.5))

    def set_initial_guess(self, selfenergy, g0, e_in = .15, e_out = -.15, v = .15, transform = True, momentum_labels = None):
        """
        initializes with paramagnetic(transform=True) or AIAO(transform=False) solution
        adds a dynamical AIAO symmetry breaking field with the energies e_in, e_out
        and the amplitude v
        paramagnetic_labels is used only if transform=True, and has a default: E, A2, A1
        assumes the paramagnetic solution to be blockdiagonal
        """
        if transform:
            if momentum_labels is None:
                momentum_labels = self.momentum_labels
            s0, s1 = self.spins[0], self.spins[1]
            e, a2, a1 = tuple(lab for lab in self.momentum_labels)
            bn = self.blocknames[0]
            rm = {(s0+'-'+e,0,0): (bn,0,0), (s0+'-'+a2,0,0): (bn,1,1),
                  (s0+'-'+a1,0,0): (bn,2,2), (s1+'-'+e,0,0): (bn,3,3),
                  (s1+'-'+a2,0,0): (bn,4,4), (s1+'-'+a1,0,0): (bn,5,5)}
            self.g0 << self.paramag_to_aiao.reblock_by_map(g0, rm)
            self.se << self.paramag_to_aiao.reblock_by_map(selfenergy, rm)
            excitation_shifts = [1,1,1] # 1 + x shifts by x
            rotation_permutations = [(0,1,2),(2,0,1),(1,2,0)]
        for (i, j, k), shift in zip(rotation_permutations, excitation_shifts):
            self.add_dynamical_aiao_field(e_in * shift, e_out * shift, v, [i, j, k])

    def add_dynamical_aiao_field(self, e_in, e_out, v, permutation):
        """delta_momentum_updn = U R_dag delta_site_aiao R U_dag"""
        se = self.se
        u = self.site_transf
        r = [self.spin_transf_mat(i * 2*np.pi /3.) for i in permutation]
        for ri in r:
            assert np.allclose(ri.imag, 0), "imag fails tail multiplication"
            ri = np.array(ri.real, dtype = float)
        bn = self.blocknames[0]
        eps = np.array([e_in, e_out])
        spins, sites = range(2), range(3)
        for s0, i0, s1, i1 in itt.product(spins, sites, spins, sites):
            a0, a1 = self.superindex(s0, i0), self.superindex(s1, i1)
            #se[bn][a0, a1] += np.sum([u[i0, j] * r[j][t, s0].conjugate() * v**2 * inverse(iOmega_n - eps[t]) * r[j][t, s1] *u[i1, j].conjugate() for t, j in itt.product(spins, sites)])
            se[bn][a0, a1] += np.sum([u[i0, j] * r[j][t, s0].real * v**2 * inverse(iOmega_n - eps[t]) * r[j][t, s1].real *u[i1, j].conjugate() for t, j in itt.product(spins, sites)])


class PlaquetteBetheSetup(CycleSetupGeneric):
    """
    site transformation must be unitary and diagonalize G, assuming all sites are equal
    """
    def __init__(self, beta, mu, u, tnn_plaquette, tnnn_plaquette, t_bethe, w1 = None, w2 = None,
                 n_mom = 3, orbital_labels = ["G", "X", "Y", "M"], symmetric_orbitals = ["X", "Y"],
                 site_transformation =.5*np.array([[1,1,1,1],[1,-1,1,-1],[1,1,-1,-1],[1,-1,-1,1]]),
                 n_iw = 1025):
        up = "up"
        dn = "dn"
        spins = [up, dn]
        sites = range(4)
        blocknames = [s+"-"+k for s in spins for k in orbital_labels]
        blocksizes = [1] * len(blocknames)
        gf_struct = [[n, range(s)] for n, s in zip(blocknames, blocksizes)]
        gf_struct_site = [[s, sites] for s in spins]
        transfbmat = dict([(s, site_transformation) for s in spins])
        transf = MatrixTransformation(gf_struct_site, transfbmat, gf_struct)
        a, b = tnn_plaquette, tnnn_plaquette
        t_loc_per_spin = np.array([[0,a,a,b],[a,0,b,a],[a,b,0,a],[b,a,a,0]])
        t_loc = {up: t_loc_per_spin, dn: t_loc_per_spin}
        t_loc = transf.transform_matrix(t_loc)
        hubbard = PlaquetteMomentum(u, spins, orbital_labels, transfbmat)
        xy = symmetric_orbitals
        self.h_int = hubbard.get_h_int()
        self.gloc = GLocal(t_bethe, t_loc, w1, w2, n_mom, blocknames, blocksizes, beta, n_iw)
        self.g0 = WeissField(blocknames, blocksizes, beta, n_iw)
        self.se = SelfEnergy(blocknames, blocksizes, beta, n_iw)
        self.mu = mu
        self.global_moves = {"spin-flip": dict([((s1+"-"+k, 0), (s2+"-"+k, 0)) for k in orbital_labels for s1, s2 in itt.product(spins, spins) if s1 != s2]), "XY-flip": dict([((s+"-"+k1, 0), (s+"-"+k2, 0)) for s in spins for k1, k2 in itt.product(xy, xy) if k1 != k2])}
        self.quantum_numbers = [hubbard.get_n_tot(), hubbard.get_n_per_spin(up)]

    def init_noninteracting(self):
        self.se.zero()

    def init_centered_semicirculars(self): # TODO test
        for n, b in self.se:
            b << self.gloc.make_matrix(self.mu)[n]


class NambuMomentumPlaquette(CycleSetupGeneric): # TODO mu?

    def __init__(self, beta, mu, u, tnn_plaquette, tnnn_plaquette, t_bethe = 1, n_iw = 1025):
        g, x, y, m = "G", "X", "Y", "M"
        up, dn = "up", "dn"
        self.spins = [up, dn]
        self.sites = range(4)
        self.momenta = [g, x, y, m]
        self.spinors = range(2) #nambu spinors: 0: particle, 1: hole
        self.block_labels = [k for k in self.momenta]
        self.gf_struct = [[l, self.spinors] for l in self.block_labels]
        self.gf_struct_site = [[s, self.sites] for s in self.spins]
        transformation_matrix = .5 * np.array([[1,1,1,1],
                                               [1,-1,1,-1],
                                               [1,1,-1,-1],
                                               [1,-1,-1,1]])
        self.transformation = dict([(s, transformation_matrix) for s in self.spins])
        a, b = tnn_plaquette, tnnn_plaquette
        t_loc = np.array([[0,a,a,b],[a,0,b,a],[a,b,0,a],[b,a,a,0]])
        t_loc = {up: np.array(t_loc), dn: np.array(t_loc)}
        self.reblock_map = {(up,0,0):(g,0,0), (dn,0,0):(g,1,1), (up,1,1):(x,0,0), (dn,1,1):(x,1,1), (up,2,2):(y,0,0), (dn,2,2):(y,1,1), (up,3,3):(m,0,0), (dn,3,3):(m,1,1)}
        self.mom_transf = MatrixTransformation(self.gf_struct_site, self.transformation, self.gf_struct, reblock_map = self.reblock_map)
        t_loc = self.mom_transf.transform_matrix(t_loc)
        self.mu = mu
        self.operators = PlaquetteMomentumNambu(u, self.spins, self.momenta, self.transformation)
        self.h_int = self.operators.get_h_int()
        self.gloc = GLocalNambu(t_bethe, t_loc, self.momenta, [2]*4, beta, n_iw)
        self.g0 = WeissFieldNambu(self.momenta, [2]*4, beta, n_iw)
        self.se = SelfEnergy(self.momenta, [2]*4, beta, n_iw)
        self.global_moves = {}
        self.quantum_numbers = []

    def set_data(self, storage, load_mu = True, transform = True):
        """initializes by previous non-nambu solution and anomalous field or by 
        nambu-solution"""
        gloc = storage.load('g_imp_iw')
        g0 = storage.load('g_weiss_iw')
        se = storage.load('se_imp_iw')
        if load_mu:
            mu = storage.load('mu')
            self.mu = self.mom_transf.reblock_by_map(mom_transf.transform_matrix({up: mu * np.identity(4), dn: mu * np.identity(4)}), self.reblock_map)
        if transform:
            self.transform_particlehole(gloc, self.gloc)
            self.transform_particlehole(g0, self.g0)
            self.transform_particlehole(se, self.se)
        else:
            self.gloc << gloc
            self.g0 << g0
            self.se << se

    def set_anomalous(self, factor):
        """d-wave, spin-singlet"""
        xi = self.momenta[1]
        yi = self.momenta[2]
        g = self.se
        n_points = len([iwn for iwn in g.mesh])/2
        for offdiag in [[0,1], [1,0]]:
            for n  in [n_points, n_points-1]:
                inds = tuple([n] + offdiag)
                g[xi].data[inds] = factor * g.beta * .5
            offdiag = tuple(offdiag)
            g[yi][offdiag] << -1 * g[xi][offdiag]

    def transform_particlehole(self, g_sm, g_nambu):
        """gets a non-nambu greensfunction to initialize nambu"""
        gf_struct_mom = dict([(s+'-'+k, [0]) for s in self.spins for k in self.momenta])
        to_nambu = MatrixTransformation(gf_struct_mom, None, self.gf_struct)
        up, dn = self.spins
        reblock_map = [[(up+'-'+k,0,0), (k,0,0)] for k in self.momenta]
        reblock_map += [[(dn+'-'+k,0,0), (k,1,1)]  for k in self.momenta]
        reblock_map = dict(reblock_map)
        for b, i, j in g_sm.all_indices:
            b_nam, i_nam, j_nam = reblock_map[(b, int(i), int(j))]
            if i_nam == 0 and j_nam == 0:
                g_nambu[b_nam][i_nam, j_nam] << g_sm[b][i, j]
            if i_nam == 1 and j_nam == 1:
                g_nambu[b_nam][i_nam, j_nam] << -1 * g_sm[b][i, j].conjugate()
