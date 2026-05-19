from t3dgraph.core.t3d.tokenizer import tokenize_lines, Line


def test_blank_and_indent():
    src = "Begin Object Class=A Name=\"X\"\n   Direction=Output\nEnd Object\n"
    lines = tokenize_lines(src)
    assert [l.indent for l in lines] == [0, 3, 0]
    assert lines[0].text == 'Begin Object Class=A Name="X"'
    assert lines[1].text == "Direction=Output"
    assert lines[2].text == "End Object"


def test_line_numbers_are_1_based():
    lines = tokenize_lines("a\nb\n")
    assert [l.number for l in lines] == [1, 2]


def test_trailing_blank_lines_skipped():
    lines = tokenize_lines("a\n\n  \n")
    assert [l.text for l in lines] == ["a"]
