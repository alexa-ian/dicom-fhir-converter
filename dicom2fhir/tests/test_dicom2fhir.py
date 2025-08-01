import os
import unittest
from .. import dicom2fhir
from fhir.resources.R4B import imagingstudy


class testDicom2FHIR(unittest.TestCase):

    def test_instance_dicom2fhir(self):
        dcmDir = os.path.join(os.getcwd(), "dicom2fhir", "tests", "resources", "dcm-instance")
        study: imagingstudy.ImagingStudy
        study, _ = dicom2fhir.process_dicom_2_fhir(dcmDir)

        self.assertIsNotNone(study, "No ImagingStudy was generated")
        self.assertEqual(study.numberOfSeries, 1, "Number of Series in the study mismatch")
        self.assertEqual(study.numberOfInstances, 1, "Number of Instances in the study mismatch")
        self.assertIsNotNone(study.series, "Series was not built for the study")
        self.assertIsNotNone(study.modality, "Modality is missing")
        self.assertEqual(len(study.modality), 1, "Series must list only one modality")
        self.assertEqual(study.modality[0].code, "CR", "Incorrect modality detected")
        self.assertEqual(len(study.series), 1, "Number objects in Series Array: mismatch")
        self.assertEqual(len(study.series[0].instance), 1, "Number objects in Instance Array: mismatch")

        series: imagingstudy.ImagingStudySeries
        series = study.series[0]
        self.assertIsNotNone(series, "Missing Series")
        self.assertIsNotNone(series.bodySite, "Body site is missing")
        self.assertEqual(series.bodySite.code, '43799004', "Expected SNOMED code for CHEST")
        self.assertIsNotNone(series.bodySite.display, "BodySite display is missing")
        self.assertEqual(series.bodySite.display, 'Chest', "Chest is expected as body site")

        instance: imagingstudy.ImagingStudySeriesInstance
        instance = series.instance[0]
        self.assertIsNotNone(instance, "Missing Instance")

    def test_multi_instance_dicom(self):
        dcmDir = os.path.join(os.getcwd(), "dicom2fhir", "tests", "resources", "dcm-multi-instance")
        study: imagingstudy.ImagingStudy
        study, _ = dicom2fhir.process_dicom_2_fhir(dcmDir)
        self.assertIsNotNone(study, "No ImagingStudy was generated")
        self.assertEqual(study.numberOfSeries, 1)
        self.assertEqual(study.numberOfInstances, 5)
        self.assertIsNotNone(study.series, "Series was not built for the study")
        self.assertEqual(len(study.modality), 1, "Only single modality expected for this study")
        self.assertEqual(study.modality[0].code, "CR")
        self.assertEqual(len(study.series), 1, "Incorrect number of series detected")
        self.assertEqual(len(study.series[0].instance), 5, "Incorrect number of instances detected")

    def test_multi_series_dicom(self):
        dcmDir = os.path.join(os.getcwd(), "dicom2fhir", "tests", "resources", "dcm-multi-series")
        study: imagingstudy.ImagingStudy
        study, _ = dicom2fhir.process_dicom_2_fhir(dcmDir)
        self.assertIsNotNone(study, "No ImagingStudy was generated")
        self.assertEqual(study.numberOfSeries, 4, "Number of Series in the study mismatch")
        self.assertEqual(study.numberOfInstances, 4, "Number of Instances in the study mismatch")
        self.assertIsNotNone(study.series, "Series was not built for the study")
        self.assertEqual(len(study.modality), 1, "Only single modality expected for this study")
        self.assertEqual(study.modality[0].code, "CR", "Incorrect Modality detected")
        self.assertEqual(len(study.series), 4, "Number of series in the study: mismatch")
