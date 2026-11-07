"""Small conservative parser for TAF validity groups and flight categories.

It deliberately handles only the common FM, TEMPO, PROBxx and BECMG groups. A
TAF that does not parse remains visible as raw source evidence, never as clear.
"""
from calendar import monthrange
from datetime import datetime, timezone
import re

_VALIDITY=re.compile(r"^(\d{2})(\d{2})/(\d{2})(\d{2})$")
_FM=re.compile(r"^FM(\d{2})(\d{2})(\d{2})$")
_RANGE=re.compile(r"^(\d{2})(\d{2})/(\d{2})(\d{2})$")
_GROUP=re.compile(r"^(?:FM\d{6}|TEMPO|BECMG|PROB\d{2})$")

def _day_hour(day, hour, reference):
    options=[]
    for delta in (-1,0,1):
        month=(reference.month-1+delta)%12+1
        year=reference.year+(reference.month-1+delta)//12
        if day <= monthrange(year,month)[1] and 0 <= hour <= 23:
            options.append(datetime(year,month,day,hour,tzinfo=timezone.utc))
    if not options: return None
    return min(options,key=lambda item:abs((item-reference).total_seconds()))

def _overlaps(start,end,window_start,window_end):
    # Forecast groups are half-open: a new group is active at its start time,
    # while the previous group's end instant belongs to the next group.
    return start < window_end and end > window_start

def _category(tokens):
    text=" ".join(tokens).upper()
    visibilities=[]
    for value in re.findall(r"(?<![A-Z0-9])(?:M)?(?:P)?\d+(?:/\d+)?SM",text):
        raw=value[:-2]
        try:
            if raw.startswith("M"): visibilities.append(float(raw[1:].split("/")[0])/float(raw[1:].split("/")[1]) if "/" in raw else float(raw[1:]))
            elif raw.startswith("P"): visibilities.append(6.1)
            else: visibilities.append(float(raw.split("/")[0])/float(raw.split("/")[1]) if "/" in raw else float(raw))
        except (ValueError,ZeroDivisionError): continue
    ceilings=[]
    for amount in re.findall(r"(?:BKN|OVC|VV)(\d{3})",text): ceilings.append(int(amount)*100)
    vis=min(visibilities) if visibilities else None
    ceiling=min(ceilings) if ceilings else None
    if (vis is not None and vis < 1) or (ceiling is not None and ceiling < 500): category="LIFR"
    elif (vis is not None and vis < 3) or (ceiling is not None and ceiling < 1000): category="IFR"
    elif (vis is not None and vis <= 5) or (ceiling is not None and ceiling <= 3000): category="MVFR"
    elif vis is not None or ceiling is not None: category="VFR"
    else: category=None
    hazards=[]
    if re.search(r"\bTS(?:RA|SN|GR|GS)?\b|\b\w*\+TS\w*\b",text): hazards.append("thunderstorm")
    if re.search(r"\b(?:SN|FZRA|FZDZ|PL|IC)\b",text): hazards.append("snow/icing")
    if re.search(r"\b(?:RA|SHRA|DZ)\b",text): hazards.append("rain/showers")
    return category,hazards

def assess_taf(raw,window_start,window_end):
    """Return (matched, category, hazards, severity); matched=False means no aligned group."""
    tokens=raw.upper().split()
    valid_index=next((i for i,t in enumerate(tokens) if _VALIDITY.match(t)),None)
    if valid_index is None: return False,None,[],"unknown"
    match=_VALIDITY.match(tokens[valid_index]); reference=window_start
    valid_start=_day_hour(int(match.group(1)),int(match.group(2)),reference)
    valid_end=_day_hour(int(match.group(3)),int(match.group(4)),reference)
    if valid_start is None or valid_end is None: return False,None,[],"unknown"
    if valid_end < valid_start: valid_end=valid_end.replace(month=valid_end.month%12+1,year=valid_end.year+(valid_end.month==12))
    body=tokens[valid_index+1:]
    starts=[i for i,t in enumerate(body) if _GROUP.match(t)]
    matched=[]
    first_fm=next((i for i,t in enumerate(body) if _FM.match(t)),len(body))
    base_end=valid_end
    if first_fm < len(body):
        fm=_FM.match(body[first_fm]); base_end=_day_hour(int(fm.group(1)),int(fm.group(2)),reference) or valid_end
    if first_fm>0 and _overlaps(valid_start,base_end,window_start,window_end):
        matched.append((valid_start,base_end,body[:first_fm]))
    fm_positions=[i for i,t in enumerate(body) if _FM.match(t)]
    for pos,idx in enumerate(fm_positions):
        fm=_FM.match(body[idx]); start=_day_hour(int(fm.group(1)),int(fm.group(2)),reference)
        end=valid_end
        for next_idx in fm_positions[pos+1:]:
            nextfm=_FM.match(body[next_idx]); end=_day_hour(int(nextfm.group(1)),int(nextfm.group(2)),reference) or valid_end; break
        next_group=next((i for i in fm_positions[pos+1:]),len(body))
        # Keep prevailing conditions but remove temporary/probability overlays.
        segment=body[idx+1:next_group]; conditions=[]; cursor=0
        while cursor<len(segment):
            if segment[cursor] in {"TEMPO","BECMG"} or re.match(r"^PROB\d{2}$",segment[cursor]):
                cursor+=1
                while cursor<len(segment) and not _GROUP.match(segment[cursor]): cursor+=1
            else:
                if not _RANGE.match(segment[cursor]): conditions.append(segment[cursor])
                cursor+=1
        if start and _overlaps(start,end,window_start,window_end): matched.append((start,end,conditions))
    for idx,token in enumerate(body):
        if token not in {"TEMPO","BECMG"} and not re.match(r"^PROB\d{2}$",token): continue
        rg=next((j for j in range(idx+1,min(len(body),idx+4)) if _RANGE.match(body[j])),None)
        if rg is None: continue
        rm=_RANGE.match(body[rg]); start=_day_hour(int(rm.group(1)),int(rm.group(2)),reference); end=_day_hour(int(rm.group(3)),int(rm.group(4)),reference)
        next_idx=next((j for j in starts if j>idx),len(body)); conditions=[t for t in body[rg+1:next_idx] if not _RANGE.match(t)]
        if start and end and _overlaps(start,end,window_start,window_end): matched.append((start,end,conditions))
    if not matched: return False,None,[],"unknown"
    categories=[]; hazards=[]
    for _,_,conditions in matched:
        category,found=_category(conditions)
        if category: categories.append(category)
        hazards.extend(found)
    order={"VFR":0,"MVFR":1,"IFR":2,"LIFR":3}
    category=max(categories,key=lambda item:order[item]) if categories else None
    hazards=list(dict.fromkeys(hazards))
    severity="high" if category=="LIFR" or "thunderstorm" in hazards or "snow/icing" in hazards else "moderate" if category in {"IFR","MVFR"} else "info"
    return True,category,hazards,severity
