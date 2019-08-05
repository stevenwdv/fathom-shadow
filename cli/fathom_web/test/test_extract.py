from ..commands.extract import BASE64_DATA_PATTERN


def test_common_example():
    """Confirm we handle to well behaving case"""
    mime_type = 'image/png'
    base64_string = 'aorienstar/tar/ararnsoine98daQAAAIST+++/rstienf='
    test_string = f'data:{mime_type};base64,{base64_string}'
    matches = list(BASE64_DATA_PATTERN.finditer(test_string))
    assert len(matches) == 1
    assert matches[0].group('mime') == mime_type
    assert matches[0].group('string') == base64_string


def test_empty_string():
    """Some base64 strings are actually empty"""
    test_string = 'data:;base64,'
    matches = list(BASE64_DATA_PATTERN.finditer(test_string))
    assert len(matches) == 0


def test_presence_of_charset():
    """Some base64 strings contain a character set specification"""
    test_string = 'data:image/png; charset=utf-8;base64,iVBORw0K'
    matches = list(BASE64_DATA_PATTERN.finditer(test_string))
    assert len(matches) == 1


def test_string_with_multiple_base64_strings():
    test_string = 'data:image/png;base64,rsoitenaofi2345wf/+ste data:image/png;base64,arsti390/'
    matches = list(BASE64_DATA_PATTERN.finditer(test_string))
    assert len(matches) == 2
