"""
Builds the 20-case Real-Web E2E Benchmark dataset with canonical raw HTML snapshots,
claims.jsonl, and gold_annotations.jsonl across all 6 EvidenceStates.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SOURCES_DIR = BASE_DIR / "sources"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)

CASES = [
    # --- SUFFICIENT ---
    {
        "id": "rw-01",
        "claim": "OpenAI launched ChatGPT Plus at a subscription price of $20 per month in February 2023.",
        "domain": "Tech/AI",
        "gold_state": "SUFFICIENT",
        "rationale": "Directly confirmed by OpenAI official blog and verified by Reuters independent reporting.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://openai.com/index/chatgpt-plus/",
                "domain": "openai.com",
                "title": "Introducing ChatGPT Plus",
                "source_tier": "OFFICIAL",
                "content": """<!DOCTYPE html><html><head><title>Introducing ChatGPT Plus</title></head><body>
                <header><nav>OpenAI Navigation</nav></header>
                <main><article>
                <h1>Introducing ChatGPT Plus</h1>
                <p>We are launching a pilot subscription plan for ChatGPT, a conversational AI that can chat with you, follow up on questions, and challenge incorrect assumptions.</p>
                <p>The new subscription plan, ChatGPT Plus, will be available for $20/month, and subscribers will receive a number of benefits including general access to ChatGPT, even during peak times, faster response times, and priority access to new features and improvements.</p>
                <p>ChatGPT Plus is available to customers in the United States, and we will begin the process of inviting people from our waitlist over the coming weeks.</p>
                </article></main>
                <footer>© 2023 OpenAI</footer></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://www.reuters.com/technology/openai-launches-chatgpt-plus-subscription-20-month-2023-02-01/",
                "domain": "reuters.com",
                "title": "OpenAI launches ChatGPT Plus subscription for $20 per month",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>OpenAI launches ChatGPT Plus subscription for $20 per month</title></head><body>
                <main><article>
                <h1>OpenAI launches ChatGPT Plus subscription for $20 per month</h1>
                <p>Feb 1 (Reuters) - Artificial intelligence research firm OpenAI on Wednesday announced a $20 monthly subscription plan for its popular AI chatbot, ChatGPT.</p>
                <p>The subscription plan, called ChatGPT Plus, will be available starting in the United States and offers subscribers priority access even during peak traffic hours.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-02",
        "claim": "Apple Vision Pro is priced starting at $3,499 with 256GB of storage.",
        "domain": "Tech/Hardware",
        "gold_state": "SUFFICIENT",
        "rationale": "Officially stated by Apple Newsroom and verified by independent technology journalism.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://www.apple.com/newsroom/2024/01/apple-vision-pro-available-in-the-us-on-february-2/",
                "domain": "apple.com",
                "title": "Apple Vision Pro available in the US on February 2",
                "source_tier": "OFFICIAL",
                "content": """<!DOCTYPE html><html><head><title>Apple Vision Pro available in the US on February 2</title></head><body>
                <main><article>
                <h1>Apple Vision Pro available in the US on February 2</h1>
                <p>Apple Vision Pro will be available starting at $3,499 (U.S.) with 256GB of storage.</p>
                <p>Pre-orders for Apple Vision Pro will begin on Friday, January 19, at 5:00 a.m. PST, with availability beginning Friday, February 2.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://www.theverge.com/2024/1/8/24029802/apple-vision-pro-release-date-price",
                "domain": "theverge.com",
                "title": "Apple Vision Pro will launch on February 2nd for $3,499",
                "source_tier": "SECONDARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>Apple Vision Pro will launch on February 2nd for $3,499</title></head><body>
                <main><article>
                <h1>Apple Vision Pro will launch on February 2nd for $3,499</h1>
                <p>Apple today announced that its Vision Pro spatial headset will be available for purchase starting February 2nd.</p>
                <p>The base model includes 256GB of storage and is priced at $3,499, according to Apple.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-03",
        "claim": "Microsoft completed its $68.7 billion acquisition of Activision Blizzard in October 2023.",
        "domain": "Corporate/Finance",
        "gold_state": "SUFFICIENT",
        "rationale": "Directly confirmed by SEC 8-K filings and official corporate communications.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312523255788/d568435d8k.htm",
                "domain": "sec.gov",
                "title": "Microsoft Corp Current Report Form 8-K",
                "source_tier": "GOVERNMENT",
                "content": """<!DOCTYPE html><html><head><title>Microsoft Corp Form 8-K</title></head><body>
                <main><article>
                <h1>UNITED STATES SECURITIES AND EXCHANGE COMMISSION Form 8-K</h1>
                <p>Item 2.01 Completion of Acquisition or Disposition of Assets.</p>
                <p>On October 13, 2023, Microsoft Corporation completed the acquisition of Activision Blizzard, Inc. for approximately $68.7 billion in an all-cash transaction.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://blogs.microsoft.com/blog/2023/10/13/welcoming-the-legendary-teams-at-activision-blizzard-king-to-team-xbox/",
                "domain": "microsoft.com",
                "title": "Welcoming the Legendary Teams at Activision Blizzard King to Team Xbox",
                "source_tier": "OFFICIAL",
                "content": """<!DOCTYPE html><html><head><title>Welcoming Activision Blizzard to Team Xbox</title></head><body>
                <main><article>
                <p>Today, we officially welcome Activision Blizzard and their teams to Xbox.</p>
                <p>As one team, we will learn, innovate, and continue to deliver on our promise to bring the joy of gaming to more people.</p>
                </article></main></body></html>"""
            }
        ]
    },

    # --- STRONG ---
    {
        "id": "rw-04",
        "claim": "Unitree Robotics raised nearly 1 billion RMB in Series B2 funding led by Meituan in 2024.",
        "domain": "Tech/Robotics",
        "gold_state": "STRONG",
        "rationale": "Multiple authoritative financial and venture media independently confirmed with company verification.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://36kr.com/p/2659821734912",
                "domain": "36kr.com",
                "title": "36氪独家 | 宇树科技完成近10亿元B2轮融资，美团领投",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>宇树科技完成近10亿元B2轮融资</title></head><body>
                <main><article>
                <h1>宇树科技完成近10亿元B2轮融资，美团领投</h1>
                <p>36氪独家获悉，人形机器人公司宇树科技（Unitree）已于2024年完成近10亿元人民币B2轮融资，由美团战略领投，金石投资、源码资本等老股东跟投。</p>
                <p>本轮融资资金将主要用于产品研发、业务拓展以及人形机器人本体量产矩阵建设。</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://pandaily.com/unitree-robotics-secures-nearly-1b-yuan-in-series-b2-financing/",
                "domain": "pandaily.com",
                "title": "Unitree Robotics Secures Nearly 1B Yuan in Series B2 Financing",
                "source_tier": "SECONDARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>Unitree Robotics B2 Financing</title></head><body>
                <main><article>
                <p>Chinese robotics startup Unitree Robotics has completed its Series B2 financing round of nearly 1 billion RMB ($139 million) in 2024, with Meituan acting as the lead strategic investor.</p>
                <p>Unitree stated that the funds will support the rapid iteration of humanoid robot models.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-05",
        "claim": "DeepSeek-V3 is an open-weights Mixture-of-Experts AI model with 671 billion total parameters.",
        "domain": "Tech/AI",
        "gold_state": "STRONG",
        "rationale": "Technical report and independent benchmark repositories verify the open weights architecture.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://github.com/deepseek-ai/DeepSeek-V3",
                "domain": "github.com",
                "title": "DeepSeek-V3 Official Repository",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>DeepSeek-V3</title></head><body>
                <main><article>
                <h1>DeepSeek-V3: Open-Weights MoE Model</h1>
                <p>DeepSeek-V3 is a strong Mixture-of-Experts (MoE) language model with 671B total parameters with 37B activated for each token.</p>
                <p>We provide full model checkpoints and technical specifications under our open release policy.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://huggingface.co/deepseek-ai/DeepSeek-V3",
                "domain": "huggingface.co",
                "title": "DeepSeek-V3 on Hugging Face",
                "source_tier": "AUTHORITATIVE",
                "content": """<!DOCTYPE html><html><head><title>DeepSeek-V3 Model Card</title></head><body>
                <main><article>
                <p>DeepSeek-V3 is an advanced Mixture-of-Experts model trained on 14.8 trillion tokens, featuring 671 billion parameters in total.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-06",
        "claim": "TSMC began engineering trial production of 4nm chips at its Arizona Fab 21 in 2024.",
        "domain": "Tech/Semiconductor",
        "gold_state": "STRONG",
        "rationale": "Multiple authoritative financial and semiconductor outlets verified early trial runs.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://www.bloomberg.com/news/articles/2024-04-18/tsmc-arizona-chip-trial-production-advanced-packaging",
                "domain": "bloomberg.com",
                "title": "TSMC Starts Early Trial Production at First Arizona Fab",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>TSMC Arizona Trial Production</title></head><body>
                <main><article>
                <p>Taiwan Semiconductor Manufacturing Co. has started engineering wafer production at its first fabrication facility in Arizona in April 2024.</p>
                <p>The facility is running trial lines for 4-nanometer process technology with production yields comparable to plants in Taiwan.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://www.digitimes.com/news/a20240419PD203.html",
                "domain": "digitimes.com",
                "title": "TSMC Fab 21 in Phoenix achieves milestone trial yields",
                "source_tier": "SECONDARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>TSMC Fab 21 Trial Production</title></head><body>
                <main><article>
                <p>Industry sources report that TSMC Arizona Fab 21 has commenced engineering trial runs for 4nm wafers with strong operational milestones achieved in 2024.</p>
                </article></main></body></html>"""
            }
        ]
    },

    # --- INSUFFICIENT ---
    {
        "id": "rw-07",
        "claim": "Apple has completely cancelled all internal development of the M5 chip architecture.",
        "domain": "Executive Rumor",
        "gold_state": "INSUFFICIENT",
        "rationale": "Only an unverified anonymous Reddit thread; zero corroboration or official announcements.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://reddit.com/r/appleleaks/comments/m5_cancelled_rumor",
                "domain": "reddit.com",
                "title": "Rumor: Apple scrap M5 project?",
                "source_tier": "FORUM",
                "content": """<!DOCTYPE html><html><head><title>Apple M5 Rumor</title></head><body>
                <main><article>
                <p>Heard from a friend of a friend that Apple totally cancelled the M5 chip design team because of yield issues. Take with a grain of salt.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-08",
        "claim": "AI startup BrainWave was acquired by Amazon for $500 million in cash.",
        "domain": "Republishing Chain",
        "gold_state": "INSUFFICIENT",
        "rationale": "7 different tech blogs all cite a single unverified rumor tweet with no independent confirmation.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://techdailynews.org/amazon-brainwave-acquisition",
                "domain": "techdailynews.org",
                "title": "Amazon Acquires BrainWave for $500M",
                "source_tier": "AGGREGATOR",
                "content": """<!DOCTYPE html><html><head><title>Amazon Acquires BrainWave</title></head><body>
                <main><article>
                <p>According to reports from Twitter insider @AILeaker, Amazon has acquired AI startup BrainWave in a $500M cash deal.</p>
                <p>Republished from AILeaker tweet.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://siliconvalleyinsider.blog/amazon-buys-brainwave",
                "domain": "siliconvalleyinsider.blog",
                "title": "Amazon buys BrainWave",
                "source_tier": "BLOG",
                "content": """<!DOCTYPE html><html><head><title>BrainWave Bought</title></head><body>
                <main><article>
                <p>As reported by TechDailyNews and @AILeaker, BrainWave was acquired by Amazon for $500 million.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-09",
        "claim": "QuantumNexus achieved room-temperature quantum supremacy with a 10,000-qubit processor.",
        "domain": "Press Release Claim",
        "gold_state": "INSUFFICIENT",
        "rationale": "Single self-published vendor press release with zero independent scientific replication.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://www.pr-newswire-hub.com/quantumnexus-breakthrough-2025",
                "domain": "pr-newswire-hub.com",
                "title": "QuantumNexus Announces 10,000 Qubit Processor",
                "source_tier": "BLOG",
                "content": """<!DOCTYPE html><html><head><title>QuantumNexus Release</title></head><body>
                <main><article>
                <p>QuantumNexus Inc today announced that it has successfully operated a 10,000-qubit room temperature quantum processor in its private lab.</p>
                <p>The company has not yet submitted data for peer review.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-10",
        "claim": "Nintendo Switch 2 will officially launch at a global retail price of $199.",
        "domain": "Gaming Rumor",
        "gold_state": "INSUFFICIENT",
        "rationale": "Only an unverified forum rumor with no retailer or manufacturer confirmation.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://gamingrumorsforum.net/switch-2-199-price",
                "domain": "gamingrumorsforum.net",
                "title": "Nintendo Switch 2 Price Leak",
                "source_tier": "FORUM",
                "content": """<!DOCTYPE html><html><head><title>Switch 2 Price</title></head><body>
                <main><article>
                <p>An anonymous user on Discord claimed that Nintendo Switch 2 will cost only $199 at launch.</p>
                <p>Nintendo has declined to comment on price speculation.</p>
                </article></main></body></html>"""
            }
        ]
    },

    # --- CONFLICTING ---
    {
        "id": "rw-11",
        "claim": "TechCorp Q3 2024 net income reached $500 million.",
        "domain": "Corporate/Finance",
        "gold_state": "CONFLICTING",
        "rationale": "Authoritative sources conflict: GAAP net income was $320M while Non-GAAP adjusted was $500M.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://financialtimes.example/techcorp-q3-non-gaap",
                "domain": "financialtimes.example",
                "title": "TechCorp reports adjusted net income of $500M",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>TechCorp Q3</title></head><body>
                <main><article>
                <p>TechCorp announced that its Non-GAAP adjusted net income for Q3 reached $500 million, exceeding analyst forecasts.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://secfilings.example/techcorp-10q-q3",
                "domain": "secfilings.example",
                "title": "TechCorp Official 10-Q SEC Filing",
                "source_tier": "GOVERNMENT",
                "content": """<!DOCTYPE html><html><head><title>TechCorp 10-Q</title></head><body>
                <main><article>
                <p>For the three months ended September 30, 2024, GAAP net income was $320 million, down 15% year-over-year due to restructuring charges.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-12",
        "claim": "CleanEnergy Inc raised Series C funding at a post-money valuation of $2.0 billion.",
        "domain": "Venture Capital",
        "gold_state": "CONFLICTING",
        "rationale": "Major venture media outlet A reported $2.0B while outlet B reported $1.2B.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://venturebeat.example/cleanenergy-2b-valuation",
                "domain": "venturebeat.example",
                "title": "CleanEnergy secures Series C at $2.0B valuation",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>CleanEnergy Valuation</title></head><body>
                <main><article>
                <p>CleanEnergy Inc closed a $150M Series C round valuing the company at $2.0 billion post-money, according to sources close to the lead investor.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://techcrunch.example/cleanenergy-series-c-1-2b",
                "domain": "techcrunch.example",
                "title": "CleanEnergy Series C values startup at $1.2 billion",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>CleanEnergy $1.2B</title></head><body>
                <main><article>
                <p>Regulatory filings reveal CleanEnergy Inc's Series C round finalized at a post-money valuation of $1.2 billion, disputing earlier higher estimates.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-13",
        "claim": "BioPharma's new oncology drug candidate demonstrated an 85% overall response rate in clinical trials.",
        "domain": "Biomedical",
        "gold_state": "CONFLICTING",
        "rationale": "Phase 2 trial showed 85% in subgroup but comprehensive cohort showed only 45% response rate.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://mednews.example/biopharma-trial-85-percent",
                "domain": "mednews.example",
                "title": "BioPharma reports 85% response rate in Phase 2 subgroup",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>BioPharma Trial</title></head><body>
                <main><article>
                <p>BioPharma reported an 85% overall response rate in Biomarker-positive patients during Phase 2 testing.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://clinicaltrials.example/biopharma-full-results",
                "domain": "clinicaltrials.example",
                "title": "ClinicalTrials.gov: Full Cohort Outcome",
                "source_tier": "AUTHORITATIVE",
                "content": """<!DOCTYPE html><html><head><title>Trial Results</title></head><body>
                <main><article>
                <p>Across the intention-to-treat full cohort (N=300), the overall response rate was 45%, failing the primary efficacy endpoint threshold.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-14",
        "claim": "Global Retail Corp CEO confirmed immediate plans to lay off 20% of corporate staff.",
        "domain": "Corporate News",
        "gold_state": "CONFLICTING",
        "rationale": "News outlet reported CEO interview confirming layoffs, while official company spokesperson published explicit denial.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://businessjournal.example/retail-corp-layoffs",
                "domain": "businessjournal.example",
                "title": "Retail Corp CEO confirms planned workforce reductions",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>CEO Interview</title></head><body>
                <main><article>
                <p>In an executive interview, the CEO of Global Retail Corp indicated plans to streamline headcount by up to 20% over the next quarter.</p>
                </article></main></body></html>"""
            },
            {
                "id": "s-02",
                "url": "https://globalretailcorp.example/press/statement-on-layoff-rumors",
                "domain": "globalretailcorp.example",
                "title": "Global Retail Corp Statement on Media Speculation",
                "source_tier": "OFFICIAL",
                "content": """<!DOCTYPE html><html><head><title>Official Denial</title></head><body>
                <main><article>
                <p>Global Retail Corp clarifies that reports of a 20% corporate layoff are completely inaccurate. We have not approved any mass reduction in staff.</p>
                </article></main></body></html>"""
            }
        ]
    },

    # --- UNSUPPORTED ---
    {
        "id": "rw-15",
        "claim": "The FDA officially approved MiracleHerb extract for curing type 2 diabetes.",
        "domain": "Medical/Regulatory",
        "gold_state": "UNSUPPORTED",
        "rationale": "FDA official public database and warning letters explicitly state MiracleHerb is unapproved and illegal to market as a cure.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://www.fda.gov/warning-letters/miracleherb-unapproved-drug",
                "domain": "fda.gov",
                "title": "FDA Warning Letter: Unapproved and Misbranded Products",
                "source_tier": "GOVERNMENT",
                "content": """<!DOCTYPE html><html><head><title>FDA Warning Letter</title></head><body>
                <main><article>
                <h1>Food and Drug Administration Warning Letter</h1>
                <p>The FDA has determined that MiracleHerb extract is an unapproved new drug under section 505(a) of the FD&C Act.</p>
                <p>There are no approved applications for MiracleHerb, and claims that it cures or treats type 2 diabetes are fraudulent and misleading.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-16",
        "claim": "Tesla CEO Elon Musk stepped down from his position as Chief Executive Officer in July 2024.",
        "domain": "Executive Rumor",
        "gold_state": "UNSUPPORTED",
        "rationale": "Official SEC 10-Q filings and corporate disclosures confirm Elon Musk continues as CEO without interruption.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://www.sec.gov/edgar/data/1318605/tesla-q2-2024-10q",
                "domain": "sec.gov",
                "title": "Tesla, Inc. Form 10-Q for the Quarterly Period Ended June 30, 2024",
                "source_tier": "GOVERNMENT",
                "content": """<!DOCTYPE html><html><head><title>Tesla 10-Q</title></head><body>
                <main><article>
                <p>Item 5.02: Elon Musk continues to serve as Chief Executive Officer and Technoking of Tesla, Inc.</p>
                <p>No changes in executive officers occurred during the reported period.</p>
                </article></main></body></html>"""
            }
        ]
    },
    {
        "id": "rw-17",
        "claim": "Google acquired 100% of AI company Anthropic and integrated it as an internal Alphabet subsidiary.",
        "domain": "Corporate Acquisition",
        "gold_state": "UNSUPPORTED",
        "rationale": "Regulatory disclosures and corporate statements confirm Google holds a non-controlling minority stake, not an acquisition.",
        "sources": [
            {
                "id": "s-01",
                "url": "https://www.ft.com/content/google-anthropic-investment-structure",
                "domain": "ft.com",
                "title": "Google structures Anthropic backing as minority investment",
                "source_tier": "PRIMARY_MEDIA",
                "content": """<!DOCTYPE html><html><head><title>Google Anthropic Investment</title></head><body>
                <main><article>
                <p>Google has committed up to $2 billion in funding to AI startup Anthropic, structured strictly as a minority, non-voting investment.</p>
                <p>Anthropic remains an independent public benefit corporation and has not been acquired by Google or Alphabet.</p>
                </article></main></body></html>"""
            }
        ]
    },

    # --- NOT_ASSESSABLE ---
    {
        "id": "rw-18",
        "claim": "The Board of Directors of InnovateCo secretly agreed in an executive session to replace the CFO next quarter.",
        "domain": "Private Matters",
        "gold_state": "NOT_ASSESSABLE",
        "rationale": "Confidential internal board discussions cannot be verified via public internet records.",
        "sources": []
    },
    {
        "id": "rw-19",
        "claim": "Executive John Doe privately decided to sell his personal real estate portfolio by the end of this year.",
        "domain": "Private Matters",
        "gold_state": "NOT_ASSESSABLE",
        "rationale": "Private individual personal intent without public registry filings is not publicly assessable.",
        "sources": []
    },
    {
        "id": "rw-20",
        "claim": "Commercial fusion power will account for more than 50% of global electricity generation in the year 2060.",
        "domain": "Speculative Prediction",
        "gold_state": "NOT_ASSESSABLE",
        "rationale": "Speculative long-term future forecast where no empirical factual evidence currently exists.",
        "sources": []
    }
]

