#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from os import PathLike
from pathlib import Path
from fhir.resources import R4B as fr
from fhir.resources.R4B import reference
from fhir.resources.R4B import imagingstudy
from fhir.resources.R4B import identifier
from pydicom import dcmread
from pydicom import dataset
from tqdm import tqdm
import logging
import hashlib
from typing import Tuple, Iterable, Union
from dicom2fhir.dicom2fhirutils import gen_coding, gen_started_datetime, SOP_CLASS_SYS, ACQUISITION_MODALITY_SYS, gen_bodysite_coding, gen_accession_identifier, gen_studyinstanceuid_identifier, gen_codeable_concept, dcm_coded_concept, gen_procedurecode_array, gen_started_datetime, dcm_coded_concept, gen_reason
from helpers import get_or

StrPath = Union[str, PathLike]

def _add_imaging_study_instance(
    study: imagingstudy.ImagingStudy,
    series: imagingstudy.ImagingStudySeries,
    ds: dataset.Dataset
):
    selectedInstance = None
    instanceUID = ds.SOPInstanceUID
    if series.instance is not None:
        selectedInstance = next(
            (i for i in series.instance if i.uid == instanceUID), None)
    else:
        series.instance = []

    if selectedInstance is not None:
        print("Error: SOP Instance UID is not unique")
        print(selectedInstance.as_json())
        return

    instance_data = {}

    instance_data["uid"] = instanceUID
    instance_data["sopClass"] = gen_coding(
        code="urn:oid:" + ds.SOPClassUID,
        system=SOP_CLASS_SYS
    )
    instance_data["number"] = ds.InstanceNumber

    try:
        if series.modality.code == "SR":
            seq = ds.ConceptNameCodeSequence
            instance_data["title"] = seq[0x0008, 0x0104]
        else:
            instance_data["title"] = '\\'.join(ds.ImageType)
    except Exception:
        pass  # print("Unable to set instance title")

    # instantiate selected instancee here
    selectedInstance = fr.imagingstudy.ImagingStudySeriesInstance(
        **instance_data)

    series.instance.append(selectedInstance)
    study.numberOfInstances = study.numberOfInstances + 1
    series.numberOfInstances = series.numberOfInstances + 1
    return


def _add_imaging_study_series(study: imagingstudy.ImagingStudy, ds: dataset.Dataset):

    # inti data container
    series_data = {}

    seriesInstanceUID = ds.SeriesInstanceUID
    # TODO: Add test for studyInstanceUID ... another check to make sure it matches
    selectedSeries = None
    if study.series is not None:
        selectedSeries = next(
            (s for s in study.series if s.uid == seriesInstanceUID), None)
    else:
        study.series = []

    if selectedSeries is not None:
        _add_imaging_study_instance(study, selectedSeries, ds)
        return

    series_data["uid"] = seriesInstanceUID
    try:
        if ds.SeriesDescription != '':
            series_data["description"] = ds.SeriesDescription
    except Exception:
        pass

    series_data["number"] = ds.SeriesNumber
    series_data["numberOfInstances"] = 0

    series_data["modality"] = gen_coding(
        code=ds.Modality,
        system=ACQUISITION_MODALITY_SYS
    )
    #dicom2fhirutils.update_study_modality_list(study_lists, ds.Modality)

    stime = None
    try:
        stime = ds.SeriesTime
    except Exception:
        pass  # print("Series TimeDate is missing")

    try:
        sdate = ds.SeriesDate
        series_data["started"] = gen_started_datetime(
            sdate, stime)
    except Exception:
        pass  # print("Series Date is missing")

    try:
        series_data["bodySite"] = gen_bodysite_coding(ds.BodyPartExamined)
        # dicom2fhirutils.update_study_bodysite_list(
        #     study, series_data["bodySite"])
    except Exception:
        pass  # print ("Body Part Examined missing")

    try:
        series_data["laterality"] = gen_coding(ds.Laterality)
        # dicom2fhirutils.update_study_laterality_list(
        #     study, series_data["laterality"])
    except Exception:
        pass  # print ("Laterality missing")

    # TODO: evaluate if we wonat to have inline "performer.actor" for the I am assuming "technician"
    # PerformingPhysicianName	0x81050
    # PerformingPhysicianIdentificationSequence	0x81052

    # extension stuff here
    # if series_data["modality"].code == "MR":
    #     try:
    #         series_data["scanningSequence"] = dicom2fhirutils.gen_extension(
    #             url="test.url.de",
    #             value=ds[0x0018, 0x0020].value,
    #             system=dicom2fhirutils.SCANNING_SEQUENCE_SYS,
    #             type="Coding"
    #         )
    #     except Exception:
    #         pass
        # try:
        #     series_data["scanningVariant"] = dicom2fhirutils.gen_codeable_concept(
        #         value_list=[ds[0x0018, 0x0021].value],
        #         system=dicom2fhirutils.SCANNING_VARIANT_SYS
        #     )
        # except Exception:
        #     pass
        # try:
        #     series_data["echoTime"] = ds[0x0018, 0x0081].value
        # except Exception:
        #     pass

    # Creating New Series
    series = imagingstudy.ImagingStudySeries(**series_data)

    study.series.append(series)
    study.numberOfSeries = len(study.series)
    _add_imaging_study_instance(study, series, ds)
    return


