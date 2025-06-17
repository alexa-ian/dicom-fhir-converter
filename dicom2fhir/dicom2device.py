# dicom2device.py

import uuid
from collections.abc import Iterable
from pydicom.dataset import Dataset
from fhir.resources.R4B.device import Device

def _map_software_versions(ds: Dataset) -> list[dict]:
    """
    Extract SoftwareVersions (DICOM 0018,1020) from the dataset and map to FHIR Device.version.
    
    This attribute is multi-valued (LO), so it returns a list of version strings.
    """
    # pydicom returns either a single value or a MultiValue object for VR LO
    raw = ds.get("SoftwareVersions", None)
    if not raw:
        return []

    # Normalize to list of strings
    if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
        return [{'value': str(item).strip()} for item in raw if item is not None]
    else:
        return [{'value': str(raw).strip()}]

def build_device_resource(ds: Dataset, config: dict) -> Device:
    """
    Build FHIR Device resource from DICOM metadata (General Equipment Module).
    Extracts manufacturer, model, serial, version, institution, station, calibration, UDI, etc.
    """

    device = Device.model_construct()
    # Resource ID
    id_func = config.get("id_function", lambda t, d: str(uuid.uuid4()))
    device.id = id_func("Device", ds)

    # Identifiers
    identifiers = []
    for tag_name, system in [
        ("DeviceSerialNumber", "urn:dicom:device-serial-number"),
        ("DeviceUID", "urn:dicom:device-uid"),
    ]:
        val = ds.get(tag_name)
        if val:
            identifiers.append({"use": "official", "system": system, "value": val})
    if identifiers:
        device.identifier = identifiers

    # Manufacturer & Model
    if (m := ds.get("Manufacturer")):
        device.manufacturer = m
    if (name := ds.get("ManufacturerModelName")):
        device.deviceName = [{"name": name, "type": "model-name"}]

    # Software version(s)
    device.version = _map_software_versions(ds)

    # Institutional context
    for field, tag in [
        ("manufacturer", "Manufacturer"),
        ("owner", ds.get("InstitutionName")),
    ]:
        pass  # Use owner assignment below
    if (inst := ds.get("InstitutionName")):
        device.owner = {"display": inst}
    if (dept := ds.get("InstitutionalDepartmentName")):
        device.location = {"display": dept}
    if (station := ds.get("StationName")):
        # Could be assigned to device.deviceName as 'station' or use part of location
        device.deviceName = device.deviceName or []
        device.deviceName.append({"name": station, "type": "station-name"})

    # Physical/device-specific details
    if (spat := ds.get("SpatialResolution")):
        device.property = device.property or []
        device.property.append({
            "type": {"text": "spatial-resolution-mm"},
            "valueQuantity": {"value": float(spat), "unit": "mm"}
        })

    # Calibration date/time
    cal_date = ds.get("DateOfLastCalibration")
    cal_time = ds.get("TimeOfLastCalibration")
    if cal_date or cal_time:
        dt = cal_date + (cal_time or "")
        device.note = device.note or []
        device.note.append({"text": f"Last calibration: {dt}"})

    # Pixel padding—maybe not core but included
    if (pad := ds.get("PixelPaddingValue")):
        device.note = device.note or []
        device.note.append({"text": f"Pixel padding value: {pad}"})

    # UDI (Unique Device Identifier)
    if hasattr(ds, "UDISequence"):
        udi_items = []
        for item in ds.UDISequence:
            if (code := ds.get("DeviceIdentifier")):
                udi_items.append({"system": "http://hl7.org/fhir/sid/udi", "value": code})
        if udi_items:
            device.udiCarrier = udi_items

    # Modality as device type
    if (mod := ds.get("Modality")):
        device.type = {"text": mod}

    return device