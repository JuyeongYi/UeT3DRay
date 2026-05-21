import subprocess
import sys


def test_serialize_round_trip(tmp_path):
    src = 'Begin Object Class=/Script/Foo.Bar Name="X"\n   Prop=42\nEnd Object\n'
    p = tmp_path / 'x.t3d.txt'
    p.write_text(src, encoding='utf-8')
    r = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'serialize', str(p)],
        capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0
    assert 'Begin Object' in r.stdout
    assert 'Name="X"' in r.stdout
    assert 'Prop=42' in r.stdout
