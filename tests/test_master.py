from payequity.config import load_settings
from payequity.generators.master import build_master
from payequity.rng import RngFactory


def test_master_has_expected_reference_shapes():
    settings = load_settings("starter", seed=20261022)
    master = build_master(settings, RngFactory(settings.seed))
    assert len(master["role_level"]) == 200
    assert len(master["location"]) == 10
    assert (master["compensation_band"]["band_min"] < master["compensation_band"]["band_mid"]).all()
    assert (master["compensation_band"]["band_mid"] < master["compensation_band"]["band_max"]).all()


def test_fx_generation_is_deterministic():
    settings = load_settings("starter", seed=20261022)
    first = build_master(settings, RngFactory(settings.seed))["fx_rate"]
    second = build_master(settings, RngFactory(settings.seed))["fx_rate"]
    assert first.to_csv(index=False) == second.to_csv(index=False)
