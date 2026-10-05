from datetime import date, datetime, time
import math

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS


def distance_in_meters(lat1, lon1, lat2, lon2):
    earth_radius_m = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_m * c


def rational_to_float(value):
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return value.numerator / value.denominator
    return float(value)


def dms_to_decimal(dms, ref):
    degrees, minutes, seconds = dms
    decimal = (
        rational_to_float(degrees)
        + (rational_to_float(minutes) / 60)
        + (rational_to_float(seconds) / 3600)
    )

    if ref in ["S", "W"]:
        decimal = -decimal

    return decimal


def readable_gps_info(gps_info):
    return {
        GPSTAGS.get(key, key): value
        for key, value in gps_info.items()
    }


def process_attendance(image_path, reference_latitude, reference_longitude, radius_meters):
    with Image.open(image_path) as image:
        exif_data = image._getexif()

    if exif_data is None:
        return "REJECTED", "No EXIF data found"

    exif_readable = {
        TAGS.get(key, key): value
        for key, value in exif_data.items()
    }

    exif_datetime_str = exif_readable.get("DateTimeOriginal")

    if not exif_datetime_str:
        return "REJECTED", "No EXIF DateTime"

    exif_datetime = datetime.strptime(exif_datetime_str, "%Y:%m:%d %H:%M:%S")

    if exif_datetime.date() > date.today():
        return "REJECTED", "Future date detected"

    if exif_datetime.date() != date.today():
        return "REJECTED", "Photo not from today"

    if "GPSInfo" not in exif_readable:
        return "REJECTED", "No GPS data"

    gps = readable_gps_info(exif_readable["GPSInfo"])

    required_gps_fields = ["GPSLatitude", "GPSLatitudeRef", "GPSLongitude", "GPSLongitudeRef"]
    if any(field not in gps for field in required_gps_fields):
        return "REJECTED", "Incomplete GPS data"

    lat = dms_to_decimal(gps["GPSLatitude"], gps["GPSLatitudeRef"])
    lon = dms_to_decimal(gps["GPSLongitude"], gps["GPSLongitudeRef"])

    dist = distance_in_meters(lat, lon, reference_latitude, reference_longitude)

    if dist > radius_meters:
        return "REJECTED", "Outside attendance location radius"

    if exif_datetime.time() > time(9, 0):
        return "LATE", "Arrived after 9:00 AM"

    return "PRESENT", "On time and within location"