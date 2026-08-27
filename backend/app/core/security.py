import ipaddress
import socket
import re
from urllib.parse import urlparse
from typing import Tuple
from app.models.schemas import SourceType

# Restricted IP ranges (SSRF defense)
RESTRICTED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/GCP Metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_safe_url(url: str) -> bool:
    """Validate that a URL does not target local/private networks or cloud metadata"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # Reject literal localhost
        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "instance-data"):
            return False

        # Resolve IP and check against restricted ranges
        try:
            ip_str = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip_str)
            for net in RESTRICTED_IP_NETWORKS:
                if ip_obj in net:
                    return False
        except Exception:
            # If resolution fails, don't allow potentially malicious host
            return False

        return True
    except Exception:
        return False

def classify_source_and_credibility(url: str, domain: str) -> Tuple[SourceType, float]:
    """Calculate heuristic credibility score and SourceType from domain/url structure"""
    domain = domain.lower()
    
    # Government / Official regulatory
    if domain.endswith(".gov") or domain.endswith(".gov.cn") or "sec.gov" in domain:
        return SourceType.GOVERNMENT, 0.95
        
    # Academic & Research institutions
    if domain.endswith(".edu") or domain.endswith(".ac.uk") or "arxiv.org" in domain or "nature.com" in domain:
        return SourceType.ACADEMIC, 0.90
        
    # Top Tier Financial & Global News
    major_news = [
        "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "cnbc.com", 
        "nytimes.com", "bbc.com", "bbc.co.uk", "techcrunch.com", "theverge.com",
        "caixin.com", "36kr.com", "huxiu.com", "yicai.com", "xinhuanet.com"
    ]
    if any(news_domain in domain for news_domain in major_news):
        return SourceType.NEWS, 0.85
        
    # Official business registry databases / filings
    if any(db in domain for db in ["crunchbase.com", "pitchbook.com", "qcc.com", "tianyancha.com", "opencorporates.com"]):
        return SourceType.DATABASE, 0.88
        
    # Reddit & Forums
    if "reddit.com" in domain:
        return SourceType.REDDIT, 0.45
    if any(f in domain for f in ["zhihu.com", "tieba.baidu.com", "v2ex.com", "news.ycombinator.com", "forum"]):
        return SourceType.FORUM, 0.50
        
    # Social Media
    if any(sm in domain for sm in ["x.com", "twitter.com", "linkedin.com", "weibo.com", "facebook.com", "instagram.com"]):
        return SourceType.SOCIAL_MEDIA, 0.40
        
    # Blogs & Substack
    if any(b in domain for b in ["medium.com", "substack.com", "blog", "wp."]):
        return SourceType.BLOG, 0.55
        
    return SourceType.OTHER, 0.60

def wrap_untrusted_content(content: str) -> str:
    """Isolate untrusted scraped text with boundary markers to prevent indirect prompt injection"""
    clean_text = content.replace("\x00", "")
    return f"<untrusted_source_content>\n{clean_text}\n</untrusted_source_content>"
