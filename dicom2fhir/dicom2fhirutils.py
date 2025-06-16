from datetime import datetime

from fhir.resources.R4B import imagingstudy
from fhir.resources.R4B import identifier
from fhir.resources.R4B import codeableconcept
from fhir.resources.R4B import coding
from fhir.resources.R4B import patient
from fhir.resources.R4B import humanname
from fhir.resources.R4B import fhirtypes
from fhir.resources.R4B import reference
from fhir.resources.R4B import extension
import pandas as pd
import json
from pathlib import Path
import os
import logging

TERMINOLOGY_CODING_SYS = "http://terminology.hl7.org/CodeSystem/v2-0203"
TERMINOLOGY_CODING_SYS_CODE_ACCESSION = "ACSN"
TERMINOLOGY_CODING_SYS_CODE_MRN = "MR"

ACQUISITION_MODALITY_SYS = "http://dicom.nema.org/resources/ontology/DCM"
SCANNING_SEQUENCE_SYS = "https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.3.html"
SCANNING_VARIANT_SYS = "https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.3.html"

SOP_CLASS_SYS = "urn:ietf:rfc:3986"

# load rather expesive resource into global var to make it reusable
BODYSITE_SNOMED_MAPPING_PATH = Path(__file__).parent / "resources" / "terminologies" / "bodysite_snomed.json"
BODYSITE_SNOMED_MAPPING = pd.DataFrame(json.loads(BODYSITE_SNOMED_MAPPING_PATH.read_text(encoding="utf-8")))

def _get_snomed(dicom_bodypart: str, sctmapping: pd.DataFrame) -> dict[str, str] | None:
    _rec = sctmapping.loc[sctmapping['Body Part Examined'] == dicom_bodypart]
    if _rec.empty:
        return None
    return {
        'code': _rec["Code Value"].iloc[0],
        'display': _rec["Code Meaning"].iloc[0],
    }

def gen_accession_identifier(id):
    idf = identifier.Identifier.model_construct()
    idf.use = "usual"
    idf.type = codeableconcept.CodeableConcept.model_construct()
    idf.type.coding = []
    acsn = coding.Coding.model_construct()
    acsn.system = TERMINOLOGY_CODING_SYS
    acsn.code = TERMINOLOGY_CODING_SYS_CODE_ACCESSION

    idf.type.coding.append(acsn)
    idf.value = id
    return idf


def gen_studyinstanceuid_identifier(id):
    idf = identifier.Identifier.model_construct()
    idf.system = "urn:dicom:uid"
    idf.value = "urn:oid:" + id
    return idf


def get_patient_resource_ids(PatientID, IssuerOfPatientID):
    idf = identifier.Identifier.model_construct()
    idf.use = "usual"
    idf.value = PatientID

    idf.type = codeableconcept.CodeableConcept.model_construct()
    idf.type.coding = []
    id_coding = coding.Coding.model_construct()
    id_coding.system = TERMINOLOGY_CODING_SYS
    id_coding.code = TERMINOLOGY_CODING_SYS_CODE_MRN
    idf.type.coding.append(id_coding)

    if IssuerOfPatientID is not None:
        idf.assigner = reference.Reference.model_construct()
        idf.assigner.display = IssuerOfPatientID

    return idf


def calc_gender(gender):
    if gender is None:
        return "unknown"
    if not gender:
        return "unknown"
    if gender.upper().lower() == "f":
        return "female"
    if gender.upper().lower() == "m":
        return "male"
    if gender.upper().lower() == "o":
        return "other"

    return "unknown"


def calc_dob(dicom_dob):
    if dicom_dob == '':
        return None

    try:
        dob = datetime.strptime(dicom_dob, '%Y%m%d')
        fhir_dob = fhirtypes.Date(
            dob.year,
            dob.month,
            dob.day
        )
    except Exception:
        return None
    return fhir_dob


def inline_patient_resource(referenceId, PatientID, IssuerOfPatientID, patientName, gender, dob):
    p = patient.Patient.model_construct()
    p.id = referenceId
    p.name = []
    # p.use = "official"
    p.identifier = [get_patient_resource_ids(PatientID, IssuerOfPatientID)]
    hn = humanname.HumanName.model_construct()
    hn.family = patientName.family_name
    if patientName.given_name != '':
        hn.given = [patientName.given_name]
    p.name.append(hn)
    p.gender = calc_gender(gender)
    p.birthDate = calc_dob(dob)
    p.active = True
    return p


