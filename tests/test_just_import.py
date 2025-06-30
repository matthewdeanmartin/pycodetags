import pycodetags.__about__
import pycodetags.logging_config
from pycodetags.data_schema import PureDataSchema


def test_imports():
    assert dir(pycodetags.__about__)
    assert dir(pycodetags.logging_config)
    assert dir(PureDataSchema)
