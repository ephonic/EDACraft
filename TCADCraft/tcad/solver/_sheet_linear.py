"""Owned Newton solve sessions with shareable, read-only SuperLU factors."""
from dataclasses import dataclass

import numpy as np
from scipy.sparse.linalg import LinearOperator, gmres, splu


@dataclass(frozen=True)
class _FrozenFactor:
    # Only solve() is used on a published factor; it is never refactorized.
    factor: object
    shape: tuple
    operator_key: tuple | None = None
    ordering: str = 'COLAMD'

    def __deepcopy__(self, memo):
        memo[id(self)] = self
        return self


class _ReusedGMRES:
    """Candidate cache and counters belong to exactly one nonlinear solve.

    A caller publishes ``factor`` only after its whole transaction succeeds.
    Failure never alters the incoming factor or any counters on its owner.
    """
    def __init__(self, factor, tolerance, operator_key=None, ordering='COLAMD'):
        if not isinstance(ordering,str) or ordering not in ('COLAMD','MMD_AT_PLUS_A'):
            raise ValueError("linear_ordering must be 'COLAMD' or 'MMD_AT_PLUS_A'")
        self.ordering = ordering
        self.invalidated_initial_factor = bool(
            factor is not None and (factor.operator_key != operator_key or factor.ordering != ordering))
        self.factor = None if self.invalidated_initial_factor else factor
        self.operator_key = operator_key
        self.atol = min(1e-14, .01 * tolerance)
        if not self.atol > 0:
            raise FloatingPointError('linear absolute tolerance is not representable')
        self.calls = []
        self.factorizations = 0
        self.reused_initial_factor = self.factor is not None

    def solve(self, A, b):
        A = A.tocsr()
        attempts = []
        for attempt in range(2):
            if self.factor is None or self.factor.shape != A.shape or attempt:
                self.factor = _FrozenFactor(splu(A.tocsc(),permc_spec=self.ordering),
                                            A.shape, self.operator_key, self.ordering)
                self.factorizations += 1
            iterations = [0]

            def count(_):
                iterations[0] += 1

            M = LinearOperator(A.shape, matvec=self.factor.factor.solve, dtype=A.dtype)
            # SciPy stops on an L2 residual. The public acceptance bound is
            # per row; an unscaled L2 target can stagnate at roundoff as the
            # number of bulk equations grows. Always check the original
            # max norm, and correct a valid RMS stop that misses that bound.
            l2_target = self.atol * np.sqrt(b.size)
            x, info = gmres(A, b, M=M,
                rtol=0., atol=l2_target, restart=60, maxiter=10,
                callback=count, callback_type='pr_norm')
            residual = b - A @ x
            initial_defect = float(np.max(np.abs(residual)))
            initial_l2 = float(np.linalg.norm(residual))
            initial_info = int(info)
            correction = None
            correction_ok = True
            if (info == 0 and np.all(np.isfinite(x)) and
                    np.isfinite(initial_defect) and initial_defect > self.atol and
                    initial_l2 <= l2_target):
                previous_iterations = iterations[0]
                dx, correction_info = gmres(A, residual, M=M,
                    rtol=0., atol=self.atol, restart=60, maxiter=10,
                    callback=count, callback_type='pr_norm')
                correction_defect = float(np.max(np.abs(A @ dx - residual)))
                correction_ok = bool(correction_info == 0 and np.all(np.isfinite(dx)) and
                    np.isfinite(correction_defect) and correction_defect <= self.atol)
                correction = dict(info=int(correction_info),
                    iterations=iterations[0]-previous_iterations,
                    true_residual_linf=correction_defect if np.isfinite(correction_defect) else None,
                    accepted=correction_ok)
                x = x + dx
                info = correction_info
            defect = float(np.max(np.abs(A @ x - b)))
            accepted = bool(initial_info == 0 and info == 0 and correction_ok and np.all(np.isfinite(x)) and
                            np.isfinite(defect) and defect <= self.atol)
            attempts.append(dict(info=int(info), iterations=iterations[0],
                initial_info=initial_info, gmres_absolute_l2_tolerance=float(l2_target),
                initial_true_scaled_residual_linf=initial_defect if np.isfinite(initial_defect) else None,
                initial_true_scaled_residual_l2=initial_l2 if np.isfinite(initial_l2) else None,
                correction=correction,
                true_scaled_residual_linf=defect if np.isfinite(defect) else None,
                accepted=accepted))
            if accepted:
                self.calls.append(attempts)
                return x
        error = FloatingPointError('reused GMRES failed true row-scaled residual after one refresh '
            f'(info={info}, max_residual={defect}, limit={self.atol})')
        error.linear_solver_attempts = attempts
        raise error

    def diagnostics(self):
        return dict(method='reused_gmres', factor_ordering=self.ordering, absolute_tolerance=self.atol,
            linear_solves=len(self.calls), factorizations=self.factorizations,
            reused_initial_factor=self.reused_initial_factor,
            invalidated_initial_factor=self.invalidated_initial_factor,
            acceptance_norm='true_row_scaled_linf',
            gmres_iterations=sum(a['iterations'] for c in self.calls for a in c),
            gmres_corrections=sum(a['correction'] is not None for c in self.calls for a in c),
            refreshes=sum(len(c)-1 for c in self.calls),
            max_accepted_true_scaled_residual_linf=max(
                (c[-1]['true_scaled_residual_linf'] for c in self.calls), default=0.),
            attempts=self.calls)