def _create_imaging_study(ds) -> Tuple[imagingstudy.ImagingStudy, list]:
    study_data = {}
    study_data["id"] = str(uuid.uuid4())
    study_data["status"] = "available"
    try:
        if ds.StudyDescription != '':
            study_data["description"] = ds.StudyDescription
    except Exception:
        pass  # missing study description

    study_data["identifier"] = []
    study_data["identifier"].append(gen_accession_identifier(ds.AccessionNumber))
    study_data["identifier"].append(gen_studyinstanceuid_identifier(ds.StudyInstanceUID))

    ipid = None
    try:
        ipid = ds.IssuerOfPatientID
    except Exception:
        pass  # print("Issuer of Patient ID is missing")
    
    patID9 = str(ds.PatientID)[:9]
    patIdentifier = "https://fhir.diz.uk-erlangen.de/identifiers/patient-id|"+patID9
    hashedIdentifier = hashlib.sha256(patIdentifier.encode('utf-8')).hexdigest()
    patientReference = "Patient/"+hashedIdentifier
    patientRef = reference.Reference()
    patientRef.reference = patientReference
    patIdent = identifier.Identifier()
    patIdent.system = "https://fhir.diz.uk-erlangen.de/identifiers/patient-id"
    patIdent.type = gen_codeable_concept(["MR"],"http://terminology.hl7.org/CodeSystem/v2-0203")
    patIdent.value = patID9
    patientRef.identifier = patIdent
    study_data["subject"] = patientRef
    # study_data["endpoint"] = []
    # endpoint = reference.Reference()
    # endpoint.reference = "file://" + dcmDir

    # study_data["endpoint"].append(endpoint)

    procedures = []
    try:
        procedures = dcm_coded_concept(ds.ProcedureCodeSequence)
    except Exception:
        pass  # procedure code sequence not found

    study_data["procedureCode"] = gen_procedurecode_array(
        procedures)

    studyTime = None
    try:
        studyTime = ds.StudyTime
    except Exception:
        pass  # print("Study Date is missing")

    try:
        studyDate = ds.StudyDate
        study_data["started"] = gen_started_datetime(studyDate, studyTime)
    except Exception:
        pass  # print("Study Date is missing")

    # TODO: we can add "inline" referrer
    # TODO: we can add "inline" reading radiologist.. (interpreter)

    reason = None
    reasonStr = None
    try:
        reason = dcm_coded_concept(ds.ReasonForRequestedProcedureCodeSequence)
    except Exception:
        pass  # print("Reason for Request procedure Code Seq is not available")

    try:
        reasonStr = ds.ReasonForTheRequestedProcedure
    except Exception:
        pass  # print ("Reason for Requested procedures not found")

    study_data["reasonCode"] = gen_reason(reason, reasonStr)

    study_data["numberOfSeries"] = 0
    study_data["numberOfInstances"] = 0

    # instantiate study here, when all required fields are available
    study = imagingstudy.ImagingStudy(**study_data)
    study_lists = []

    _add_imaging_study_series(study, ds)
    return study, study_lists

