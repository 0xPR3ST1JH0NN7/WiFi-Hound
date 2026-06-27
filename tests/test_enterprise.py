"""Tests for WPA2-Enterprise support: parsers, guardrails, routes, graph flag.

The external tools (EAP_buster.sh, tshark, pcapFilter.sh) are never invoked:
the pure parsers run on synthetic input and the runners are exercised through
``dry_run`` / monkeypatched guardrails, mirroring the deauth tests.
"""

import datetime
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import wifihound.operations.base as base
import wifihound.operations.enterprise as ent
from wifihound.graph import WifiGraph
from wifihound.models import AccessPoint, Scan
from wifihound.operations.base import OperationError, OperationNotAuthorized
from wifihound.server import create_app


def client():
    return TestClient(create_app())


# --------------------------------------------------------------- cert fixtures
def _der_cert(cn, issuer_cn=None, serial=0x1234ABCD):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    issuer = (subject if issuer_cn is None
              else x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_cn)]))
    cert = (x509.CertificateBuilder()
            .subject_name(subject).issuer_name(issuer)
            .public_key(key.public_key()).serial_number(serial)
            .not_valid_before(datetime.datetime(2026, 1, 1))
            .not_valid_after(datetime.datetime(2027, 1, 1))
            .sign(key, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.DER)


# ------------------------------------------------------------- EAP parser
def test_parse_eap_buster_basic():
    out = (
        "EAP_buster by BlackArrow\n"
        "\rchecking EAP-TLS ...\r\x1b[K\x1b[0;32msupported    \x1b[0m =>  EAP-TLS\n"
        "\rchecking EAP-PEAP_GTC ...\r\x1b[K\x1b[0;31mnot supported\x1b[0m =>  EAP-PEAP_GTC\n"
    )
    res = ent.parse_eap_buster(out)
    by = {r["method"]: r["supported"] for r in res}
    assert by["EAP-TLS"] == "yes"
    assert by["EAP-PEAP_GTC"] == "no"            # "not supported" not misread as yes
    # untested declared methods are synthesised as "maybe"
    assert by["EAP-PEAP_MSCHAPv2"] == "maybe"
    assert all(r["supported"] in ("yes", "no", "maybe") for r in res)


def test_parse_eap_buster_no_maybe():
    out = "supported     =>  EAP-TLS\n"
    res = ent.parse_eap_buster(out, mark_untested_as_maybe=False)
    assert res == [{"method": "EAP-TLS", "supported": "yes"}]


def test_parse_eap_buster_ignores_noise_and_dedups():
    out = (
        "banner line, not a verdict\n"
        "checking EAP-TLS support ...\n"
        "supported     =>  EAP-TLS\n"
        "not supported =>  EAP-TLS\n"     # duplicate -> first verdict wins
    )
    res = ent.parse_eap_buster(out, mark_untested_as_maybe=False)
    assert res == [{"method": "EAP-TLS", "supported": "yes"}]


# ----------------------------------------------------------- cert parsers
def test_parse_certificates_from_der_leaf_first():
    leaf = _der_cert("radius.example.com", issuer_cn="Example CA")
    ca = _der_cert("Example CA")  # self-signed (subject == issuer)
    certs = ent.parse_certificates_from_der_list([ca, leaf])
    assert "radius.example.com" in certs[0]["subject"]   # leaf sorted first
    assert certs[0]["issuer"] != certs[0]["subject"]
    assert certs[0]["serial"] == format(0x1234ABCD, "x")
    assert certs[0]["not_before"].startswith("2026-01-01")


def test_hexfields_to_der_roundtrip_and_garbage():
    der = _der_cert("radius.example.com", issuer_cn="CA")
    colon_hex = ":".join(f"{b:02x}" for b in der)
    # two certs comma-joined on one line, plus a junk token
    field = f"{colon_hex},{colon_hex}\nzz:zz"
    ders = ent.hexfields_to_der(field)
    assert len(ders) == 2 and all(d == der for d in ders)
    assert ent.parse_certificates_from_der_list(ders)[0]["subject"]


def test_parse_certificates_from_pem_text():
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    pem = "\n".join(
        x509.load_der_x509_certificate(_der_cert(cn, issuer_cn="CA"))
        .public_bytes(serialization.Encoding.PEM).decode()
        for cn in ("a.example.com", "b.example.com"))
    certs = ent.parse_certificates_from_pem_text(pem)
    assert len(certs) == 2


# ------------------------------------------------------ cert runner (no root)
def test_extract_cert_missing_file():
    with pytest.raises(OperationError):
        ent.extract_radius_cert("/no/such/file.cap")


def test_extract_cert_dry_run_uses_tshark(monkeypatch, tmp_path):
    cap = tmp_path / "x.cap"
    cap.write_bytes(b"\x00")
    monkeypatch.setattr(ent.shutil, "which", lambda name: None)  # no pcapFilter.sh
    monkeypatch.setattr(ent, "require_tools", lambda *a, **k: None)
    res = ent.extract_radius_cert(str(cap), ap_bssid="AA:BB:CC:00:11:22",
                                  dry_run=True)
    assert res["status"] == "dry-run" and res["backend"] == "tshark"
    assert "tls.handshake.type == 11 && wlan.sa == AA:BB:CC:00:11:22" in res["command"]


def test_extract_cert_invalid_bssid(monkeypatch, tmp_path):
    cap = tmp_path / "x.cap"
    cap.write_bytes(b"\x00")
    with pytest.raises(OperationError):
        ent.extract_radius_cert(str(cap), ap_bssid="not-a-mac", dry_run=True)


# --------------------------------------------------- EAP runner (root + ack)
def test_eap_blocked_without_root(monkeypatch):
    monkeypatch.setattr(base, "_is_root", lambda: False)
    with pytest.raises(OperationNotAuthorized):
        ent.enumerate_eap_methods("wlan0", "CorpWiFi", "DOMAIN\\u", acknowledged=True)


def test_eap_dry_run(monkeypatch):
    monkeypatch.setattr(base, "_is_root", lambda: True)
    monkeypatch.setattr(ent, "require_tools", lambda *a, **k: None)
    res = ent.enumerate_eap_methods("wlan0", "CorpWiFi", "DOMAIN\\jdoe",
                                    acknowledged=True, dry_run=True)
    assert res["status"] == "dry-run"
    assert res["command"] == ["EAP_buster.sh", "CorpWiFi", "DOMAIN\\jdoe", "wlan0"]


def test_eap_rejects_bad_identity(monkeypatch):
    monkeypatch.setattr(base, "_is_root", lambda: True)
    monkeypatch.setattr(ent, "require_tools", lambda *a, **k: None)
    for bad in ("", "with\x01control"):
        with pytest.raises(OperationError):
            ent.enumerate_eap_methods("wlan0", "CorpWiFi", bad,
                                      acknowledged=True, dry_run=True)


# ------------------------------------------------------------- graph flag
def test_graph_marks_enterprise_aps():
    scan = Scan(access_points=[
        AccessPoint(bssid="AA:BB:CC:00:11:22", essid="CorpWiFi",
                    privacy="WPA2", authentication="MGT"),
        AccessPoint(bssid="DC:A6:32:11:22:33", essid="HomeNet",
                    privacy="WPA2", authentication="PSK"),
    ])
    g = WifiGraph()
    g.load(scan)
    flags = {n["data"]["id"]: n["data"]["enterprise"]
             for n in g.to_cytoscape()["elements"]["nodes"]}
    assert flags["AA:BB:CC:00:11:22"] is True
    assert flags["DC:A6:32:11:22:33"] is False
    assert g.node("AA:BB:CC:00:11:22")["enterprise"] is True


# ---------------------------------------------------------------- API routes
def test_cert_route_needs_capture():
    assert client().post("/api/operations/enterprise/cert", json={}).status_code == 400


def test_cert_route_dry_run(monkeypatch, tmp_path):
    from wifihound.api import routes
    cap = tmp_path / "c.cap"; cap.write_bytes(b"\x00")
    monkeypatch.setattr(routes.enterprise.shutil, "which", lambda name: None)
    monkeypatch.setattr(routes.enterprise, "require_tools", lambda *a, **k: None)
    res = client().post("/api/operations/enterprise/cert",
                        json={"cap_path": str(cap), "dry_run": True})
    assert res.status_code == 200 and res.json()["backend"] == "tshark"


def test_eap_route_requires_interface():
    res = client().post("/api/operations/enterprise/eap-methods",
                        json={"essid": "X", "identity": "u"})
    assert res.status_code == 400


def test_eap_route_blocked_without_root(monkeypatch):
    monkeypatch.setattr(base, "_is_root", lambda: False)
    res = client().post("/api/operations/enterprise/eap-methods",
                        json={"essid": "X", "identity": "u", "interface": "wlan0",
                              "acknowledged": True})
    assert res.status_code == 403


def test_eap_route_dry_run(monkeypatch):
    from wifihound.api import routes
    monkeypatch.setattr(base, "_is_root", lambda: True)
    monkeypatch.setattr(routes.enterprise, "require_tools", lambda *a, **k: None)
    res = client().post("/api/operations/enterprise/eap-methods",
                        json={"essid": "CorpWiFi", "identity": "DOMAIN\\jdoe",
                              "interface": "wlan0", "acknowledged": True,
                              "dry_run": True})
    assert res.status_code == 200
    assert res.json()["command"][0] == "EAP_buster.sh"


def test_eap_route_single_flight(monkeypatch):
    from wifihound.api import routes
    routes._EAP_LOCK.acquire()
    try:
        res = client().post("/api/operations/enterprise/eap-methods",
                            json={"essid": "X", "identity": "u",
                                  "interface": "wlan0", "acknowledged": True})
        assert res.status_code == 409
    finally:
        routes._EAP_LOCK.release()
