import pytest
from app.core.security import is_safe_url, classify_source_and_credibility
from app.models.schemas import SourceType

def test_is_safe_url_blocks_localhost_and_private_ips():
    assert not is_safe_url("http://127.0.0.1/admin")
    assert not is_safe_url("http://localhost:8000")
    assert not is_safe_url("http://10.0.0.1/secret")
    assert not is_safe_url("http://192.168.1.1/router")
    assert not is_safe_url("http://172.16.0.5/internal")
    assert not is_safe_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe_url("http://0.0.0.0/")

def test_is_safe_url_blocks_ipv6_loopback_and_private():
    assert not is_safe_url("http://[::1]/")
    assert not is_safe_url("http://[fc00::1]/")
    assert not is_safe_url("http://[fe80::1]/")

def test_is_safe_url_allows_valid_public_web():
    assert is_safe_url("https://www.google.com/search?q=test")
    assert is_safe_url("https://www.reuters.com/world")
    assert is_safe_url("http://example.com/")

def test_classify_source_anti_spoofing():
    # Legitimate domains
    st_sec, cred_sec = classify_source_and_credibility("https://www.sec.gov/edgar", "www.sec.gov")
    assert st_sec == SourceType.GOVERNMENT
    assert cred_sec == 0.95

    st_reu, cred_reu = classify_source_and_credibility("https://reuters.com/news", "reuters.com")
    assert st_reu == SourceType.NEWS
    assert cred_reu == 0.85

    # Attacker spoofed domains (e.g. sec.gov.attacker.com, reuters.com.fake.site)
    st_spoof_sec, cred_spoof_sec = classify_source_and_credibility("https://sec.gov.attacker.com", "sec.gov.attacker.com")
    assert st_spoof_sec != SourceType.GOVERNMENT
    assert cred_spoof_sec < 0.90

    st_spoof_reu, cred_spoof_reu = classify_source_and_credibility("https://reuters.com.fake.site", "reuters.com.fake.site")
    assert st_spoof_reu != SourceType.NEWS
    assert cred_spoof_reu < 0.80

    st_spoof_nat, cred_spoof_nat = classify_source_and_credibility("https://nature.com.phishing.io", "nature.com.phishing.io")
    assert st_spoof_nat != SourceType.ACADEMIC
    assert cred_spoof_nat < 0.90
