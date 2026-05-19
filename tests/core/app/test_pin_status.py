from t3dgraph.core.base.graph_model import Pin
from t3dgraph.core.app.pin_status import is_changed_from_default


def _pin(cpp, dv):
    return Pin(name="P", cpp_type=cpp, direction="Input", default_value=dv)


def test_none_default_not_changed():
    assert is_changed_from_default(_pin("double", None)) is False


def test_bool_false_not_changed():
    assert is_changed_from_default(_pin("bool", "False")) is False
    assert is_changed_from_default(_pin("bool", "false")) is False


def test_bool_true_changed():
    assert is_changed_from_default(_pin("bool", "True")) is True


def test_numeric_zero_not_changed():
    assert is_changed_from_default(_pin("double", "0.000000")) is False
    assert is_changed_from_default(_pin("int32", "0")) is False


def test_numeric_nonzero_changed():
    assert is_changed_from_default(_pin("double", "1.000000")) is True


def test_fname_none_not_changed():
    assert is_changed_from_default(_pin("FName", "None")) is False


def test_fname_value_changed():
    assert is_changed_from_default(_pin("FName", "IKTarget")) is True


def test_empty_struct_not_changed():
    assert is_changed_from_default(_pin("FVector", "()")) is False


def test_struct_with_value_changed():
    assert is_changed_from_default(_pin("FQuat", "(X=0.0,W=1.0)")) is True


def test_zero_struct_not_changed():
    assert is_changed_from_default(
        _pin("FVector", "(X=0.000000,Y=0.000000,Z=0.000000)")) is False


def test_nonzero_struct_changed():
    assert is_changed_from_default(
        _pin("FVector", "(X=1.000000,Y=0.000000,Z=0.000000)")) is True


def test_nested_zero_struct_not_changed():
    assert is_changed_from_default(
        _pin("FTransform", "(Rotation=(X=0,Y=0,Z=0),Translation=(X=0,Y=0,Z=0))")) is False
