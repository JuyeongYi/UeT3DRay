from t3dgraph.core.t3d.values import Scalar, QuotedString, Struct, ArrayLiteral, parse_value
from t3dgraph.core.t3d.serializer import serialize_value


def test_scalar_round_trip():
    src = '42'
    assert serialize_value(parse_value(src)) == src


def test_quoted_string():
    src = '"hello"'
    assert serialize_value(parse_value(src)) == src


def test_struct():
    src = '(X=1,Y=2,Z=3)'
    assert serialize_value(parse_value(src)) == src


def test_nested_struct():
    src = '(A=(X=1,Y=2),B=10)'
    assert serialize_value(parse_value(src)) == src


def test_array():
    src = '(1,2,3)'
    assert serialize_value(parse_value(src)) == src
