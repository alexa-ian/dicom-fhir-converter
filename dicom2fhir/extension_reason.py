from dicom2fhir import dicom2fhirutils

def gen_extension(ds):

    ex_list = []

    try:
        extension_reason = dicom2fhirutils.gen_extension(
            url="https://www.medizininformatik-initiative.de/fhir/ext/modul-bildgebung/StructureDefinition/mii-ex-bildgebung-bildgebungsgrund"
            )
    except Exception:
        pass
    
    #reason
    try:
        dicom2fhirutils.add_extension_value(
            e = extension_reason,
            url = "imagingReason",
            value= ds[0x0040, 0x1002].value,
            system= None,
            unit= None,
            type="string"
        )
        ex_list.append(extension_reason)
    except Exception:
        pass

    extension_reason.extension = ex_list

    return extension_reason