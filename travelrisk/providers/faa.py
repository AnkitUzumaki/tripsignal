"""FAA NAS Status XML adapter. Parsing is conservative and preserves feed provenance."""
import re
import xml.etree.ElementTree as ET
from ..http_client import get_xml
from .common import evidence, status, failed

URL="https://nasstatus.faa.gov/api/airport-status-information"

def _local(tag): return tag.rsplit("}",1)[-1].lower()

def airport_events(codes):
    try:
        xml,meta=get_xml(URL,ttl=60)
        if xml is None:
            return [evidence("FAA NAS Status","No FAA status payload","The feed returned a valid empty response.",URL,severity="unknown",signal_id="faa-empty")],status("FAA NAS Status","route airports","no_data","The source returned no status payload.",meta)
        root=ET.fromstring(xml); found=[]
        targets={x.upper() for x in codes}
        # Identify airport-code-bearing subtrees and retain a compact parent event description.
        for node in root.iter():
            descendants=list(node.iter())
            code_values={((x.text or "").strip().upper()) for x in descendants if _local(x.tag) in {"airport_code","airportcode","code","iata","icao"}}
            if not (targets & code_values): continue
            texts=[" ".join((x.text or "").split()) for x in descendants if (x.text or "").strip()]
            detail=" · ".join(dict.fromkeys(texts))
            if detail and len(detail)<900: found.append((sorted(targets&code_values),detail))
        # Root/subtree duplication is common in XML; keep the largest useful distinct snippets.
        unique=[]
        for codes_found,detail in sorted(found,key=lambda x:len(x[1]),reverse=True):
            if not any(detail in old or old in detail for _,old in unique): unique.append((codes_found,detail))
        if unique:
            ev=[]
            for codes_found,detail in unique[:6]:
                normalized=detail.lower()
                severity="high" if any(term in normalized for term in ("ground stop","airport closure","airport closed")) else "moderate" if any(term in normalized for term in ("ground delay","delay program","arrival delay","departure delay")) else "info"
                ev.append(evidence("FAA NAS Status",f"FAA notice for {', '.join(codes_found)}",detail,URL,severity=severity,signal_id="faa-"+"-".join(codes_found),meta=meta))
            return ev,status("FAA NAS Status","route airports","stale" if meta.get("cache")=="stale" else "data",f"{len(ev)} matching operational notice(s) found.",meta)
        state="stale" if meta.get("cache")=="stale" else "clear"
        return [evidence("FAA NAS Status","No matching FAA airport notice", "The feed returned successfully but no airport-code match was found. Absence of a match does not guarantee normal operations.",URL,signal_id="faa-no-match",meta=meta)],status("FAA NAS Status","route airports",state,"Feed returned but no matching route-airport notice was found.",meta)
    except Exception as exc: return failed("FAA NAS Status","route airports",URL,exc)
