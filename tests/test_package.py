from reliable_agent_runtime import __doc__


def test_package_has_public_identity() -> None:
    assert __doc__ == "Reliable Agent Runtime package."
