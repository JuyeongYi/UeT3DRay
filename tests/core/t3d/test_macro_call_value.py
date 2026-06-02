"""x2 — _scalar paren-balanced for UE macro-call values."""
from pathlib import Path
import pytest
from t3dgraph.core.t3d.values import parse_value, Struct, Scalar, ArrayLiteral
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.objects import parse_objects


def test_nsloctext_macro_in_struct_value() -> None:
    """Category=NSLOCTEXT(...) 가 한 scalar로 흡수."""
    text = '(VarName="X",Category=NSLOCTEXT("KismetSchema", "Default", "Default"),Flags=1)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    keys = [k for k, _ in v.items]
    assert keys == ["VarName", "Category", "Flags"]
    category = next(val for k, val in v.items if k == "Category")
    assert isinstance(category, Scalar)
    assert "NSLOCTEXT" in category.text
    assert '"KismetSchema"' in category.text
    assert category.text.endswith(")")


def test_nested_macro_call() -> None:
    """nested paren도 정확히 balance."""
    text = '(X=A(B(C),D(E,F)),Y=2)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    x_val = next(val for k, val in v.items if k == "X")
    assert isinstance(x_val, Scalar)
    assert x_val.text == "A(B(C),D(E,F))"


def test_quote_inside_paren_protects_comma() -> None:
    """따옴표 안 `,`·`(` 가 paren depth/comma 종료 영향 안 줌."""
    text = '(Cat=FN("a,b","c)d"),Z=1)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    cat = next(val for k, val in v.items if k == "Cat")
    assert isinstance(cat, Scalar)
    assert cat.text == 'FN("a,b","c)d")'


def test_plain_scalar_no_regression() -> None:
    """paren 없는 일반 scalar는 동작 동일."""
    text = '(A=hello,B=42)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    a = next(val for k, val in v.items if k == "A")
    b = next(val for k, val in v.items if k == "B")
    assert isinstance(a, Scalar) and a.text == "hello"
    assert isinstance(b, Scalar) and b.text == "42"


def test_array_of_macro_scalars() -> None:
    """array element가 매크로 호출형."""
    text = '(NSLOCTEXT("a","b","c"),NSLOCTEXT("d","e","f"))'
    v = parse_value(text)
    assert isinstance(v, ArrayLiteral)
    assert len(v.items) == 2
    assert all(isinstance(item, Scalar) for item in v.items)


def test_spaced_scalar_with_guid_still_works() -> None:
    """기존 `RigUnit_X SP GUID` 공백 scalar 회귀 없음.
    UE trailing-comma 배열 `(X,)` → 첫 번째 원소에 내용이 있어야 한다."""
    text = '(LinkedTo=(RigUnit_X 2466091D48C71EBA1D2EF4BB6AEED3DD,))'
    v = parse_value(text)
    assert isinstance(v, Struct)
    linked = next(val for k, val in v.items if k == "LinkedTo")
    assert isinstance(linked, ArrayLiteral)
    # trailing-comma 배열은 빈 후미 원소 포함 가능 — 첫 원소만 검증
    assert len(linked.items) >= 1
    elem = linked.items[0]
    assert isinstance(elem, Scalar)
    assert "RigUnit_X" in elem.text and "2466091D" in elem.text


def test_new_variables_full_line_struct() -> None:
    """397283 형 실제 line 통과."""
    text = (
        '(VarName="L_mouth_suck_blow_offset",'
        'VarGuid=D03976AB34474BBB0B2807CD14D7A95,'
        'VarType=(PinCategory="real",PinSubCategory="double",bSerializeAsSinglePrecisionFloat=True),'
        'FriendlyName="L Mouth Suck Blow Offset",'
        'Category=NSLOCTEXT("KismetSchema", "Default", "Default"),'
        'PropertyFlags=65541,'
        'MetaDataArray=((DataKey="MultiLine",DataValue="true")))'
    )
    v = parse_value(text)
    assert isinstance(v, Struct)
    keys = [k for k, _ in v.items]
    assert "VarName" in keys
    assert "Category" in keys
    assert "MetaDataArray" in keys


@pytest.mark.skipif(
    not Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").exists(),
    reason="repro file 미존재 환경",
)
def test_simple_face_ctrlrig_full_parse() -> None:
    """전체 파일이 폭발 없이 parse_document 통과."""
    raw = Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").read_text(
        encoding="utf-16",
    )
    doc = parse_document(raw)
    assert doc is not None
