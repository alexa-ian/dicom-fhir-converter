import uuid
from fhir.resources.R4B import bundle
from fhir.resources.R4B import imagingstudy
from fhir.resources.R4B import patient
from pydicom import dataset
import logging
from dicom2fhir.dicom2fhirutils import gen_coding, gen_started_datetime, SOP_CLASS_SYS, ACQUISITION_MODALITY_SYS, gen_bodysite_coding, gen_accession_identifier, gen_studyinstanceuid_identifier, dcm_coded_concept, gen_procedurecode_array, gen_started_datetime, dcm_coded_concept, gen_reason
from dicom2fhir.dicom2patient import build_patient_resource
from dicom2fhir.helpers import get_or

class Dicom2FHIRBundle():

    def __init__(self, config: dict = {}):
        """
        Initialize the Dicom2FHIRBundle with an optional configuration.
        """
        self.study: imagingstudy.ImagingStudy | None = None
        self.series = {}
        self.instances = {}
        # Patient
        self.pat: patient.Patient | None = None
        self.config = config
        
    def add(self, ds: dataset.Dataset):
        """
        Add a DICOM dataset to the ImagingStudy.
        """
        if not isinstance(ds, dataset.Dataset):
            raise TypeError("Expected a pydicom Dataset object")

        # is first instance?
        if self.study is None:
            self.pat = build_patient_resource(ds, self.config)
            self._create_imaging_study(ds)

        self._add_imaging_study_series(ds)
        self._add_instance(ds)

    def _create_imaging_study(self, ds):

        study_data = {}
        study_data["resource_type"] = "ImagingStudy"
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

        # Set the patient reference
        study_data["subject"] = {
            "reference": f"Patient/{self.pat.id}" if self.pat else None
        }

        procedures = []
        try:
            procedures = dcm_coded_concept(ds.ProcedureCodeSequence)
        except Exception:
            pass  # procedure code sequence not found

        study_data["procedureCode"] = gen_procedurecode_array(procedures)

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
        self.study = imagingstudy.ImagingStudy(**study_data)
        
    def _add_imaging_study_series(self, ds: dataset.Dataset):

        series_instance_uid = str(ds.SeriesInstanceUID)

        if series_instance_uid in self.series:
            return  # Series already exists

        # inti data container
        self.series[series_instance_uid] = {}

        
        self.series[series_instance_uid]["uid"] = series_instance_uid
        try:
            if ds.SeriesDescription != '':
                self.series[series_instance_uid]["description"] = ds.SeriesDescription
        except Exception:
            pass

        self.series[series_instance_uid]["number"] = ds.SeriesNumber
        self.series[series_instance_uid]["numberOfInstances"] = 0

        self.series[series_instance_uid]["modality"] = gen_coding(
            code=ds.Modality,
            system=ACQUISITION_MODALITY_SYS
        )
        
        try:
            stime = ds.SeriesTime
            sdate = ds.SeriesDate
            self.series[series_instance_uid]["started"] = gen_started_datetime(sdate, stime)
        except Exception:
            pass  # print("Series Date/Time is missing")

        try:
            self.series[series_instance_uid]["bodySite"] = gen_bodysite_coding(ds.BodyPartExamined)
        except Exception:
            pass  # print ("Body Part Examined missing")

        try:
            self.series[series_instance_uid]["laterality"] = gen_coding(ds.Laterality)
        except Exception:
            pass  # print ("Laterality missing")
    
    def _add_instance(self, ds: dataset.Dataset):

        series_instance_uid = str(ds.SeriesInstanceUID)
        sop_instance_uid = str(ds.SOPInstanceUID)

        if series_instance_uid not in self.instances:
            self.instances[series_instance_uid] = {}

        if sop_instance_uid in self.instances[series_instance_uid]:
            print("Error: SOP Instance UID already exists in the series")
            print(self.instances[series_instance_uid][sop_instance_uid].as_json())
            return

        self.instances[series_instance_uid][sop_instance_uid] = {}
       
        self.instances[series_instance_uid][sop_instance_uid]["uid"] = sop_instance_uid
        self.instances[series_instance_uid][sop_instance_uid]["sopClass"] = gen_coding(
            code="urn:oid:" + ds.SOPClassUID,
            system=SOP_CLASS_SYS
        )
        self.instances[series_instance_uid][sop_instance_uid]["number"] = ds.InstanceNumber

        try:
            if str(ds.Modality) == "SR":
                seq = ds.ConceptNameCodeSequence
                self.instances[series_instance_uid][sop_instance_uid]["title"] = seq[0x0008, 0x0104]
            else:
                self.instances[series_instance_uid][sop_instance_uid]["title"] = '\\'.join(ds.ImageType)
        except Exception:
            pass  # print("Unable to set instance title")

    def _build_imaging_study(self) -> imagingstudy.ImagingStudy:
        """
        Build the ImagingStudy resource from the collected data.
        """
        if self.study is None:
            raise ValueError("No ImagingStudy data has been added")

        # Add series to the study
        self.study.series = []
        for series_uid, series_data in self.series.items():

            # only add sop instance data if configured
            if get_or(self.config, "generator.imaging_study.add_instances", False):
                series_data["instance"] = []
                for instance_uid, instance_data in self.instances.get(series_uid, {}).items():
                    series_data["instance"].append(imagingstudy.ImagingStudySeriesInstance(**instance_data))
                series_data["numberOfInstances"] = len(series_data["instance"])
            else:
                series_data["numberOfInstances"] = len(self.instances[series_uid])

            # Create ImagingStudySeries object
            series = imagingstudy.ImagingStudySeries(**series_data)
            self.study.series.append(series)

        # Set the number of series and instances
        self.study.numberOfSeries = len(self.study.series)
        self.study.numberOfInstances = sum(s.numberOfInstances for s in self.study.series)

        # Set the modalities
        modality_set = {
            s.modality.code: s.modality
            for s in self.study.series or []
            if s.modality is not None
        }
        self.study.modality = list(modality_set.values())

        return self.study
    
    def create_bundle(self) -> bundle.Bundle:
        """
        Create the final transaction bundle.
        """
        if not self.study:
            raise ValueError("No ImagingStudy data has been added")

        # Build the ImagingStudy resource
        _study = self._build_imaging_study()
    
        # wrap entries in a transaction Bundle and return
        return bundle.Bundle.model_validate({
            'resourceType': 'Bundle',
            'type': "transaction",
            'id': str(uuid.uuid4()),
            'entry': [
                {
                    'fullUrl': f"urn:uuid:{_study.id}",
                    'resource': _study,
                    'request': {
                        'method': 'PUT',
                        'url': f"ImagingStudy/{_study.id}"
                    }
                },
                {
                    'fullUrl': f"urn:uuid:{self.pat.id}",
                    'resource': self.pat,
                    'request': {
                        'method': 'PUT',
                        'url': f"Patient/{self.pat.id}"
                    }
                }
            ]
        })