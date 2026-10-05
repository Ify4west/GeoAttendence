# test_core.py
from attendance_core import process_attendance

status, reason = process_attendance("test_images/t1.jpg")
print(status, reason)
