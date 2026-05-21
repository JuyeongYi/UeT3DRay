import subprocess
import sys


def test_single_file_arg_works(tmp_path):
    p = tmp_path / 'x.t3d.txt'
    p.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="X"\nEnd Object\n',
        encoding='utf-8')
    r1 = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', str(p)],
        capture_output=True, text=True, encoding='utf-8')
    r2 = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'summary', str(p)],
        capture_output=True, text=True, encoding='utf-8')
    assert r1.returncode == 0 and r2.returncode == 0
    assert r1.stdout == r2.stdout


def test_lenient_flag_warns_on_bad_parse(tmp_path):
    p = tmp_path / 'bad.t3d.txt'
    p.write_text('Begin Object Class=X Name="X"\n', encoding='utf-8')
    r = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'summary', str(p), '--lenient'],
        capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0
    assert ('warning' in r.stdout.lower() or 'warning' in r.stderr.lower()
            or '실패' in r.stdout or '실패' in r.stderr)


def test_strict_default_fails_on_bad(tmp_path):
    p = tmp_path / 'bad.t3d.txt'
    p.write_text('Begin Object Class=X Name="X"\n', encoding='utf-8')
    r = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'summary', str(p)],
        capture_output=True, text=True, encoding='utf-8')
    assert r.returncode != 0
