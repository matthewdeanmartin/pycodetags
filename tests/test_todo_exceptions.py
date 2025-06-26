from pycodetags import TodoException


def test_serialization():
    ex = TodoException("It is what it is", "me", "2053-12-12")
    serialization = ex.to_dict()
    for value in ("It is what it is", "me", "2053-12-12"):
        assert value in serialization.values()
