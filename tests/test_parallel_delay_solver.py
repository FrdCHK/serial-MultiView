import copy
from dataclasses import replace
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-mv-tests")

import numpy as np
import pandas as pd
import tkinter as tk
import yaml

from gen_control_file import render_control
from core.solver_config_compat import migrate_legacy_solver_config
from plugin.core.mv.Antenna import Antenna
from plugin.core.mv.ConfigWindow import ConfigWindow
from plugin.core.mv.ProgressWindow import ProgressState
from plugin.core.mv.RootWindow import RootWindow
from plugin.core.mv.delay_parallel import (
    DelayIfSolveError,
    DelayIfSolveResult,
    effective_worker_count,
    validate_parallel_workers,
)
from plugin.core.mv.solver_config import (
    apply_solver_defaults,
    solver_kwargs,
)


def _synthetic_antenna(no_if=3, n_obs=36):
    times = np.arange(n_obs, dtype=float) / 1000.0
    source_ids = np.array([101, 102, 103], dtype=int)
    source_id = source_ids[np.arange(n_obs) % source_ids.size]
    positions = {
        101: np.array([1.0, 0.0]),
        102: np.array([0.0, 1.0]),
        103: np.array([1.0, 1.0]),
    }
    delta_el = np.array([positions[int(src)][0] for src in source_id])
    delta_az = np.array([positions[int(src)][1] for src in source_id])
    gradient_el = 2.0e-10 + 1.5e-11 * np.sin(np.arange(n_obs) / 9.0)
    gradient_az = -1.2e-10 + 1.0e-11 * np.cos(np.arange(n_obs) / 8.0)
    clean_delay = delta_el * gradient_el + delta_az * gradient_az

    data = pd.DataFrame({
        "calsour": source_id,
        "x": delta_el,
        "y": delta_az,
        "t": times,
        "weight": np.linspace(0.8, 1.2, n_obs),
    })
    if_freq = []
    for if_id in range(no_if):
        freq_ghz = 1.0 + 0.2 * if_id
        if_freq.append(freq_ghz)
        delay = clean_delay + (if_id + 1) * 2.0e-13 * np.sin(np.arange(n_obs) * 1.3)
        scale = freq_ghz * 2.0e9 * np.pi
        data[f"d{if_id}"] = delay
        data[f"p{if_id}"] = (-delay * scale + np.pi) % (2 * np.pi) - np.pi

    calibrators = [
        SimpleNamespace(id=source, dx=positions[source][0], dy=positions[source][1])
        for source in source_ids
    ]
    antenna = Antenna(
        2,
        "TEST",
        data=data,
        calibrators=calibrators,
        if_freq=if_freq,
        no_if=no_if,
        target={"RA": 0.0, "DEC": 0.0},
    )

    def fake_offsets(source, requested_times, elevation_mapping=None):
        if isinstance(source, dict):
            position = np.array([0.4, -0.2])
        else:
            position = positions[int(source.id)]
        return np.tile(position, (len(requested_times), 1))

    antenna.source_altaz_offsets = fake_offsets
    return antenna


def _solver_kwargs(parallel_workers):
    return {
        "kalman_factor": 1.0e-18,
        "unit_weight_variance": 6.4e-25,
        "rts_smoothing": True,
        "viterbi_integer_states": 1,
        "viterbi_max_jump": 1,
        "viterbi_jump_penalty": 16.0,
        "viterbi_robust": True,
        "viterbi_huber_c": 3.0,
        "viterbi_z_out": 8.0,
        "viterbi_max_outlier_iterations": 1,
        "viterbi_fix_initial_integer": 0,
        "viterbi_p0_gradient": 1.0e-18,
        "elevation_mapping": "linear",
        "separation_noise": 0.0,
        "parallel_workers": parallel_workers,
    }


