import datetime

from pycodetags.data_tags_classes import Serializable


class Sample(Serializable):
    def __init__(self):
        self.a = 1
        self._b = 2
        self.dt = datetime.datetime(2020, 1, 1, 12, 0)


def test_serializable_to_dict(tmp_path):
    s = Sample()
    d = s.to_dict()
    assert d["a"] == 1
    assert "dt" in d and isinstance(d["dt"], str)
    assert "_b" not in d
