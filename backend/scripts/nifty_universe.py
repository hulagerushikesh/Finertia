"""The two universes for the Nifty survival study (planning/RESEARCH-PLAN.md).

START_2011 is the Nifty 50 as it stood on 1 January 2011. It is rebuilt from
today's list by undoing every change dated after that day, using the
"Index changes" table of the NIFTY 50 article on English Wikipedia (read
3 Nov 2026), which cites NSE Indices press releases. The rebuild is
consistent: every stock it removes was present, and it ends on exactly 50.

Each row is (yahoo symbol or None, name, note). None means Yahoo no longer has
the stock: it is listed, with what happened to it, rather than dropped
quietly. The note also records where today's symbol stands for an older
company.

TODAY is the list as of the same read, the comparison universe that carries
survivorship bias on purpose.
"""

START_2011 = [
    ("ACC.NS", "ACC", ""),
    ("AMBUJACEM.NS", "Ambuja Cements", ""),
    ("AXISBANK.NS", "Axis Bank", ""),
    ("BAJAJ-AUTO.NS", "Bajaj Auto", ""),
    ("BHEL.NS", "BHEL", ""),
    ("BPCL.NS", "Bharat Petroleum", ""),
    ("BHARTIARTL.NS", "Bharti Airtel", ""),
    (None, "Cairn India", "merged into Vedanta, April 2017"),
    ("CIPLA.NS", "Cipla", ""),
    ("DLF.NS", "DLF", ""),
    ("DRREDDY.NS", "Dr. Reddy's Laboratories", ""),
    ("GAIL.NS", "GAIL", ""),
    ("HCLTECH.NS", "HCLTech", ""),
    (None, "HDFC", "merged into HDFC Bank, July 2023"),
    ("HDFCBANK.NS", "HDFC Bank", ""),
    ("HEROMOTOCO.NS", "Hero MotoCorp", "Hero Honda in 2011"),
    ("HINDALCO.NS", "Hindalco Industries", ""),
    ("HINDUNILVR.NS", "Hindustan Unilever", ""),
    ("ICICIBANK.NS", "ICICI Bank", ""),
    (None, "IDFC", "merged into IDFC First Bank, October 2024"),
    ("INFY.NS", "Infosys", ""),
    ("ITC.NS", "ITC", ""),
    (None, "Jaiprakash Associates", "in insolvency; Yahoo has no history"),
    ("JINDALSTEL.NS", "Jindal Steel & Power", ""),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank", ""),
    ("LT.NS", "Larsen & Toubro", ""),
    ("M&M.NS", "Mahindra & Mahindra", ""),
    ("MARUTI.NS", "Maruti Suzuki", ""),
    ("NTPC.NS", "NTPC", ""),
    ("ONGC.NS", "ONGC", ""),
    ("POWERGRID.NS", "Power Grid", ""),
    ("PNB.NS", "Punjab National Bank", ""),
    (None, "Ranbaxy Laboratories", "merged into Sun Pharma, March 2015"),
    (None, "Reliance Capital", "delisted after insolvency"),
    ("RCOM.NS", "Reliance Communications", "suspended for long stretches; 295 days with no volume"),
    ("RELIANCE.NS", "Reliance Industries", ""),
    ("RELINFRA.NS", "Reliance Infrastructure", ""),
    ("RPOWER.NS", "Reliance Power", ""),
    ("SIEMENS.NS", "Siemens India", ""),
    ("SBIN.NS", "State Bank of India", ""),
    ("SAIL.NS", "Steel Authority of India", ""),
    (None, "Sterlite Industries", "merged into Sesa Goa (now Vedanta), August 2013"),
    ("SUNPHARMA.NS", "Sun Pharma", ""),
    ("SUZLON.NS", "Suzlon", ""),
    ("TCS.NS", "Tata Consultancy Services", ""),
    ("TMPV.NS", "Tata Motors", "TMPV carries Tata Motors' history since the 2025 demerger"),
    ("TATAPOWER.NS", "Tata Power", ""),
    ("TATASTEEL.NS", "Tata Steel", ""),
    ("VEDL.NS", "Sesa Goa", "now Vedanta"),
    ("WIPRO.NS", "Wipro", ""),
]

TODAY = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO",
    "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL", "BSE", "CIPLA", "COALINDIA",
    "DRREDDY", "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDIGO", "INFY", "ITC", "JIOFIN",
    "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "MAXHEALTH", "NESTLEIND", "NTPC",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SHRIRAMFIN", "SBIN", "SUNPHARMA",
    "TCS", "TATACONSUM", "TMPV", "TATASTEEL", "TECHM", "TITAN", "TRENT", "ULTRACEMCO",
]
TODAY = [s + ".NS" for s in TODAY]

assert len(START_2011) == 50 and len(TODAY) == 50
