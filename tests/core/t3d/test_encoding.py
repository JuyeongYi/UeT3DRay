from t3dgraph.core.t3d.encoding import read_t3d_text


def test_plain_utf8(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("Begin Object", encoding="utf-8")
    assert read_t3d_text(f) == "Begin Object"


def test_utf8_bom(tmp_path):
    f = tmp_path / "b.txt"
    f.write_bytes(b"\xef\xbb\xbf" + "Begin Object".encode("utf-8"))
    assert read_t3d_text(f) == "Begin Object"


def test_utf16(tmp_path):
    f = tmp_path / "c.txt"
    f.write_bytes("Begin Object".encode("utf-16"))
    assert read_t3d_text(f) == "Begin Object"
