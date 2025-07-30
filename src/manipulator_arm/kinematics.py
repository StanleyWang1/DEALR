"""Symbolic and numerical kinematics using modified DH parameters."""

import numpy as np
import sympy as sp
import time

# -------------------- CONSTANTS --------------------
L1_CONST = 0.08545  # Link 1 length [m]
L2_CONST = 0.396008  # Link 2 length [m]
L3_CONST = 0.386435  # Link 3 length [m]

# -------------------- SYMBOLIC VARIABLES --------------------
th1, th2, th3, th4 = sp.symbols("th1 th2 th3 th4", real=True)

# Modified DH parameters
MDH_sym = {
    1: {"a": 0,         "al": 0,            "d": L1_CONST,  "th": th1},
    2: {"a": 0,         "al": sp.pi / 2,    "d": 0,         "th": th2},
    3: {"a": L2_CONST,  "al": 0,            "d": 0,         "th": th3},
    4: {"a": L3_CONST,  "al": 0,            "d": 0,         "th": th4},
}

def sym_MDH_forward(dh_param: dict) -> sp.Matrix:
    """Return the symbolic homogeneous transform for a link using modified DH parameters."""
    a = dh_param["a"]  # a(i-1)
    al = dh_param["al"]  # alpha(i-1)
    d = dh_param["d"]  # d(i)
    th = dh_param["th"]  # theta(i)

    return sp.Matrix([
        [sp.cos(th), -sp.sin(th), 0, a],
        [sp.sin(th)*sp.cos(al), sp.cos(th)*sp.cos(al), -sp.sin(al), -sp.sin(al)*d],
        [sp.sin(th)*sp.sin(al), sp.cos(th)*sp.sin(al), sp.cos(al), sp.cos(al)*d],
        [0, 0, 0, 1],
    ])


def sym_forward_kinematics(mdh: dict) -> sp.Matrix:
    """Compute the symbolic forward kinematics for the entire chain."""
    T = sp.eye(4)
    for i in sorted(mdh.keys()):
        T @= sym_MDH_forward(mdh[i])
    return T


def sym_jacobian_linear(T: sp.Matrix) -> sp.Matrix:
    """Compute the symbolic linear velocity Jacobian."""
    x, y, z = T[0, 3], T[1, 3], T[2, 3]

    return sp.Matrix([
        [x.diff(th1), x.diff(th2), x.diff(th3), x.diff(th4)],
        [y.diff(th1), y.diff(th2), y.diff(th3), y.diff(th4)],
        [z.diff(th1), z.diff(th2), z.diff(th3), z.diff(th4)],
    ])


def sym_jacobian_angular(mdh: dict) -> sp.Matrix:
    """Compute the symbolic angular velocity Jacobian (not general for all manipulators)."""
    # Individual link transforms
    T01 = sym_MDH_forward(mdh[1])
    T12 = sym_MDH_forward(mdh[2])
    T23 = sym_MDH_forward(mdh[3])
    T34 = sym_MDH_forward(mdh[4])

    # Cumulative transforms
    T01_cum = T01
    T02_cum = T01 @ T12
    T03_cum = T02_cum @ T23
    T04_cum = T03_cum @ T34

    # z-axes in base frame
    z1 = T01_cum[:3, 2]
    z2 = T02_cum[:3, 2]
    z3 = sp.zeros(3, 1)  # Prismatic joint → no angular velocity
    z4 = T04_cum[:3, 2]

    return sp.Matrix.hstack(z1, z2, z3, z4)


def num_forward_kinematics(joint_coords: list[float]) -> np.ndarray:
    """Compute numerical forward kinematics for given joint coordinates."""
    return np.array(FK_num(*joint_coords))


def num_jacobian(joint_coords: list[float]) -> np.ndarray:
    """Compute numerical Jacobian for given joint coordinates."""
    return np.array(J_num(*joint_coords))


# -------------------- SYMBOLIC DERIVATIONS --------------------
print("Starting symbolic kinematic derivations...")
# T = sp.simplify(sym_forward_kinematics(MDH_sym))
T = sym_forward_kinematics(MDH_sym)
print("Computed forward kinematics.")

FK_num = sp.lambdify((th1, th2, th3, th4), T, modules="numpy")

Jv = sp.simplify(sym_jacobian_linear(T))
print("Computed linear velocity Jacobian.")

Jw = sp.simplify(sym_jacobian_angular(MDH_sym))
print("Computed angular velocity Jacobian.")

y_e = T[:3, 1]
z_0 = sp.Matrix([0, 0, 1])
c = z_0.cross(y_e)
J_orient = c.T @ Jw
print("Computed task orientation Jacobian")

J = sp.Matrix.vstack(Jv, J_orient)
J_num = sp.lambdify((th1, th2, th3, th4), J, modules="numpy")

# -------------------- TEST CASE --------------------
test_config = [0, np.pi / 2, -np.pi / 2, np.pi / 2]
print(num_forward_kinematics(test_config))
print(num_jacobian(test_config))

# -------------------- BENCHMARKING --------------------
# print("\nBenchmarking FK and Jacobian for 100 random configs...")

# # Generate 100 random configurations: th1, th2, th3, th4
# configs = np.random.uniform(low=-np.pi, high=np.pi, size=(100, 4))

# # Benchmark FK
# start_fk = time.perf_counter()
# for q in configs:
#     _ = num_forward_kinematics(q)
# end_fk = time.perf_counter()
# avg_fk_ms = (end_fk - start_fk) / len(configs) * 1000

# # Benchmark Jacobian
# start_jac = time.perf_counter()
# for q in configs:
#     _ = num_jacobian(q)
# end_jac = time.perf_counter()
# avg_jac_ms = (end_jac - start_jac) / len(configs) * 1000

# print(f"Average FK runtime: {avg_fk_ms:.4f} ms per call")
# print(f"Average Jacobian runtime: {avg_jac_ms:.4f} ms per call")
