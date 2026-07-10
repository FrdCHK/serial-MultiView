import unittest
import os

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
