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
