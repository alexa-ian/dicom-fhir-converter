#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
import os
from fhir.resources import R4B as fr
from fhir.resources.R4B import reference
from fhir.resources.R4B import imagingstudy
from fhir.resources.R4B import identifier
from pydicom import dcmread
from pydicom import dataset
from tqdm import tqdm
import logging
import hashlib

from dicom2fhir.dicom2fhirutils import gen_coding, gen_started_datetime, SOP_CLASS_SYS, ACQUISITION_MODALITY_SYS, gen_bodysite_coding, gen_accession_identifier, gen_studyinstanceuid_identifier, gen_codeable_concept, dcm_coded_concept, gen_procedurecode_array, gen_started_datetime, dcm_coded_concept, gen_reason

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


def _add_imaging_study_series(study: imagingstudy.ImagingStudy, ds: dataset.FileDataset):

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


def _create_imaging_study(ds) -> imagingstudy.ImagingStudy:
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


from typing import Tuple, Optional

def process_dicom_2_fhir(dcmDir: str) -> Tuple[Optional[imagingstudy.ImagingStudy], Optional[str]]:
    files = []
    # TODO: subdirectory must be traversed
    for r, d, f in os.walk(dcmDir):
        for file in f:
            files.append(os.path.join(r, file))

    studyInstanceUID = None
    imagingStudy = None
    for fp in tqdm(files):
        try:
            with dcmread(fp, None, stop_before_pixels=True, force=True) as ds:
                if studyInstanceUID is None:
                    studyInstanceUID = ds.StudyInstanceUID
                if studyInstanceUID != ds.StudyInstanceUID:
                    raise Exception(
                        "Incorrect DCM path, more than one study detected")
                if imagingStudy is None:
                    imagingStudy, _ = _create_imaging_study(ds)
                else:
                    _add_imaging_study_series(imagingStudy, ds)
        except Exception as e:
            logging.error(e)
            pass  # file is not a dicom file
    if imagingStudy is not None:
        modality_set = {
            s.modality.code: s.modality
            for s in imagingStudy.series if s.modality is not None
        }
        imagingStudy.modality = list(modality_set.values())
    return imagingStudy, studyInstanceUID