import json
import subprocess
import sys
from pathlib import Path


def _sample(tmp_path):
    p = tmp_path / 'x.t3d.txt'
    p.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="O"\n'
        '    CPPType="float"\n    Direction=Output\n'
        '  End Object\nEnd Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="B"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="I"\n'
        '    CPPType="float"\n    Direction=Input\n'
        '  End Object\nEnd Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L0"\n'
        '  SourcePinPath="A.O"\n  TargetPinPath="B.I"\nEnd Object\n',
        encoding='utf-8')
    return p


def test_dataflow_subcommand_json(tmp_path):
    p = _sample(tmp_path)
    r = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'dataflow', str(p), '--json'],
        capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert {'source': 'A.O', 'target': 'B.I'} in json.loads(r.stdout)['data_edges']


def test_dataflow_subcommand_text(tmp_path):
    p = _sample(tmp_path)
    r = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'dataflow', str(p)],
        capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0
    assert 'A.O' in r.stdout and 'B.I' in r.stdout
