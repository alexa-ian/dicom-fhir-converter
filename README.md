# dicom-fhir-converter
DICOM FHIR converter is an open source python library that accepts a DICOM directory as an input.
It processes all files (instances) within that directory. It expects that directory will only contain files for a single study.
If multiple studies detected, an exception is raised. 
Using the usual convention, if file cannot be read, it will be skipped assuming it is not a dicom file (no error raised).

This library utilizes the following projects:
- fhir.resources project (https://pypi.org/project/fhir.resources/) - used to create FHIR models
- pydicom (https://pydicom.github.io/) - used to read dicom instances

The library does not rely on the terminology service therefore, any coding that requires a look-up were coded with ```"userSelected=True"``` values.

## Usage

```python
dicom2fhir.process_dicom_2_fhir("study directory")
```

The dicom file represents a single instance within DICOM study. A study is a collection of instances grouped by series.
The assumption is that all instances are copied into a single folder prior to calling this function. The flattened structure is then consolidated into a single FHIR Imaging Study resource.

If you need to update the bodysite Snomed mappings run:

```bash
cd dicom2fhir 
./build_terminologies.py
```

Activate tests against Firemetrics:
```bash
export RUN_FMX_TESTS=1
```

## Structure 
The FHIR Imaging Study id is being generated internally within the library. 
The DICOM Study UID is actually stored as part of the "identifier" (see ```"system":"urn:dicom:uid"``` object for DICOM study uid.

The model is meant to be self-inclusive (to mimic the DICOM structure), it does not produce separate resources for other resource types.
Instead, it uses "contained" resource to include all of the supporting data. (See "subject" with ```"reference": "#patient.contained.inline"```

This approach will allow downstream systems to map inline resources to new or existing FHIR resource types replacing inline references to actual object within FHIR Server.
Until such time, all of the a data is included within a single resource.

### Sample Output
```
{
  "resourceType": "Bundle",
  "id": "f87746a0-7ff5-4666-8302-423cfdf3f275",
  "type": "transaction",
  "entry": [
    {
      "fullUrl": "urn:uuid:7423de5ec8508bb1dc9036a7478d7bd4940a6c5daf5751d8ad2ca13f1dae85d0",
      "resource": {
        "resourceType": "ImagingStudy",
        "id": "7423de5ec8508bb1dc9036a7478d7bd4940a6c5daf5751d8ad2ca13f1dae85d0",
        "identifier": [
          {
            "use": "usual",
            "type": {
              "coding": [
                {
                  "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                  "code": "ACSN"
                }
              ]
            },
            "value": "62541999"
          },
          {
            "system": "urn:dicom:uid",
            "value": "urn:oid:1.2.840.113711.9425041.6.7312.599853596.26.2116281012.165600"
          }
        ],
        "status": "available",
        "modality": [
          {
            "system": "http://dicom.nema.org/resources/ontology/DCM",
            "code": "CR"
          }
        ],
        "subject": {
          "reference": "Patient/c13a8cd37541b87b256fe08a3800b5f409439357a250661efaec6a9642901d72"
        },
        "started": "2020-01-11T00:00:00",
        "numberOfSeries": 4,
        "numberOfInstances": 4,
        "procedureCode": [
          {
            "coding": [
              {
                "system": "UNKNOWN",
                "code": "7003520",
                "display": "XR Ribs w/ PA Chest Left"
              }
            ],
            "text": "XR Ribs w/ PA Chest Left"
          }
        ],
        "series": [
          {
            "uid": "1.2.840.113564.19216812.20200110232537925600",
            "number": 2,
            "modality": {
              "system": "http://dicom.nema.org/resources/ontology/DCM",
              "code": "CR"
            },
            "description": "AP",
            "numberOfInstances": 1,
            "bodySite": {
              "code": "RIBS",
              "userSelected": true
            },
            "instance": [
              {
                "uid": "1.2.840.113564.19216812.20200110232537925610.2203801020003",
                "sopClass": {
                  "system": "urn:ietf:rfc:3986",
                  "code": "urn:oid:1.2.840.10008.5.1.4.1.1.1"
                },
                "number": 1,
                "title": "DERIVED\\PRIMARY"
              }
            ]
          },
          {
            "uid": "1.2.840.113564.19216812.20200110232537987660",
            "number": 5,
            "modality": {
              "system": "http://dicom.nema.org/resources/ontology/DCM",
              "code": "CR"
            },
            "description": "RPO",
            "numberOfInstances": 1,
            "bodySite": {
              "code": "RIBS",
              "userSelected": true
            },
            "instance": [
              {
                "uid": "1.2.840.113564.19216812.20200110232537987670.2203801020003",
                "sopClass": {
                  "system": "urn:ietf:rfc:3986",
                  "code": "urn:oid:1.2.840.10008.5.1.4.1.1.1"
                },
                "number": 1,
                "title": "DERIVED\\PRIMARY"
              }
            ]
          },
          {
            "uid": "1.2.840.113564.19216812.20200110232538003680",
            "number": 6,
            "modality": {
              "system": "http://dicom.nema.org/resources/ontology/DCM",
              "code": "CR"
            },
            "description": "LPO",
            "numberOfInstances": 1,
            "bodySite": {
              "code": "RIBS",
              "userSelected": true
            },
            "instance": [
              {
                "uid": "1.2.840.113564.19216812.20200110232538003690.2203801020003",
                "sopClass": {
                  "system": "urn:ietf:rfc:3986",
                  "code": "urn:oid:1.2.840.10008.5.1.4.1.1.1"
                },
                "number": 1,
                "title": "DERIVED\\PRIMARY"
              }
            ]
          },
          {
            "uid": "1.2.840.113564.19216812.20200110232537909580",
            "number": 1,
            "modality": {
              "system": "http://dicom.nema.org/resources/ontology/DCM",
              "code": "CR"
            },
            "description": "PA",
            "numberOfInstances": 1,
            "bodySite": {
              "system": "http://snomed.info/sct",
              "code": "43799004",
              "display": "Chest"
            },
            "instance": [
              {
                "uid": "1.2.840.113564.19216812.20200110232537909590.2203801020003",
                "sopClass": {
                  "system": "urn:ietf:rfc:3986",
                  "code": "urn:oid:1.2.840.10008.5.1.4.1.1.1"
                },
                "number": 1,
                "title": "DERIVED\\PRIMARY"
              }
            ]
          }
        ]
      },
      "request": {
        "method": "PUT",
        "url": "ImagingStudy/7423de5ec8508bb1dc9036a7478d7bd4940a6c5daf5751d8ad2ca13f1dae85d0"
      }
    },
    {
      "fullUrl": "urn:uuid:c13a8cd37541b87b256fe08a3800b5f409439357a250661efaec6a9642901d72",
      "resource": {
        "resourceType": "Patient",
        "id": "c13a8cd37541b87b256fe08a3800b5f409439357a250661efaec6a9642901d72",
        "identifier": [
          {
            "use": "usual",
            "system": "urn:dicom:patient-id",
            "value": "A09650600b71bfe4043b5b44e05b362015f"
          }
        ],
        "name": [
          {
            "family": "Doe",
            "given": ["John", "A."],
            "prefix": "Dr.",
            "suffix": "MD"
          }
        ],
        "gender": "male",
        "birthDate": "1976-01-01"
      },
      "request": {
        "method": "PUT",
        "url": "Patient/c13a8cd37541b87b256fe08a3800b5f409439357a250661efaec6a9642901d72"
      }
    },
    {
      "fullUrl": "urn:uuid:5a4d77e9-04a7-4897-ad05-b80432794242",
      "resource": {
        "resourceType": "Device",
        "id": "5a4d77e9-04a7-4897-ad05-b80432794242",
        "manufacturer": "Carestream Health",
        "deviceName": [
          {
            "name": "DRX-Evolution",
            "type": "model-name"
          }
        ],
        "type": {
          "text": "CR"
        },
        "version": [
          {
            "value": "5.7.412.7005"
          }
        ]
      },
      "request": {
        "method": "PUT",
        "url": "Device/5a4d77e9-04a7-4897-ad05-b80432794242"
      }
    }
  ]
}
```

## Todo 

- [ ] Allow to pass custom function to create FHIR resource ids from business identifiers
- [ ] Add support for DICOMweb data inputs