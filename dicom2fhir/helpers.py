# -*- coding: utf-8 -*-
import os
import uuid
import hashlib
from typing import Callable
from pydicom import dataset

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

# default id functions
def default_id_function(pepper: str | None = None) -> Callable[[str, dataset.Dataset], str]:
    """
    Default ID function for FHIR resource id generation.
    Can be customized with a pepper string for additional uniqueness.
    """
    def _id(resource_type: str, ds: dataset.Dataset) -> str:
        if not isinstance(ds, dataset.Dataset):
            raise TypeError("Expected a pydicom Dataset object")

        base_string = ""
        if resource_type == "ImagingStudy" and hasattr(ds, "StudyInstanceUID"):
            base_string = ds.StudyInstanceUID
        elif resource_type == "Patient" and hasattr(ds, "PatientID"):
            base_string = ds.PatientID
        elif resource_type == "Device" and hasattr(ds, "DeviceSerialNumber"):
            uid = ds.get("DeviceUID") or ''
            ser = ds.get("DeviceSerialNumber") or ''
            mod = ds.get("ManufacturerModelName") or ''
            base_string = f"{uid}{ser}{mod}"
        else:
            return str(uuid.uuid4())

        return hashlib.sha256(f"{base_string}{pepper or ''}".encode("utf-8")).hexdigest()

    return _id