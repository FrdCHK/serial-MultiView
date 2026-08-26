"""Spawn-safe per-IF execution helpers for the MultiView delay solver."""

from collections import deque
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
import multiprocessing
import operator
import os
from typing import Any, Callable, Dict, Iterable, List, Optional

import numpy as np

from .viterbi_kalman_altaz import fit_viterbi_kalman_gradient


ProgressCallback = Optional[Callable[[Dict[str, Any]], None]]


@dataclass(frozen=True)
class DelayIfSolveInput:
    """Immutable numerical input for one independent IF solve."""

    if_id: int
    t: np.ndarray
    source_id: np.ndarray
    delta_el: np.ndarray
    delta_az: np.ndarray
    delay: np.ndarray
    variance: np.ndarray
    orig_index: np.ndarray
    kalman_factor: float
    ambiguity_spacing: float
    integer_states: Iterable[int]
    max_jump: int
    jump_penalty: float
    robust: bool
    huber_c: float
    z_out: float
    max_outlier_iterations: int
    fix_initial_integer: Any
    p0_gradient: Optional[float]
    rts_smoothing: bool
    reverse: bool = False


@dataclass(frozen=True)
class DelayIfSolveResult:
    """Result returned from one IF worker without mutating ``Antenna``."""

    if_id: int
    state: np.ndarray
    t: np.ndarray
    integer_path: np.ndarray
    orig_index: np.ndarray
    outlier_mask: np.ndarray
    standardized_residual: np.ndarray


class DelayIfSolveError(RuntimeError):
    """Identify the IF whose worker prevented an atomic MultiView update."""

    def __init__(self, if_id: int, cause: BaseException):
        self.if_id = int(if_id)
        self.cause = cause
        super().__init__(f"IF{self.if_id + 1} solve failed: {cause}")


def progress_event(event_type: str, **values: Any) -> Dict[str, Any]:
    """Build the internal structured progress-event shape."""

    return {"type": event_type, **values}


def emit_progress(callback: ProgressCallback, event_type: str, **values: Any) -> None:
    """Send an event when a progress consumer is available."""

    if callback is not None:
        callback(progress_event(event_type, **values))


def validate_parallel_workers(value: Any) -> int:
    """Return a non-negative integer worker setting without silent coercion."""

    if isinstance(value, (bool, np.bool_)):
        raise ValueError("parallel_workers must be a non-negative integer.")
    try:
        workers = operator.index(value)
    except TypeError as exc:
        raise ValueError("parallel_workers must be a non-negative integer.") from exc
    if workers < 0:
        raise ValueError("parallel_workers must be a non-negative integer.")
    return int(workers)


def effective_worker_count(task_count: int, parallel_workers: int) -> int:
    """Resolve ``0`` to an automatic CPU-aware worker count."""

    task_count = int(task_count)
    workers = validate_parallel_workers(parallel_workers)
    if task_count <= 0:
        return 0
    requested = (os.cpu_count() or 1) if workers == 0 else workers
    return min(task_count, max(1, requested))


def solve_delay_if(task: DelayIfSolveInput) -> DelayIfSolveResult:
    """Run the sequential Viterbi/Kalman/RTS solve for one IF."""

    fit = fit_viterbi_kalman_gradient(
        task.t,
        task.source_id,
        task.delta_el,
        task.delta_az,
        task.delay,
        task.variance,
        task.kalman_factor,
        task.ambiguity_spacing,
        integer_states=task.integer_states,
        max_jump=task.max_jump,
        jump_penalty=task.jump_penalty,
        robust=task.robust,
        huber_c=task.huber_c,
        z_out=task.z_out,
        max_outlier_iterations=task.max_outlier_iterations,
        fix_initial_integer=task.fix_initial_integer,
        p0_gradient=task.p0_gradient,
        rts_smoothing=task.rts_smoothing,
    )
    if task.reverse:
        return DelayIfSolveResult(
            if_id=task.if_id,
            state=fit.state[::-1],
            t=task.t[::-1],
            integer_path=fit.integer_path[::-1],
            orig_index=task.orig_index[::-1],
            outlier_mask=fit.outlier_mask[::-1],
            standardized_residual=fit.standardized_residual[::-1],
        )
    return DelayIfSolveResult(
        if_id=task.if_id,
        state=fit.state,
        t=task.t,
        integer_path=fit.integer_path,
        orig_index=task.orig_index,
        outlier_mask=fit.outlier_mask,
        standardized_residual=fit.standardized_residual,
    )


def _cancel_remaining(
    pending: deque,
    active: Dict[Any, DelayIfSolveInput],
    callback: ProgressCallback,
) -> None:
    """Cancel queued work and drain already-running workers cleanly."""

    while pending:
        task = pending.popleft()
        emit_progress(callback, "if_state", if_id=task.if_id, state="cancelled")
    for future, task in list(active.items()):
        if future.cancel():
            emit_progress(callback, "if_state", if_id=task.if_id, state="cancelled")
            active.pop(future, None)
    for future, task in list(active.items()):
        try:
            future.result()
        except BaseException:
            pass
        emit_progress(callback, "if_state", if_id=task.if_id, state="cancelled")
        active.pop(future, None)


def run_delay_if_tasks(
    tasks: List[DelayIfSolveInput],
    parallel_workers: int = 0,
    progress_callback: ProgressCallback = None,
) -> Dict[int, DelayIfSolveResult]:
    """Run IF tasks inline or in a bounded spawn-based process pool."""

    worker_count = effective_worker_count(len(tasks), parallel_workers)
    if worker_count == 0:
        return {}

    pending = deque(tasks)
    results: Dict[int, DelayIfSolveResult] = {}
    if worker_count == 1:
        while pending:
            task = pending.popleft()
            emit_progress(progress_callback, "if_state", if_id=task.if_id, state="running")
            try:
                results[task.if_id] = solve_delay_if(task)
            except BaseException as exc:
                emit_progress(progress_callback, "if_state", if_id=task.if_id, state="failed", message=str(exc))
                _cancel_remaining(pending, {}, progress_callback)
                raise DelayIfSolveError(task.if_id, exc) from exc
            emit_progress(progress_callback, "if_state", if_id=task.if_id, state="complete")
        return results

    spawn_context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=worker_count, mp_context=spawn_context) as executor:
        active: Dict[Any, DelayIfSolveInput] = {}

        def submit_available() -> None:
            while pending and len(active) < worker_count:
                task = pending.popleft()
                future = executor.submit(solve_delay_if, task)
                active[future] = task
                emit_progress(progress_callback, "if_state", if_id=task.if_id, state="running")

        submit_available()
        while active:
            completed, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in completed:
                task = active.pop(future)
                try:
                    result = future.result()
                except BaseException as exc:
                    emit_progress(
                        progress_callback,
                        "if_state",
                        if_id=task.if_id,
                        state="failed",
                        message=str(exc),
                    )
                    _cancel_remaining(pending, active, progress_callback)
                    raise DelayIfSolveError(task.if_id, exc) from exc
                results[result.if_id] = result
                emit_progress(progress_callback, "if_state", if_id=result.if_id, state="complete")
            submit_available()
    return results
