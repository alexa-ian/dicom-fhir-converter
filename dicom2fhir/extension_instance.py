from dicom2fhir import dicom2fhirutils

def gen_extension(ds):

    ex_list = []

    try:
        extension_instance = dicom2fhirutils.gen_extension(
            url="https://www.medizininformatik-initiative.de/fhir/ext/modul-bildgebung/StructureDefinition/mii-ex-bildgebung-instanz-details"
            )
    except Exception:
        pass

    try: 
        pixelSpacingX = ds[0x0028, 0x0030].value[0]
        pixelSpacingY = ds[0x0028, 0x0030].value[1]
    except Exception:
        pass
    
    #pixelSpacing(x)
    try:
        extension_pixelSpacingX = dicom2fhirutils.gen_extension(
            url="pixelSpacing(x)"
            )
    except Exception:
        pass
    try:
        dicom2fhirutils.add_extension_value(
            e = extension_pixelSpacingX,
            url = "pixelSpacing(x)",
            value= pixelSpacingX,
            system= "http://unitsofmeasure.org",
            unit= "millimeter",
            type="quantity"
        )
        ex_list.append(extension_pixelSpacingX)
    except Exception:
        pass

    #pixelSpacing(y)
    try:
        extension_pixelSpacingY = dicom2fhirutils.gen_extension(
            url="pixelSpacing(y)"
            )
    except Exception:
        pass
    try:
        dicom2fhirutils.add_extension_value(
            e = extension_pixelSpacingY,
            url = "pixelSpacing(y)",
            value= pixelSpacingY,
            system= "http://unitsofmeasure.org",
            unit= "millimeter",
            type="quantity"
        )
        ex_list.append(extension_pixelSpacingY)
    except Exception:
        pass

    #sliceThickness
    try:
        extension_sliceThickness = dicom2fhirutils.gen_extension(
            url="sliceThickness"
            )
    except Exception:
        pass
    try:
        dicom2fhirutils.add_extension_value(
            e = extension_sliceThickness,
            url = "sliceThickness",
            value= ds[0x0018, 0x0050].value,
            system= "http://unitsofmeasure.org",
            unit= "millimeter",
            type="quantity"
        )
        ex_list.append(extension_sliceThickness)
    except Exception:
        pass

    #imageType
    try:
        extension_imageType = dicom2fhirutils.gen_extension(
            url="imageType"
            )
    except Exception:
        pass
    try:
        dicom2fhirutils.add_extension_value(
            e = extension_imageType,
            url = "imageType",
            value= str(ds[0x0008, 0x0008].value),
            system= None,
            unit= None,
            type="string"
        )
        ex_list.append(extension_imageType)
    except Exception:
        pass

    extension_instance.extension = ex_list

    return extension_instance