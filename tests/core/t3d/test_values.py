from t3dgraph.core.t3d.values import parse_value, Scalar, QuotedString, Struct, ArrayLiteral


def test_scalar():
    assert parse_value("Output") == Scalar("Output")


def test_quoted_string():
    assert parse_value('"hello world"') == QuotedString("hello world")


def test_struct():
    v = parse_value("(X=1.0,Y=2.0)")
    assert v == Struct([("X", Scalar("1.0")), ("Y", Scalar("2.0"))])


def test_nested_struct():
    v = parse_value("(A=(X=0),B=1)")
    assert v == Struct([("A", Struct([("X", Scalar("0"))])), ("B", Scalar("1"))])


def test_empty_paren_is_empty_struct():
    assert parse_value("()") == Struct([])


def test_array_literal():
    assert parse_value("(1,2,3)") == ArrayLiteral([Scalar("1"), Scalar("2"), Scalar("3")])


def test_quoted_string_with_comma_and_parens():
    v = parse_value('"/Script/X.Y\'/Game/A.B:C\'"')
    assert isinstance(v, QuotedString)
    assert v.text == "/Script/X.Y'/Game/A.B:C'"


def test_struct_value_can_be_quoted():
    v = parse_value('(Name="a,b",Count=2)')
    assert v == Struct([("Name", QuotedString("a,b")), ("Count", Scalar("2"))])
