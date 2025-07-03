import pytest

from pycodetags import DATA


def assert_repr_eval_roundtrip(obj, globals_dict=None):
    # You can pass globals_dict if eval needs help finding the class
    if globals_dict is None:
        globals_dict = globals()
    obj_repr = repr(obj)
    obj_repr = obj_repr.replace("data_meta=...", "")

    reconstructed = eval(obj_repr, globals_dict)

    assert reconstructed == obj, f"Repr/eval mismatch: {str(obj)} != {reconstructed}"


@pytest.mark.parametrize(
    "obj",
    [
        DATA(
            code_tag="TODO",
            comment="Make donuts",
            custom_fields={"fruit": "banana"},
            default_fields={"user": "mdm"},
        ),
        DATA(
            code_tag="TODO",
            comment="Make more donuts",
            custom_fields={},
            default_fields={},
        ),
        DATA(
            code_tag="TODO",
            comment="Make more donuts",
            custom_fields=None,
            default_fields=None,
        ),
    ],
)
def test_repr_eval_roundtrip(obj):
    assert_repr_eval_roundtrip(obj, globals_dict=globals())