class ParallelDelaySolverTest(unittest.TestCase):
    def test_parallel_matches_inline_and_keeps_manual_if_edits_separate(self):
        antenna = _synthetic_antenna()
        antenna.delay_adjust_info.loc[0, "flag0"] = 1
        antenna.delay_adjust_info.loc[1, "flag1"] = 1
        antenna.delay_adjust_info.loc[2:, "w2"] = 1

        inline_events = []
        antenna.delay_multiview(progress_callback=inline_events.append, **_solver_kwargs(1))
        inline_results = {if_id: value.copy() for if_id, value in antenna.delay_mv_result.items()}
        inline_times = {if_id: value.copy() for if_id, value in antenna.delay_mv_t_by_if.items()}
        inline_fit = copy.deepcopy(antenna.delay_fit_info)
        inline_auto = antenna.delay_auto_adjust_info.copy(deep=True)
        inline_average = antenna.delay_average.copy()

        parallel_events = []
        antenna.delay_multiview(progress_callback=parallel_events.append, **_solver_kwargs(2))

        self.assertEqual(list(antenna.delay_mv_result), [0, 1, 2])
        for if_id in antenna.delay_if_ids:
            np.testing.assert_allclose(antenna.delay_mv_result[if_id], inline_results[if_id])
            np.testing.assert_allclose(antenna.delay_mv_t_by_if[if_id], inline_times[if_id])
            np.testing.assert_array_equal(
                antenna.delay_fit_info[if_id]["integer_path"],
                inline_fit[if_id]["integer_path"],
            )
            np.testing.assert_array_equal(
                antenna.delay_fit_info[if_id]["orig_index"],
                inline_fit[if_id]["orig_index"],
            )
            np.testing.assert_array_equal(
                antenna.delay_fit_info[if_id]["outlier_mask"],
                inline_fit[if_id]["outlier_mask"],
            )
        pd.testing.assert_frame_equal(antenna.delay_auto_adjust_info, inline_auto)
        np.testing.assert_allclose(antenna.delay_average, inline_average)
        self.assertNotIn(0, antenna.delay_fit_info[0]["orig_index"])
        self.assertNotIn(1, antenna.delay_fit_info[1]["orig_index"])
        self.assertIn(0, antenna.delay_fit_info[1]["orig_index"])
        self.assertTrue(any(event.get("state") == "running" for event in parallel_events))
        self.assertEqual(parallel_events[-1]["state"], "complete")

    def test_skipped_if_is_terminal_and_excluded_from_average(self):
        antenna = _synthetic_antenna()
        antenna.delay_adjust_info["flag2"] = 1
        events = []

        antenna.delay_multiview(progress_callback=events.append, **_solver_kwargs(2))

        self.assertEqual(antenna.delay_mv_result[2].shape, (0, 4))
        self.assertNotIn(2, antenna.delay_fit_info)
        self.assertGreater(antenna.delay_average.size, 0)
        self.assertTrue(
            any(
                event.get("type") == "if_state"
                and event.get("if_id") == 2
                and event.get("state") == "skipped"
                for event in events
            )
        )

    def test_single_if_uses_inline_worker_and_all_skipped_commits_empty(self):
        single = _synthetic_antenna(no_if=1)
        single.delay_multiview(**_solver_kwargs(8))
        self.assertEqual(list(single.delay_mv_result), [0])
        self.assertGreater(single.delay_average.size, 0)

        skipped = _synthetic_antenna()
        for if_id in skipped.delay_if_ids:
            skipped.delay_adjust_info[f"flag{if_id}"] = 1
        events = []
        skipped.delay_multiview(progress_callback=events.append, **_solver_kwargs(0))

        self.assertTrue(all(result.shape == (0, 4) for result in skipped.delay_mv_result.values()))
        self.assertEqual(skipped.delay_fit_info, {})
        self.assertEqual(skipped.delay_average.size, 0)
        self.assertTrue((skipped.delay_auto_adjust_info.to_numpy() == 0).all())
        self.assertEqual(
            sum(event.get("state") == "skipped" for event in events),
            len(skipped.delay_if_ids),
        )
        self.assertEqual(events[-1]["state"], "complete")

    def test_failure_preserves_previous_committed_solution(self):
        antenna = _synthetic_antenna()
        antenna.delay_multiview(**_solver_kwargs(1))
        previous_results = {if_id: value.copy() for if_id, value in antenna.delay_mv_result.items()}
        previous_auto = antenna.delay_auto_adjust_info.copy(deep=True)
        previous_average = antenna.delay_average.copy()
        events = []
        prepare_task = antenna._prepare_delay_if_task

        def prepare_invalid_if(*args, **kwargs):
            task = prepare_task(*args, **kwargs)
            if task is not None and task.if_id == 1:
                return replace(task, z_out=-1.0)
            return task

        with patch.object(antenna, "_prepare_delay_if_task", side_effect=prepare_invalid_if):
            with self.assertRaisesRegex(DelayIfSolveError, "IF2 solve failed"):
                antenna.delay_multiview(progress_callback=events.append, **_solver_kwargs(2))

        for if_id in antenna.delay_if_ids:
            np.testing.assert_allclose(antenna.delay_mv_result[if_id], previous_results[if_id])
        pd.testing.assert_frame_equal(antenna.delay_auto_adjust_info, previous_auto)
        np.testing.assert_allclose(antenna.delay_average, previous_average)
        self.assertEqual(events[-1]["state"], "failed")

    def test_shuffled_result_mapping_commits_in_if_order(self):
        antenna = _synthetic_antenna(n_obs=3)
        results = {}
        for if_id in (2, 0, 1):
            results[if_id] = DelayIfSolveResult(
                if_id=if_id,
                state=np.full((3, 4), float(if_id)),
                t=np.arange(3, dtype=float),
                integer_path=np.zeros(3, dtype=int),
                orig_index=np.arange(3, dtype=int),
                outlier_mask=np.zeros(3, dtype=bool),
                standardized_residual=np.zeros(3, dtype=float),
            )

        antenna._commit_delay_solution("linear", results, [])

        self.assertEqual(list(antenna.delay_mv_result), [0, 1, 2])
        np.testing.assert_allclose(antenna.delay_average, np.full(3, 0.2))


