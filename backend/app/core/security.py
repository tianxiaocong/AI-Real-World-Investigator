import ipaddress
import socket
import re
from urllib.parse import urlparse
from typing import Tuple
from app.models.schemas import SourceType

# Restricted IP ranges (SSRF defense covering IPv4, IPv6, CGNAT, Link-Local & Cloud Metadata)
RESTRICTED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),       # CGNAT (RFC 6598)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / AWS/GCP/Azure Metadata
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    ipaddress.ip_network("100::/64"),           # Discard prefix
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
]

def _is_ip_restricted(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address falls into any restricted private, loopback, or metadata networks."""
    # Built-in properties check
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        return True

    # If IPv6 mapped IPv4 (e.g. ::ffff:127.0.0.1)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        if _is_ip_restricted(ip_obj.ipv4_mapped):
            return True

    # Explicit subnet range check
    for net in RESTRICTED_IP_NETWORKS:
        if ip_obj in net:
            return True
    return False

def is_safe_url(url: str) -> bool:
    """
    Validate that a URL does not target local/private networks, cloud metadata,
    or internal services via IPv4/IPv6 resolution.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
            
        hostname_clean = hostname.strip().lower()

        # Reject literal localhost or known metadata keywords
        if hostname_clean in ("localhost", "instance-data", "metadata.google.internal"):
            return False

        # Attempt direct IP parse first (if hostname is an IP string)
        try:
            ip_obj = ipaddress.ip_address(hostname_clean)
            if _is_ip_restricted(ip_obj):
                return False
        except ValueError:
            pass

        # Resolve all addresses (IPv4 & IPv6) via getaddrinfo
        try:
            addr_info_list = socket.getaddrinfo(hostname_clean, None)
            if not addr_info_list:
                return False
            for addr_info in addr_info_list:
                sockaddr = addr_info[4]
                ip_str = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip_str)
                if _is_ip_restricted(ip_obj):
                    return False
        except Exception:
            # If resolution fails, reject to prevent DNS rebinding or malicious targets
            return False

        return True
    except Exception:
        return False

def _is_domain_or_subdomain(domain: str, target: str) -> bool:
    """Strictly matches exact domain or subdomain suffix to prevent domain spoofing (e.g. sec.gov.attacker.com)."""
    target = target.strip().lower()
    domain = domain.strip().lower()
    return domain == target or domain.endswith("." + target)

def classify_source_and_credibility(url: str, domain: str) -> Tuple[SourceType, float]:
    """Calculate heuristic credibility score and SourceType from domain/url structure with anti-spoofing."""
    domain = domain.lower().strip()
    
    # Government / Official regulatory
    if domain.endswith(".gov") or domain.endswith(".gov.cn") or _is_domain_or_subdomain(domain, "sec.gov") or _is_domain_or_subdomain(domain, "csrc.gov.cn"):
        return SourceType.GOVERNMENT, 0.95
        
    # Academic & Research institutions
    academic_exact = ["arxiv.org", "nature.com", "science.org", "cell.com", "nejm.org", "thelancet.com", "biorxiv.org", "medrxiv.org"]
    if domain.endswith(".edu") or domain.endswith(".ac.uk") or domain.endswith(".edu.cn") or any(_is_domain_or_subdomain(domain, acad) for acad in academic_exact):
        return SourceType.ACADEMIC, 0.90
        
    # Top Tier Financial & Global News
    major_news = [
        "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "cnbc.com", 
        "nytimes.com", "bbc.com", "bbc.co.uk", "techcrunch.com", "theverge.com",
        "caixin.com", "36kr.com", "huxiu.com", "yicai.com", "xinhuanet.com",
        "apnews.com", "afp.com", "theguardian.com", "forbes.com"
    ]
    if any(_is_domain_or_subdomain(domain, news_domain) for news_domain in major_news):
        return SourceType.NEWS, 0.85
        
    # Official business registry databases / filings / health registries
    major_dbs = ["crunchbase.com", "pitchbook.com", "qcc.com", "tianyancha.com", "opencorporates.com", "fda.gov", "who.int", "clinicaltrials.gov"]
    if any(_is_domain_or_subdomain(domain, db) for db in major_dbs):
        return SourceType.DATABASE, 0.88
        
    # Reddit & Forums
    if _is_domain_or_subdomain(domain, "reddit.com"):
        return SourceType.REDDIT, 0.45
    major_forums = ["zhihu.com", "tieba.baidu.com", "v2ex.com", "news.ycombinator.com"]
    if any(_is_domain_or_subdomain(domain, f) for f in major_forums):
        return SourceType.FORUM, 0.50
        
    # Social Media
    major_social = ["x.com", "twitter.com", "linkedin.com", "weibo.com", "facebook.com", "instagram.com"]
    if any(_is_domain_or_subdomain(domain, sm) for sm in major_social):
        return SourceType.SOCIAL_MEDIA, 0.40
        
    # Blogs & Substack
    major_blogs = ["medium.com", "substack.com"]
    if any(_is_domain_or_subdomain(domain, b) for b in major_blogs):
        return SourceType.BLOG, 0.55
        
    return SourceType.OTHER, 0.60

def wrap_untrusted_content(content: str) -> str:
    """Isolate untrusted scraped text with boundary markers to prevent indirect prompt injection"""
    clean_text = content.replace("\x00", "")
    return f"<untrusted_source_content>\n{clean_text}\n</untrusted_source_content>"
