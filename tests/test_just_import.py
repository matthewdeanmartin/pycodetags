import pycodetags.__about__
import pycodetags.logging_config


def test_imports():
    assert dir(pycodetags.__about__)
    assert dir(pycodetags.logging_config)
