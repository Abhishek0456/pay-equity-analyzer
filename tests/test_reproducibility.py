from payequity.pipeline import generate
from payequity.reproducibility import checksums, verify_reproducible


def test_same_seed_is_reproducible():
    assert verify_reproducible(generate, "starter", 20261022)


def test_different_seed_changes_output():
    assert checksums(generate("starter", 20261022)) != checksums(generate("starter", 20261023))
