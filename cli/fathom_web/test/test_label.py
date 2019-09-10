from ..commands.label import label_html_tags_in_html_string


IN_TYPE = 'test'


def test_opening_html_tag_has_no_attributes():
    """Some HTML tags may not have any attributes"""
    input_string = '<html>'
    expected_string = f'<html data-fathom="{IN_TYPE}">'
    assert label_html_tags_in_html_string(input_string, IN_TYPE) == expected_string


def test_opening_html_tag_has_attributes():
    """Most HTML tags have at least one attribute"""
    input_string = '<html lang="en-us">'
    expected_string = f'<html data-fathom="{IN_TYPE}" lang="en-us">'
    assert label_html_tags_in_html_string(input_string, IN_TYPE) == expected_string


def test_html_string_has_multiple_opening_html_tags():
    """Some HTML tags may have multiple HTML tags"""
    input_string = '<html><div></div><html>'
    expected_string = f'<html data-fathom="{IN_TYPE}"><div></div><html data-fathom="{IN_TYPE}">'
    assert label_html_tags_in_html_string(input_string, IN_TYPE) == expected_string


def test_html_string_has_right_angle_bracket_as_attribute_value():
    """Some HTML tags may contain a right angle bracket in an unexpected location."""
    input_string = '<html data-bracket=">" class="foo">'
    expected_string = f'<html data-fathom="{IN_TYPE}" data-bracket=">" class="foo">'
    assert label_html_tags_in_html_string(input_string, IN_TYPE) == expected_string


def test_html_string_is_multiline():
    """Some HTML tags may span multiple lines"""
    input_string ='<html\n' + \
                'class="foo"\n' + \
                'id="bar"\n' + \
                '>'
    expected_string = f'<html data-fathom="{IN_TYPE}"\n' + \
                'class="foo"\n' + \
                'id="bar"\n' + \
                '>'
    assert label_html_tags_in_html_string(input_string, IN_TYPE) == expected_string


def test_html_string_has_extra_spaces():
    """
    Some HTML tags may have extra spaces inside the HTML tag. Note that having a space
    between the '<' and the tag name (e.g. 'html') is not valid HTML.
    """
    input_string ='<html   >'
    expected_string = f'<html data-fathom="{IN_TYPE}"   >'
    assert label_html_tags_in_html_string(input_string, IN_TYPE) == expected_string


def test_html_string_has_comments():
    """
    Some HTML tags may have HTML comments throughout. Note that comments cannot
    occur within a tag.
    """
    input_string = '<!-- this is a comment --><html lang="en">\n' + \
    '<!-- this is another comment --></html><!-- this is yet another comment -->'
    expected_string = f'<!-- this is a comment --><html data-fathom="{IN_TYPE}" lang="en">\n' + \
    '<!-- this is another comment --></html><!-- this is yet another comment -->'
    assert label_html_tags_in_html_string(input_string, IN_TYPE) == expected_string
