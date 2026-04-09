import pathlib

from platformdirs import user_cache_path, user_config_path, user_data_path


def get_cache_path() -> pathlib.Path:
    """Return the path to the user's cache directory."""
    return user_cache_path("brunel", "brunel")


def get_data_path() -> pathlib.Path:
    """Return the path to the user's data directory."""
    return user_data_path("brunel", "brunel")


def get_config_path() -> pathlib.Path:
    """Return the path to the user's config directory."""
    return user_config_path("brunel", "brunel")


def get_home_path() -> pathlib.Path:
    """Return the path to the user's home directory."""
    return pathlib.Path.home()


def get_install_path() -> pathlib.Path:
    """Return the path to the installation directory."""
    return pathlib.Path(__file__).parent.parent
