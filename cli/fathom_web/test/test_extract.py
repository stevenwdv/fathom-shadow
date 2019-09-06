from ..commands.extract import BASE64_DATA_PATTERN, decode


def test_common_example():
    """Confirm we handle the well-behaving case"""
    mime_type = 'image/png'
    base64_string = 'aorienstar/tar/ararnsoine98daQAAAIST+++/rstienf='
    test_string = f'data:{mime_type};base64,{base64_string}'
    matches = get_base64_regex_matches(test_string)
    assert len(matches) == 1
    assert matches[0].group('mime') == mime_type
    assert matches[0].group('string') == base64_string


def get_base64_regex_matches(from_string):
    """Helper method to get the list of matches from the given string.

    We need to use finditer() here because it returns Match objects while
    findall() does not, and we use Match objects in fathom-extract.
    """
    return list(BASE64_DATA_PATTERN.finditer(from_string))


def test_empty_string():
    """Some base64 strings are actually empty"""
    test_string = 'data:;base64,'
    matches = get_base64_regex_matches(test_string)
    assert len(matches) == 0


def test_presence_of_charset():
    """Some base64 strings contain a character set specification"""
    test_string = 'data:image/png; charset=utf-8;base64,iVBORw0K'
    matches = get_base64_regex_matches(test_string)
    assert len(matches) == 1


def test_string_with_multiple_base64_strings():
    test_string = 'data:image/png;base64,rsoitenaofi2345wf/+ste data:image/png;base64,arsti390/'
    matches = get_base64_regex_matches(test_string)
    assert len(matches) == 2


def test_string_with_percent_encoded_equals_signs_is_found():
    """Some base64 strings have their padding characters (=) percent
    encoded so they appear as %3D. Our regex should capture them.
    """
    base64_string = 'R0lGODlhAQABAID/AMDAwAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw%3D%3D'
    test_string = f'url(&quot;data:image/gif;base64,{base64_string}&quot;)'
    matches = get_base64_regex_matches(test_string)
    assert len(matches) == 1
    assert matches[0].group('string') == base64_string


def test_string_with_percent_encoded_equals_signs_is_decoded():
    """Some base64 strings have their padding characters (=) percent
    encoded so they appear as %3D. We should be able to decode them.

    At the moment, we will trust the decoding is correct, we just want
    to make sure no errors are raised.
    """
    base64_string = 'R0lGODlhAQABAID/AMDAwAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw%3D%3D'
    decode(base64_string)


def test_unpadded_string_is_decoded():
    """Some base64 strings do not have padding characters. Python's
    base64.b64decode() expects the string to be padded to a number of
    characters that is a multiple of four.

    At the moment, we will trust the decoding is correct, we just want
    to make sure no errors are raised.
    """
    base64_string = 'R0lGODlhAQABAIAAAAUEBAAAACwAAAAAAQABAAACAkQBADs'
    decode(base64_string)
