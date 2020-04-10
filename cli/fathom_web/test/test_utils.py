from ..utils import fit_unicode


def test_fit_unicode():
    assert fit_unicode('abc', 3) == 'abc'
    assert fit_unicode('abc', 2) == 'ab'
    assert fit_unicode('a母', 2) == 'a '
    assert fit_unicode('a母', 3) == 'a母'
    assert fit_unicode('a母母母s', 7) == 'a母母母'
    assert fit_unicode('a母母母s', 6) == 'a母母 '
    assert fit_unicode('a母母母s', 5) == 'a母母'
    assert fit_unicode('a母母', 4) == 'a母 '
    assert fit_unicode('a母', 6) == 'a母   '
