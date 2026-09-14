import beaver_db


def test_package_importable():
    assert isinstance(beaver_db.__version__, str)
    assert len(beaver_db.__version__) > 0
