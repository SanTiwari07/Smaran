import pytest

from backend.common.pii import find_pii, redact


@pytest.mark.parametrize("text,rule", [
    ("Call Ravi on 9876543210 about night shift", "phone_in"),
    ("call +91 98765 43210 tomorrow", "phone_in"),
    ("mail priya.k@plant.example.com", "email"),
    ("aadhaar 1234 5678 9012 for gate pass", "aadhaar"),
    ("PAN ABCDE1234F", "pan"),
])
def test_detects(text, rule):
    assert rule in find_pii(text)


@pytest.mark.parametrize("text", [
    "CNC-07 bearing replaced, vibration normal",
    "Spindle at 12000 RPM, temp 68 C, torque 45 Nm",
    "Replaced filter part 4410-22 on LATHE-03",
    "ROBOT-ARM-5 axis 3 encoder drift 0.02 mm",
])
def test_no_false_positive_on_machine_text(text):
    assert find_pii(text) == []


def test_redact():
    assert "9876543210" not in redact("ring 9876543210")