def gen_procedurecode_array(procedures):
    if procedures is None:
        return None
    fhir_proc = []
    for p in procedures:
        concept = codeableconcept.CodeableConcept.model_construct()
        c = coding.Coding.model_construct()
        c.system = p["system"]
        c.code = p["code"]
        c.display = p["display"]
        concept.coding = []
        concept.coding.append(c)
        concept.text = p["display"]
        fhir_proc.append(concept)
    if len(fhir_proc) > 0:
        return fhir_proc
    return None


def gen_started_datetime(dt, tm):
    if dt is None:
        return None

    dt_pattern = '%Y%m%d'

    if tm is not None and len(tm) >= 6:
        studytm = datetime.strptime(tm[0:6], '%H%M%S')

        dt_string = dt + " " + str(studytm.hour) + ":" + \
            str(studytm.minute) + ":" + str(studytm.second)
        dt_pattern = dt_pattern + " %H:%M:%S"
    else:
        dt_string = dt

    dt_date = datetime.strptime(dt_string, dt_pattern)

    # strangely, providing the datetime.date object does not work
    fhirDtm = datetime(
        dt_date.year,
        dt_date.month,
        dt_date.day,
        dt_date.hour,
        dt_date.minute,
        dt_date.second
    )

    return fhirDtm

def gen_reason(reason, reasonStr):
    if reason is None and reasonStr is None:
        return None
    reasonList = []
    if reason is None or len(reason) <= 0:
        rc = codeableconcept.CodeableConcept.model_construct()
        rc.text = reasonStr
        reasonList.append(rc)
        return reasonList

    for r in reason:
        rc = codeableconcept.CodeableConcept.model_construct()
        rc.coding = []
        c = coding.Coding.model_construct()
        c.system = r["system"]
        c.code = r["code"]
        c.display = r["display"]
        rc.coding.append(c)
        reasonList.append(rc)
    return reasonList


def gen_coding(code: str, system: str|None = None, display: str|None = None):
    if isinstance(code, list):
        raise Exception(
        "More than one code for type Coding detected")
    c = coding.Coding.model_construct()
    c.code = code
    c.system = system
    c.display = display
    if system is None and display is None:
        c.userSelected = True

    return c

def gen_codeable_concept(value_list: list, system):
    c = codeableconcept.CodeableConcept.model_construct()
    c.coding = []
    for _l in value_list:
        m = gen_coding(_l, system)
        c.coding.append(m)
    return c

def gen_bodysite_coding(bd):

    bd_snomed = _get_snomed(bd, sctmapping=BODYSITE_SNOMED_MAPPING)
    
    if bd_snomed is None:
        return gen_coding(code=str(bd))
    
    return gen_coding(
        code=str(bd_snomed['code']),
        system="http://snomed.info/sct",
        display=bd_snomed['display']
    ) 

# def update_study_modality_list(study_list_modality: list, modality: str):
#     if study_list_modality is None or len(study_list_modality) <= 0:
#         study_list_modality = []
#         study_list_modality.append(modality)
#         return

#     c = next((mc for mc in study_list_modality if
#               mc == modality), None)
#     if c is not None:
#         return

#     study_list_modality.append(modality)
#     return


# def update_study_bodysite_list(study: imagingstudy.ImagingStudy, bodysite: coding.Coding):
#     if study.bodySite__ext is None or len(study.bodySite__ext) <= 0:
#         study.bodySite__ext = []
#         study.bodySite__ext.append(bodysite)
#         return

#     c = next((mc for mc in study.bodySite__ext if
#               mc.system == bodysite.system and
#               mc.code == bodysite.code), None)
#     if c is not None:
#         return

#     study.bodySite__ext.append(bodysite)
#     return


# def update_study_laterality_list(study: imagingstudy.ImagingStudy, laterality: coding.Coding):
#     if study.laterality__ext is None or len(study.laterality__ext) <= 0:
#         study.laterality__ext = []
#         study.laterality__ext.append(laterality)
#         return

#     c = next((mc for mc in study.laterality__ext if
#               mc.system == laterality.system and
#               mc.code == laterality.code), None)
#     if c is not None:
#         return

    # study.laterality__ext.append(laterality)
    # return


def dcm_coded_concept(CodeSequence):
    concepts = []
    for seq in CodeSequence:
        concept = {}
        concept["code"] = seq[0x0008, 0x0100].value
        concept["system"] = seq[0x0008, 0x0102].value
        concept["display"] = seq[0x0008, 0x0104].value
        concepts.append(concept)
    return concepts