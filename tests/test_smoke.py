def test_import_airi_module() -> None:
    import airi  # noqa: F401

    assert hasattr(airi, "__version__")
