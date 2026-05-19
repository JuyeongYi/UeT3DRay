from t3dgraph.cli import run


def test_cli_summary_on_real_file(orion_dir, capsys):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    exit_code = run([str(f)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "graph type: rigvm" in out
    assert "nodes:" in out
    assert "links:" in out


def test_cli_missing_file_returns_nonzero(capsys):
    exit_code = run(["nonexistent.t3d.txt"])
    assert exit_code != 0
    assert "찾을 수 없" in capsys.readouterr().err


def _sample(orion_dir):
    return (orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
            ).read_text(encoding="utf-8")


def test_cli_handles_utf8_bom(tmp_path, orion_dir):
    f = tmp_path / "bom.t3d.txt"
    f.write_bytes(b"\xef\xbb\xbf" + _sample(orion_dir).encode("utf-8"))
    assert run([str(f)]) == 0


def test_cli_handles_utf16(tmp_path, orion_dir):
    f = tmp_path / "u16.t3d.txt"
    f.write_bytes(_sample(orion_dir).encode("utf-16"))
    assert run([str(f)]) == 0


def test_cli_summary_includes_external_refs(orion_dir, capsys):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    assert run([str(f)]) == 0
    assert "external refs:" in capsys.readouterr().out
