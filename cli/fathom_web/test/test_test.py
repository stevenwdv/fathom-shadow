from click import BadParameter
from pytest import raises

from ..commands.test import decode_weights


def test_expected_input_format():
    """Test that an example of good input decodes as expected"""
    json_string = '{"coeffs": [["rule1", 0.1], ["rule2", 0.2]], "bias": 0.5}'
    expected_dict = {
        'coeffs': [
            ['rule1', 0.1],
            ['rule2', 0.2],
        ],
        'bias': 0.5,
    }
    decoded_weights = decode_weights(None, None, json_string)
    assert decoded_weights == expected_dict


def test_not_json():
    run_invalid_json('not_json', r'.*valid.*')


def run_invalid_json(json_string, assertion_match_regex):
    """Helper method to run `decode_weights()` with invalid input"""
    with raises(BadParameter, match=assertion_match_regex):
        decode_weights(None, None, json_string)


def test_no_coeffs():
    run_invalid_json('{"bias": 0.5}', r'.*contain.*coeffs.*')


def test_no_bias():
    run_invalid_json('{"coeffs": [["rule", 0.5]]}', r'.*contain.*bias.*')


def test_coeffs_not_list():
    run_invalid_json('{"coeffs": {"not": "a_list"}, "bias": 0.5}', r'Coeffs must be a list of 2-element lists.*')


def test_coeffs_not_pairs():
    run_invalid_json(
        '{"coeffs": [["rule1"], ["rule2", 0.2]], "bias": 0.5}',
        r'Coeffs must be a list of 2-element lists.*'
    )


def test_rulename_not_string():
    run_invalid_json(
        '{"coeffs": [[0.2, 0.2], ["rule2", 0.2]], "bias": 0.5}',
        r'Coeffs must be a list of 2-element lists.*'
    )


def test_coeff_value_not_float():
    run_invalid_json(
        '{"coeffs": [["rule1", "rule1"], ["rule2", 0.2]], "bias": 0.5}',
        r'Coeffs must be a list of 2-element lists.*'
    )