class ParallelConfigurationTest(unittest.TestCase):
    def test_worker_count_validation_and_auto_limit(self):
        with patch("plugin.core.mv.delay_parallel.os.cpu_count", return_value=4):
            self.assertEqual(effective_worker_count(7, 0), 4)
            self.assertEqual(effective_worker_count(2, 0), 2)
        self.assertEqual(effective_worker_count(3, 8), 3)
        self.assertEqual(effective_worker_count(3, 1), 1)
        for invalid in (-1, 1.5, "2", True):
            with self.assertRaises(ValueError):
                validate_parallel_workers(invalid)

    def test_config_default_translation_and_entry_validation(self):
        config = {}
        apply_solver_defaults(config)
        self.assertEqual(config["parallel_workers"], 0)
        self.assertEqual(solver_kwargs(config)["parallel_workers"], 0)
        null_config = {
            "parallel_workers": None,
            "integer_states": None,
            "kalman_factor": "null",
            "z_out": "",
        }
        apply_solver_defaults(null_config)
        self.assertEqual(null_config["parallel_workers"], 0)
        self.assertEqual(null_config["integer_states"], 3)
        self.assertEqual(null_config["kalman_factor"], 1.0e-14)
        self.assertEqual(null_config["z_out"], 4.0)
        self.assertEqual(Antenna._parse_integer_states(None), list(range(-3, 4)))
        self.assertEqual(Antenna._parse_integer_states("None"), list(range(-3, 4)))
        window = ConfigWindow.__new__(ConfigWindow)
        self.assertEqual(window._parse_entry("parallel_workers", "3"), 3)
        with self.assertRaises(ValueError):
            window._parse_entry("parallel_workers", "-1")

    def test_legacy_solver_keys_render_as_current_mvrun_parameters(self):
        repo_root = Path(__file__).resolve().parents[1]
        with open(repo_root / "config" / "config.yaml", "r", encoding="utf-8") as stream:
            old_config = yaml.safe_load(stream)
        expected = {
            "integer_states": 1,
            "max_jump": 1,
            "jump_penalty": 50.0,
            "huber_c": 3.0,
            "z_out": 5.0,
        }
        for new_key in expected:
            old_config.pop(new_key, None)
        old_config.update({f"viterbi_{key}": value for key, value in expected.items()})

        templates = (
            "template/manual_smv.yaml.j2",
            "template/vlba_smv.yaml.j2",
            "template/vlba_smv_calsour_struc.yaml.j2",
        )
        for template_path in templates:
            control = yaml.safe_load(render_control(template_path, old_config))
            mvrun_params = next(
                plugin["params"]
                for plugin in control["plugins"]
                if plugin["name"] == "MVRun"
            )
            for key, value in expected.items():
                self.assertEqual(mvrun_params[key], value, f"{template_path}: {key}")
            self.assertFalse(any(key.startswith("viterbi_") for key in control["config"]))

    def test_current_solver_key_wins_over_legacy_alias(self):
        config = {"integer_states": 2, "viterbi_integer_states": 1}
        migrate_legacy_solver_config(config)
        self.assertEqual(config, {"integer_states": 2})

        blank_current = {"integer_states": None, "viterbi_integer_states": 1}
        migrate_legacy_solver_config(blank_current)
        self.assertEqual(blank_current, {"integer_states": 1})


class ParallelProgressStateTest(unittest.TestCase):
    def test_out_of_order_completion_and_terminal_counts(self):
        state = ProgressState([0, 1, 2])
        state.apply_event({"type": "global_state", "state": "solving"})
        state.apply_event({"type": "if_state", "if_id": 2, "state": "complete"})
        self.assertEqual(state.summary(), "Solving IFs in parallel — 1/3 complete")
        state.apply_event({"type": "if_state", "if_id": 0, "state": "skipped"})
        state.apply_event({"type": "if_state", "if_id": 1, "state": "complete"})
        self.assertEqual(state.terminal_count, 3)
        state.apply_event({"type": "global_state", "state": "combining", "message": "Combining IF solutions"})
        self.assertEqual(state.summary(), "Combining IF solutions")
        state.apply_event({"type": "global_state", "state": "complete"})
        self.assertEqual(state.summary(), "Calculation complete — 3/3 complete")

    def test_invalid_progress_event_is_rejected(self):
        state = ProgressState([0])
        with self.assertRaises(ValueError):
            state.apply_event({"type": "if_state", "if_id": 4, "state": "running"})
        with self.assertRaises(ValueError):
            state.apply_event({"type": "global_state", "state": "waiting"})


class RootWindowProgressIntegrationTest(unittest.TestCase):
    def test_modal_tk_loop_runs_spawn_pool_from_coordinator_thread(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display is not available: {exc}")
        root.withdraw()
        try:
            window = RootWindow.__new__(RootWindow)
            window.root = root
            window.antenna = _synthetic_antenna()

            window._run_solver_with_progress(_solver_kwargs(2))

            self.assertEqual(list(window.antenna.delay_mv_result), [0, 1, 2])
            self.assertGreater(window.antenna.delay_average.size, 0)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
