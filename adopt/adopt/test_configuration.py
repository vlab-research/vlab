import numpy as np
import pandas as pd

from .configuration import read_share_lookup


def test_read_share_lookup_works_with_one_variable():

    config_file = "test/targeting_distribution_test_sheet.xlsx"

    share_lookup = read_share_lookup(
        config_file, ["location"], "targeting_distribution_single"
    )

    expect = pd.DataFrame(
        [
            ("West", 0.6),
            ("East", 0.4),
        ],
        columns=["location", "percentage"],
    )

    assert expect.equals(share_lookup)


def test_read_share_lookup_works_with_two_variables():

    config_file = "test/targeting_distribution_test_sheet.xlsx"

    share_lookup = read_share_lookup(
        config_file, ["location", "gender"], "targeting_distribution_double"
    )

    expect = pd.DataFrame(
        [
            ("West", "1", 0.3),
            ("East", "1", 0.2),
            ("West", "2", 0.1),
            ("East", "2", 0.4),
        ],
        columns=["location", "gender", "percentage"],
    )

    assert expect.equals(share_lookup)


def test_read_share_lookup_works_with_three_variables():
    config_file = "test/targeting_distribution_test_sheet.xlsx"

    share_lookup = read_share_lookup(
        config_file, ["location", "gender", "age"], "targeting_distribution_triple"
    )

    expect = pd.DataFrame(
        [
            ("West", "1", "18", 0.12),
            ("East", "1", "18", 0.08),
            ("West", "2", "18", 0.04),
            ("East", "2", "18", 0.16),
            ("West", "1", "40", 0.18),
            ("East", "1", "40", 0.12),
            ("West", "2", "40", 0.06),
            ("East", "2", "40", 0.24),
        ],
        columns=["location", "gender", "age", "percentage"],
    )

    assert expect[["location", "gender", "age"]].equals(
        share_lookup[["location", "gender", "age"]]
    )
    assert np.allclose(share_lookup.percentage.values, expect.percentage.values)


def test_read_share_lookup_works_with_four_variables():
    config_file = "test/targeting_distribution_test_sheet.xlsx"

    share_lookup = read_share_lookup(
        config_file, ["location", "gender", "age", "education"], "targeting_distribution_four"
    )

    expect = pd.DataFrame(
        [
            ("West", "1", "18", "a", 0.12),
            ("East", "1", "18", "a", 0.08),
            ("West", "2", "18", "a", 0.04),
            ("East", "2", "18", "a", 0.16),
            ("West", "1", "40", "a", 0.18),
            ("East", "1", "40", "a", 0.12),
            ("West", "2", "40", "a", 0.06),
            ("East", "2", "40", "a", 0.24),
            ("West", "1", "18", "b", 0.12),
            ("East", "1", "18", "b", 0.08),
            ("West", "2", "18", "b", 0.04),
            ("East", "2", "18", "b", 0.16),
            ("West", "1", "40", "b", 0.18),
            ("East", "1", "40", "b", 0.12),
            ("West", "2", "40", "b", 0.06),
            ("East", "2", "40", "b", 0.24),
        ],
        columns=["location", "gender", "age", "education", "percentage"],
    )

    assert expect[["location", "gender", "age"]].equals(
        share_lookup[["location", "gender", "age"]]
    )
    assert np.allclose(share_lookup.percentage.values, expect.percentage.values)


def test_read_share_lookup_works_with_four_variables_and_one_location():
    config_file = "test/targeting_distribution_test_sheet.xlsx"

    share_lookup = read_share_lookup(
        config_file, ["location", "gender", "age", "education"], "targeting_distribution_four_1"
    )

    expect = pd.DataFrame(
        [
            ("West", "1", "18", "a", 0.12),
            ("West", "2", "18", "a", 0.04),
            ("West", "1", "40", "a", 0.18),
            ("West", "2", "40", "a", 0.06),
            ("West", "1", "18", "b", 0.12),
            ("West", "2", "18", "b", 0.04),
            ("West", "1", "40", "b", 0.18),
            ("West", "2", "40", "b", 0.06),
        ],
        columns=["location", "gender", "age", "education", "percentage"],
    )

    assert expect[["location", "gender", "age"]].equals(
        share_lookup[["location", "gender", "age"]]
    )
    assert np.allclose(share_lookup.percentage.values, expect.percentage.values)
