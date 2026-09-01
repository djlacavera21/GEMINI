from gemini_cloner.transport import classify_serial, tag_device


def test_classify_serial():
    assert classify_serial("ABC123") == "usb"
    assert classify_serial("192.168.1.20:5555") == "wifi"


def test_tag_device():
    device = tag_device({"serial": "10.0.0.5:5555", "state": "device"})
    assert device["transport"] == "wifi"
