from scikms.server import dslv1
from scikms.server import Request


def test_request():
    req = Request(cmd='play', cmd_args=['fuo://x'])
    assert 'play fuo://x' in dslv1.unparse(req)
