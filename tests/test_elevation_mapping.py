import unittest
import os
from types import SimpleNamespace

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-mv-tests")

import numpy as np
import pandas as pd

from plugin.core.mv.Antenna import Antenna
from plugin.core.mv.elevation_mapping import (
    COSECANT_ELEVATION_MAPPING,
    LINEAR_ELEVATION_MAPPING,
    mapped_elevation_offset,
    normalize_elevation_mapping,
)
from plugin.core.mv.solver_config import apply_solver_defaults, solver_kwargs


class ElevationMappingTest(unittest.TestCase):
    def test_linear_mapping_is_degree_difference(self):
        source_alt = np.array([31.0, 45.0])
        primary_alt = np.array([30.0, 42.5])

        result = mapped_elevation_offset(source_alt, primary_alt, LINEAR_ELEVATION_MAPPING)

        np.testing.assert_allclose(result, np.array([1.0, 2.5]))

    def test_cosecant_mapping_is_raw_slant_mapping_difference(self):
        source_alt = np.array([31.0, 45.0])
        primary_alt = np.array([30.0, 42.5])
        expected = (
            1.0 / np.sin(np.deg2rad(source_alt))
            - 1.0 / np.sin(np.deg2rad(primary_alt))
        )

        result = mapped_elevation_offset(source_alt, primary_alt, COSECANT_ELEVATION_MAPPING)

        np.testing.assert_allclose(result, expected)

    def test_invalid_mapping_falls_back_to_linear(self):
        self.assertEqual(normalize_elevation_mapping("not-a-mapping"), LINEAR_ELEVATION_MAPPING)
        self.assertEqual(normalize_elevation_mapping(None), LINEAR_ELEVATION_MAPPING)

        result = mapped_elevation_offset([12.0], [10.0], "not-a-mapping")

        np.testing.assert_allclose(result, np.array([2.0]))

    def test_solver_config_normalizes_mapping_for_gui_and_solver(self):
        config = {"elevation_mapping": "bad-value"}

        apply_solver_defaults(config)
        kwargs = solver_kwargs(config)

        self.assertEqual(config["elevation_mapping"], LINEAR_ELEVATION_MAPPING)
        self.assertEqual(kwargs["elevation_mapping"], LINEAR_ELEVATION_MAPPING)
        self.assertEqual(kwargs["separation_noise"], 0.0)

    def test_effective_delay_variance_uses_separation_noise(self):
        weight = np.array([4.0, 1.0])
        theta = np.array([3.0, 5.0])
        unit_weight_variance = 2.0

        no_sep = Antenna.effective_delay_variance(unit_weight_variance, weight, theta, 0.0)
        with_sep = Antenna.effective_delay_variance(unit_weight_variance, weight, theta, 0.1)

        np.testing.assert_allclose(no_sep, unit_weight_variance / weight)
        np.testing.assert_allclose(
            with_sep,
            unit_weight_variance * (1.0 / weight + (0.1 * theta) ** 2),
        )
        with self.assertRaises(ValueError):
            Antenna.effective_delay_variance(unit_weight_variance, weight, theta, -0.1)

    def test_theta_deg_uses_linear_offsets_when_mapping_is_cosecant(self):
        calibrator = SimpleNamespace(id=1, dx=0.0, dy=0.0)
        antenna = Antenna(1, "TEST", data=pd.DataFrame(), calibrators=[calibrator], no_if=1)

        def fake_offsets(_source, times, elevation_mapping=None):
            if elevation_mapping == COSECANT_ELEVATION_MAPPING:
                return np.column_stack([np.full(len(times), 99.0), np.full(len(times), 4.0)])
            return np.column_stack([np.full(len(times), 3.0), np.full(len(times), 4.0)])

        antenna.source_altaz_offsets = fake_offsets
        data = pd.DataFrame({"calsour": [1, 1], "t": [0.0, 1.0]})

        mapped = antenna.add_altaz_offsets(data, COSECANT_ELEVATION_MAPPING)

        np.testing.assert_allclose(mapped["delta_el"].to_numpy(), np.array([99.0, 99.0]))
        np.testing.assert_allclose(mapped["delta_az"].to_numpy(), np.array([4.0, 4.0]))
        np.testing.assert_allclose(mapped["theta_deg"].to_numpy(), np.array([5.0, 5.0]))

    def test_target_correction_uses_current_mapping(self):
        antenna = Antenna(1, "TEST", data=pd.DataFrame(), calibrators=[], no_if=1)
        antenna.target = {"RA": 0.0, "DEC": 0.0}
        antenna.elevation_mapping = COSECANT_ELEVATION_MAPPING
        antenna.delay_mv_result = {0: np.array([[2.0, 3.0, 0.0, 0.0]])}
        antenna.delay_mv_t_by_if = {0: np.array([0.0])}
        calls = []

        def fake_offsets(_source, _times, elevation_mapping=None):
            calls.append(elevation_mapping)
            return np.array([[5.0, 7.0]])

        antenna.source_altaz_offsets = fake_offsets

        antenna._refresh_delay_target_series()

        self.assertEqual(calls, [COSECANT_ELEVATION_MAPPING])
        np.testing.assert_allclose(antenna.delay_target_if[0], np.array([31.0]))
        np.testing.assert_allclose(antenna.delay_average, np.array([31.0]))


if __name__ == "__main__":
    unittest.main()
