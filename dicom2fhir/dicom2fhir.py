#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import PathLike
from pathlib import Path
from fhir.resources.R4B import bundle
from pydicom import dcmread
from pydicom import dataset
from tqdm import tqdm
import logging
from typing import Iterable, Union
import dicom2fhir.helpers as helpers
from dicom2fhir.helpers import get_or
from dicom2fhir.dicom2fhirbundle import Dicom2FHIRBundle

StrPath = Union[str, PathLike]

def _parse_directory(dcmDir: StrPath, config: dict) -> Iterable[dataset.Dataset]:
    """
    Parse a directory of DICOM files including subdirectories and return instances as a Generator.

    :param dcmDir: Directory containing DICOM files.
    :return: Iterable[dataset.Dataset]
    """
    base = Path(dcmDir)
    if not base.is_dir():
        raise ValueError(f"Directory '{dcmDir}' not found")

    skip_invalid_files = get_or(config, "directory_parser.skip_invalid_files", True)

    def is_dicom_file(path: str) -> bool:
        try:
            with open(path, 'rb') as f:
                f.seek(128)
                return f.read(4) == b'DICM'
        except Exception:
            return False

    for fp in tqdm(base.rglob("*")):

        if not fp.is_file():
            continue
        if skip_invalid_files and not is_dicom_file(str(fp)):
            logging.warning(f"Skipping invalid DICOM file: {fp}")
            continue

        try:
            yield dcmread(str(fp), stop_before_pixels=True, force=True)
        except:
            logging.exception(f"An error occurred while processing DICOM file {fp}")
            raise

def _create_bundle(instances: Iterable[dataset.Dataset], config: dict = {}) -> bundle.Bundle:

    dcm2fhir = Dicom2FHIRBundle(config=config)
    
    for ds in instances:
        if not isinstance(ds, dataset.Dataset):
            raise TypeError("Expected a pydicom Dataset object")
        dcm2fhir.add(ds)

    return dcm2fhir.create_bundle()

def process_dicom_2_fhir(dcms: StrPath | Iterable[dataset.Dataset], config: dict = {}) -> bundle.Bundle:
    """
    Process DICOM files or datasets into an ImagingStudy FHIR resource.
    
    :param dcms: Either a directory containing DICOM files or an iterable of DICOM datasets.
    :return: ImagingStudy resource.
    """

    # use default id function for FHIR resource id generation
    if 'id_function' not in config:
        config['id_function'] = helpers.default_id_function()

    instances = _parse_directory(dcms, config) if isinstance(dcms, StrPath) else dcms
    return _create_bundle(instances, config)
