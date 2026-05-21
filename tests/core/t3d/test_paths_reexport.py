def test_legacy_import_still_works():
    from t3dgraph.core.t3d.paths import node_of, pin_segment, type_suffix
    assert node_of("A.B") == "A"
    assert pin_segment("A.B.C", 1) == "B"
    assert type_suffix("/Script/X.Foo") == "Foo"


def test_legacy_and_new_are_same_symbol():
    from t3dgraph.core.t3d.paths import node_of as legacy
    from t3dgraph.core.base.paths import node_of as new
    assert legacy is new
