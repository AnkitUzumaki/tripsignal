"""Conservative heuristic index. Never represents calibrated probability."""
from collections import defaultdict
from .config import SETTINGS

def score(evidence):
    # De-duplicate weather feeds into one family so the same weather event isn't added repeatedly.
    groups=defaultdict(list)
    for item in evidence:
        if item.severity not in {"high","moderate"}: continue
        family="operations" if item.source=="FAA NAS Status" else "weather"
        groups[family].append(item.severity)
    points=SETTINGS["risk_index"]; value=0
    for severities in groups.values():
        value += points["high_signal_points"] if "high" in severities else points["moderate_signal_points"]
    value=min(100,value)
    if not evidence or all(x.severity=="unknown" for x in evidence): return None,"Insufficient evidence"
    if value>=points["elevated_at"]: return value,"Elevated"
    if value>=points["some_risk_at"]: return value,"Some risk"
    return value,"No major signal found"

def recommendation(band,evidence):
    triggers=[]
    if band=="Insufficient evidence":
        return "Check directly with your airline because the available sources could not support an assessment.",["Too little current source data was available."]
    signals=[x for x in evidence if x.severity in {"moderate","high"}]
    if not signals:
        triggers=["No moderate or high signal was returned by the sources that responded."]
        return "No major signal was found. Confirm your itinerary with the airline and recheck before leaving.",triggers
    for item in signals:
        triggers.append(f"{item.source}: {item.title}")
    if band=="Elevated":
        action="Check your airline's flight status and review flexible alternatives. Reassess closer to departure; this tool cannot advise you to rebook."
    else:
        action="Review the cited notices and check your airline before leaving for the airport. Allow extra time if the airline advises it."
    return action,list(dict.fromkeys(triggers))
