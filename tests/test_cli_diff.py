import subprocess
import sys
import json


def _make_file(p, body):
    p.write_text(body, encoding='utf-8')


_NODE_A = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
    '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="O"\n'
    '    CPPType="float"\n    Direction=Output\n  End Object\nEnd Object\n'
)
_NODE_B = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="B"\n'
    '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="O"\n'
    '    CPPType="float"\n    Direction=Output\n  End Object\nEnd Object\n'
)
_NODE_S_ONE_PIN = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="S"\n'
    '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="I"\n'
    '    CPPType="float"\n    Direction=Input\n  End Object\nEnd Object\n'
)
_NODE_S_TWO_PINS = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="S"\n'
    '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="I"\n'
    '    CPPType="float"\n    Direction=Input\n  End Object\n'
    '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="J"\n'
    '    CPPType="float"\n    Direction=Input\n  End Object\nEnd Object\n'
)
_LINK_A_S = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L0"\n'
    '  SourcePinPath="A.O"\n  TargetPinPath="S.I"\nEnd Object\n'
)
_LINK_B_S = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L1"\n'
    '  SourcePinPath="B.O"\n  TargetPinPath="S.J"\nEnd Object\n'
)


def test_diff_basic(tmp_path):
    a = tmp_path / 'a.t3d.txt'
    b = tmp_path / 'b.t3d.txt'
    _make_file(a, _NODE_A + _NODE_S_ONE_PIN + _LINK_A_S)
    _make_file(b, _NODE_A + _NODE_B + _NODE_S_TWO_PINS + _LINK_A_S + _LINK_B_S)
    r = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'diff', str(a), str(b), '--json'],
        capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert 'S' in data['sinks_common']
    assert 'B' in data['per_sink']['S']['added_ancestors']


def test_diff_text_output(tmp_path):
    a = tmp_path / 'a.t3d.txt'
    b = tmp_path / 'b.t3d.txt'
    _make_file(a, _NODE_A + _NODE_S_ONE_PIN + _LINK_A_S)
    _make_file(b, _NODE_A + _NODE_B + _NODE_S_TWO_PINS + _LINK_A_S + _LINK_B_S)
    r = subprocess.run(
        [sys.executable, '-m', 't3dgraph.cli', 'diff', str(a), str(b)],
        capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert 'sinks common' in r.stdout
