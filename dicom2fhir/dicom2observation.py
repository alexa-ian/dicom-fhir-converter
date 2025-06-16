# -*- coding: utf-8 -*-
import uuid
from typing import List
from pydicom.dataset import Dataset
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.imagingstudy import ImagingStudy
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from dicom2fhir.dicom2fhirutils import gen_started_datetime

def build_observation_resources(ds: Dataset, patient: Patient, study: ImagingStudy, config: dict) -> List[Observation]:
    observations = []
    
    def create_obs(code: str, display: str, value: float, unit: str, system: str, code_unit: str) -> Observation:
        return Observation.model_construct(
            id=str(uuid.uuid4()),
            status="final",
            category=[CodeableConcept.model_construct(
                coding=[Coding.model_construct(system="http://terminology.hl7.org/CodeSystem/observation-category", code="vital-signs")]
            )],
            code=CodeableConcept.model_construct(
                coding=[Coding.model_construct(system="http://loinc.org", code=code, display=display)],
                text=display
            ),
            subject={
                "reference": f"Patient/{patient.id}" if patient else None
            },
            partOf=[{
                "reference": f"ImagingStudy/{study.id}" if study else None
            }],
            effectiveDateTime=gen_started_datetime(ds.StudyDate, ds.StudyTime),
            valueQuantity=Quantity.model_construct(value=value, unit=unit, system=system, code=code_unit)
        )

    if "PatientWeight" in ds:
        try:
            weight = float(ds.PatientWeight)
            observations.append(create_obs("29463-7", "Body Weight", weight, "kg", "http://unitsofmeasure.org", "kg"))
        except ValueError:
            pass

    if "PatientSize" in ds:
        try:
            height = float(ds.PatientSize)
            observations.append(create_obs("8302-2", "Body Height", height, "m", "http://unitsofmeasure.org", "m"))
        except ValueError:
            pass

    return observations