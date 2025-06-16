

# dicom2fhir/utils/patient_mapping.py
import re
import datetime
import uuid
from typing import Union
from pydicom.dataset import Dataset
from pydicom.valuerep import PersonName
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.humanname import HumanName
from fhir.resources.R4B.address import Address
from fhir.resources.R4B.contactpoint import ContactPoint
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.fhirtypes import DateType
from fhir.resources.R4B.extension import Extension
from fhir.resources.R4B.quantity import Quantity
from dicom2fhir.helpers import get_or

DATE8_REGEX = re.compile(r'^(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$')

def dicom_name_to_fhir(name: Union[PersonName, str, None]) -> HumanName:
    """
    Convert DICOM PersonName to FHIR HumanName.

    DICOM name format: 'Family^Given^Middle^Prefix^Suffix'
    """
    name = PersonName(name) if not isinstance(name, PersonName) else name
    if name is None:
        return HumanName.model_construct()

    return HumanName.model_construct(
        family      = name.family_name,
        given       = [n for n in [name.given_name, name.middle_name] if n],
        prefix      = name.name_prefix,
        suffix      = name.name_suffix
    )


def dicom_birthdate_to_fhir(birthdate: str) -> DateType | None:
     """
     Convert DICOM PatientBirthDate (YYYYMMDD) to FHIR-compliant date.
     Returns a datetime.date or None if invalid.
     """
     if not isinstance(birthdate, str) or not DATE8_REGEX.match(birthdate):
         return None

     try:
         year = int(birthdate[:4])
         month = int(birthdate[4:6])
         day = int(birthdate[6:])
         return datetime.date(year, month, day)
     except ValueError:
         return None

def dicom_gender_to_fhir(sex: str) -> str:
    """
    Map DICOM PatientSex to FHIR gender.
    - 'M' -> 'male'
    - 'F' -> 'female'
    - 'O' or other -> 'other'
    """
    mapping = {
        'M': 'male',
        'F': 'female',
        'O': 'other'
    }
    return mapping.get(sex.upper(), 'unknown') if sex else 'unknown'

def dicom_address_to_fhir(address_str: str) -> Address:
    """
    Convert DICOM address string to FHIR Address.
    Format: 'Street^OtherDesignation^City^State^PostalCode^Country'
    """
    if not address_str:
        return Address.model_construct()

    parts = address_str.split("^")
    return Address.model_construct(
        line=[parts[0]] if parts[0] else None,
        city=parts[2] if len(parts) > 2 else None,
        state=parts[3] if len(parts) > 3 else None,
        postalCode=parts[4] if len(parts) > 4 else None,
        country=parts[5] if len(parts) > 5 else None
    )

def build_patient_resource(ds: Dataset, config: dict) -> Patient:

    patient = Patient.model_construct()

    # Identifier
    if "PatientID" in ds:
        patient.id = config['id_function'](ds.PatientID)
        patient.identifier = [
            Identifier.model_construct(
                use="usual",
                system="urn:dicom:patient-id",
                value=ds.PatientID,
                assigner={"display": ds.get("IssuerOfPatientID")} if "IssuerOfPatientID" in ds else None
            )
        ]
    else:
        patient.id = str(uuid.uuid4())

    # Name
    if "PatientName" in ds:
        patient.name = [dicom_name_to_fhir(ds.PatientName)]

    # BirthDate
    if "PatientBirthDate" in ds:
        patient.birthDate = dicom_birthdate_to_fhir(ds.PatientBirthDate)

    # Gender
    if "PatientSex" in ds:
        patient.gender = dicom_gender_to_fhir(ds.PatientSex)

    # Address
    if "PatientAddress" in ds:
        patient.address = [dicom_address_to_fhir(ds.PatientAddress)]

    # Telecom
    if "PatientTelephoneNumbers" in ds:
        tel = ds.PatientTelephoneNumbers
        if not isinstance(tel, list):
            tel = [tel]
        patient.telecom = [
            ContactPoint.model_construct(system="phone", value=phone, use="home") for phone in tel
        ]

    # Only add Extensions if configured
    if get_or(config, "generator.patient.add_extensions", False):

        extensions = []

        if "PatientAge" in ds:
            extensions.append(
                Extension.model_construct(
                    url="http://hl7.org/fhir/StructureDefinition/patient-age",
                    valueAge={"value": int(ds.PatientAge[:-1]), "unit": "years"}
                )
            )

        if "PatientWeight" in ds:
            extensions.append(
                Extension.construct(
                    url="http://hl7.org/fhir/StructureDefinition/bodyWeight",
                    valueQuantity=Quantity.model_construct(
                        value=float(ds.PatientWeight), unit="kg", system="http://unitsofmeasure.org", code="kg"
                    )
                )
            )

        if "PatientSize" in ds:
            extensions.append(
                Extension.model_construct(
                    url="http://hl7.org/fhir/StructureDefinition/bodyHeight",
                    valueQuantity=Quantity.model_construct(
                        value=float(ds.PatientSize), unit="m", system="http://unitsofmeasure.org", code="m"
                    )
                )
            )

        if extensions:
            patient.extension = extensions

    return patient