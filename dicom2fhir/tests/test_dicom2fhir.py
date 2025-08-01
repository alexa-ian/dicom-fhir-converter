import os
import unittest
from unittest import skipUnless
import json
import pydicom
from .. import dicom2fhir
from fhir.resources.R4B import imagingstudy


class testDicom2FHIR(unittest.TestCase):

    def test_instance_dicom2fhir(self):
        dcmDir = os.path.join(os.getcwd(), "dicom2fhir", "tests", "resources", "dcm-instance")
        study: imagingstudy.ImagingStudy
        study = dicom2fhir.process_dicom_2_fhir(dcmDir)

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
        study = dicom2fhir.process_dicom_2_fhir(dcmDir)
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
        study = dicom2fhir.process_dicom_2_fhir(dcmDir)
        self.assertIsNotNone(study, "No ImagingStudy was generated")
        self.assertEqual(study.numberOfSeries, 4, "Number of Series in the study mismatch")
        self.assertEqual(study.numberOfInstances, 4, "Number of Instances in the study mismatch")
        self.assertIsNotNone(study.series, "Series was not built for the study")
        self.assertEqual(len(study.modality), 1, "Only single modality expected for this study")
        self.assertEqual(study.modality[0].code, "CR", "Incorrect Modality detected")
        self.assertEqual(len(study.series), 4, "Number of series in the study: mismatch")

    @skipUnless(os.getenv("RUN_FMX_TESTS") == "1", "Skipping FMX tests by config")
    def test_fmx(self):

        import psycopg2
        import psycopg2.extras

        def env_or_config(env: str, config_path: str, config: dict):
            """
            Return the value of an environment variable or a configuration key.
            If neither is set raise a ValueError.
            """
            if env in os.environ:
                return os.environ[env]

            val = config
            for path in config_path.split('.'):
                if not isinstance(val, dict) or path not in val:
                    raise ValueError(f"Neither environment variable '{env}' nor configuration key '{config_path}' is set.")
                val = val[path]

            if val is None:
                raise ValueError(f"Neither environment variable '{env}' nor configuration key '{config_path}' is set.")
            return val

        def load_fmx_conn_params(config: dict) -> dict:
            """
            Load connection params from YAML and inject password from ENV.
            """
            if os.getenv("FMX_PASSWORD") is None:
                raise ValueError("FMX_PASSWORD environment variable is not set.")

            return {
                "database": env_or_config("FMX_DATABASE", "fmx.database", config),
                "user":  env_or_config("FMX_USER", "fmx.user", config),
                "host": env_or_config("FMX_HOST", "fmx.host", config),
                "port": int(env_or_config("FMX_PORT", "fmx.port", config)),
                "password": os.getenv("FMX_PASSWORD")
            }
        
        sql = """
        select 
          di.tags
        from (select study_instance_uid from dicom.dicom_studies order by random() limit 1) ds
        join dicom.dicom_instances di on di.study_instance_uid = ds.study_instance_uid;
        """

        with psycopg2.connect(**load_fmx_conn_params({})) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql)

                instances = [pydicom.Dataset.from_json(row['tags']) for row in cur.fetchall()]
                study = dicom2fhir.process_dicom_2_fhir(instances)

                print(study)

                self.assertIsNotNone(study, "No ImagingStudy was generated")
                self.assertIsNotNone(study.series, "Series was not built for the study")
                self.assertIsNotNone(study.series[0].instance[0].sopClass, "SOP Class is missing")
                self.assertEqual(study.series[0].instance[0].sopClass.system, "urn:ietf:rfc:3986", "SOP Class system is incorrect")
                