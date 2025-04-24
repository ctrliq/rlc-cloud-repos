try:  # pragma: no cover
    # Try importlib.metadata first (available in Python 3.8+)
    from importlib.metadata import version

    __version__ = version("rlc.cloud-repos")
except ImportError:  # pragma: no cover
    try:
        # Fallback to pkg_resources
        from pkg_resources import get_distribution

        __version__ = get_distribution("rlc.cloud-repos").version
    except Exception:  # pragma: no cover
        __version__ = "unknown"
