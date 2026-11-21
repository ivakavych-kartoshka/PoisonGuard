def test_package_imports() -> None:
    import poisonguard
    from poisonguard.cli import build_parser
    assert poisonguard.__version__ == "0.1.0"
    assert build_parser().prog == "poisonguard"