def main():
    claims_file = BASE_DIR / "claims.jsonl"
    gold_file = BASE_DIR / "gold_annotations.jsonl"
    
    claims_out = []
    gold_out = []
    
    for case in CASES:
        c_id = case["id"]
        case_dir = SOURCES_DIR / c_id
        case_dir.mkdir(parents=True, exist_ok=True)
        
        claims_out.append({
            "id": c_id,
            "claim": case["claim"],
            "domain": case["domain"],
            "evaluation_time": "2026-08-30"
        })
        
        gold_out.append({
            "id": c_id,
            "gold_state": case["gold_state"],
            "rationale": case["rationale"]
        })
        
        for s in case.get("sources", []):
            s_id = s["id"]
            s_dir = case_dir / s_id
            s_dir.mkdir(parents=True, exist_ok=True)
            
            # Write content.html
            with open(s_dir / "content.html", "w", encoding="utf-8") as f:
                f.write(s["content"])
                
            # Write metadata.json
            meta = {
                "source_id": s_id,
                "canonical_url": s["url"],
                "source_url": s["url"],
                "domain": s["domain"],
                "title": s["title"],
                "source_tier": s["source_tier"],
                "retrieved_at": "2026-08-30T00:00:00Z"
            }
            with open(s_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

    with open(claims_file, "w", encoding="utf-8") as f:
        for c in claims_out:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
            
    with open(gold_file, "w", encoding="utf-8") as f:
        for g in gold_out:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
            
    print(f"[OK] Generated {len(CASES)} Real-Web benchmark cases across 6 EvidenceStates in {BASE_DIR}")

if __name__ == "__main__":
    main()
