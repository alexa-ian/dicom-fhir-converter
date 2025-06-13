# -*- coding: utf-8 -*-
import os

def get_or(d: dict, path: str, default=None):
    """
    Get a value from a nested dictionary using a dot-separated path.
    If the path does not exist, return the default value.
    """
    keys = path.split('.')
    val = d
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val if val is not None else default

def env_or_config(env: str, config_path: str, config: dict):
    """
    Return the value of an environment variable or a configuration key.
    If neither is set raise a ValueError.
    """
    if env in os.environ:
        return os.environ[env]

    val = get_or(config, config_path)
    if val is None:
        raise ValueError(f"Neither environment variable '{env}' nor configuration key '{config_path}' is set.")
    return val