def _process_instance(ds: dataset.Dataset, imagingStudy: imagingstudy.ImagingStudy | None = None) -> imagingstudy.ImagingStudy | None:
    """
    Process a single DICOM dataset and return an ImagingStudy object.
    If imagingStudy is provided, it will be updated with the new series and instances.
    """
    if imagingStudy is None:
        imagingStudy, _ = _create_imaging_study(ds)
    else:
        _add_imaging_study_series(imagingStudy, ds)
    return imagingStudy

def _finalize_imaging_study(imagingStudy) -> imagingstudy.ImagingStudy:
    modality_set = {
        s.modality.code: s.modality
        for s in imagingStudy.series or []
        if s.modality is not None
    }
    imagingStudy.modality = list(modality_set.values())
    return imagingStudy

def _process_dicom_2_fhir_instances(instances: Iterable[dataset.Dataset], config: dict) -> imagingstudy.ImagingStudy:
    imagingStudy = None
    for ds in instances:
        try:
            imagingStudy = _process_instance(ds, imagingStudy)
        except:
            sop_instance_uid = ds.SOPInstanceUID if hasattr(ds, 'SOPInstanceUID') else 'unknown'
            logging.exception(f"An error occurred while processing DICOM instance {sop_instance_uid}")
            raise

    return _finalize_imaging_study(imagingStudy)

def is_dicom_file(path: str) -> bool:
    try:
        with open(path, 'rb') as f:
            f.seek(128)
            return f.read(4) == b'DICM'
    except Exception:
        return False

def _process_dicom_2_fhir_directory(dcmDir: StrPath, config: dict) -> imagingstudy.ImagingStudy:
    """
    Process DICOM files in a directory into an ImagingStudy FHIR resource.

    :param dcmDir: Directory containing DICOM files.
    :return: ImagingStudy resource. 
    """
    base = Path(dcmDir)
    if not base.is_dir():
        raise ValueError(f"Directory '{dcmDir}' not found")

    skip_invalid_files = get_or(config, "directory_parser.skip_invalid_files", True)

    studyInstanceUID = None
    imagingStudy = None
    for fp in tqdm(base.rglob("*")):
        if not fp.is_file():
            continue
        if skip_invalid_files and not is_dicom_file(str(fp)):
            logging.warning(f"Skipping invalid DICOM file: {fp}")
            continue

        try:
            ds = dcmread(str(fp), stop_before_pixels=True, force=True)
            if studyInstanceUID is None:
                studyInstanceUID = ds.StudyInstanceUID
            if studyInstanceUID != ds.StudyInstanceUID:
                raise Exception("Incorrect DCM path, more than one study detected")
            imagingStudy = _process_instance(ds, imagingStudy)
        except:
            logging.exception(f"An error occurred while processing DICOM file {fp}")
            raise

    return _finalize_imaging_study(imagingStudy)

def process_dicom_2_fhir(dcms: StrPath | Iterable[dataset.Dataset], config: dict = {}) -> imagingstudy.ImagingStudy:
    """
    Process DICOM files or datasets into an ImagingStudy FHIR resource.
    
    :param dcms: Either a directory containing DICOM files or an iterable of DICOM datasets.
    :return: ImagingStudy resource.
    """
    if isinstance(dcms, StrPath):
        return _process_dicom_2_fhir_directory(dcms, config)
    else:
        return _process_dicom_2_fhir_instances(dcms, config)
