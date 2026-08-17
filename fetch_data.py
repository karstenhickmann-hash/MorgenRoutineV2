import json, math, re
from datetime import datetime, timezone
import requests, pandas as pd, yfinance as yf

R={"generated_at":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
   "vix":None,"vvix":None,"skew":None,"fearGreed":None,
   "pcrTotal":None,"pcrEquity":None,"pcrIndex":None}

SYMS={"Vix":"^VIX","Es":"ES=F","Rut":"^RUT","Nya":"^NYA","Ym":"YM=F","Djt":"^DJT",
      "Dju":"^DJU","Nq":"NQ=F","Dax":"^GDAXI","Stoxx":"^STOXX50E","Ewg":"EWG"}

def clean(v):
    try:
        v=float(v)
        return None if math.isnan(v) or math.isinf(v) else round(v,2)
    except: return None

def last(sym):
    try:
        h=yf.download(sym,period="10d",interval="1d",progress=False,auto_adjust=False,threads=False)
        s=h["Close"]
        if hasattr(s,"columns"): s=s.iloc[:,0]
        return clean(s.dropna().iloc[-1])
    except: return None

R["vix"]=last("^VIX"); R["vvix"]=last("^VVIX"); R["skew"]=last("^SKEW")

def ma(sym):
    try:
        h=yf.download(sym,period="2y",interval="1d",progress=False,auto_adjust=False,threads=False)
        s=h["Close"]
        if hasattr(s,"columns"): s=s.iloc[:,0]
        s=s.dropna()
        d=clean((s.iloc[-1]/s.tail(21).mean()-1)*100) if len(s)>=21 else None
        w=s.resample("W-FRI").last().dropna()
        wk=clean((w.iloc[-1]/w.tail(21).mean()-1)*100) if len(w)>=21 else None
        return d,wk
    except: return None,None

for k,s in SYMS.items():
    d,w=ma(s); R[f"ma{k}D"]=d; R[f"ma{k}W"]=w

try:
    j=requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                   headers={"User-Agent":"Mozilla/5.0"},timeout=20).json()
    fg=j.get("fear_and_greed",{}) if isinstance(j,dict) else {}
    R["fearGreed"]=clean(fg.get("score"))
except: pass

try:
    url="https://www.cboe.com/markets/us/options/market-statistics/daily/"
    html=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=30).text
    text=re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",html))
    for heading,key in {"SUM OF ALL PRODUCTS":"pcrTotal","EQUITY OPTIONS":"pcrEquity","INDEX OPTIONS":"pcrIndex"}.items():
        p=text.upper().find(heading)
        if p>=0:
            vals=[int(x.replace(",","")) for x in re.findall(r'(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?![\w.])',text[p:p+1000])]
            for i in range(len(vals)-1):
                c,put=vals[i],vals[i+1]
                if c>1000 and put>1000:
                    R[key]=clean(put/c); break
except: pass

with open("current.json","w",encoding="utf-8") as f:
    json.dump(R,f,ensure_ascii=False,indent=2)
print(json.dumps(R,ensure_ascii=False,indent=2))
