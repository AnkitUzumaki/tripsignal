"""Assessment orchestration: input validation, source fan-out, scoring and provenance."""
import concurrent.futures
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .config import AIRPORTS, SETTINGS
from .models import Assessment
from .models import SourceStatus
from .time_windows import route_windows
from .providers import faa, nws, aviation_weather, open_meteo
from .scoring import score, recommendation
from .fixtures import demo

def assess(payload):
    origin_code=str(payload.get("origin","")).upper().strip(); destination_code=str(payload.get("destination","")).upper().strip()
    if origin_code not in AIRPORTS or destination_code not in AIRPORTS: raise ValueError("Choose origin and destination from the supported US airport list.")
    if origin_code==destination_code: raise ValueError("Choose two different airports.")
    try: travel_date=date.fromisoformat(str(payload.get("date","")))
    except ValueError: raise ValueError("Enter a valid travel date.")
    origin=AIRPORTS[origin_code]; destination=AIRPORTS[destination_code]
    today=datetime.now(ZoneInfo(origin["timezone"])).date()
    if travel_date < today or travel_date > today+timedelta(days=SETTINGS["maximum_forecast_days"]):
        raise ValueError(f"Choose a date from today through {SETTINGS['maximum_forecast_days']} days ahead in the origin airport's local timezone.")
    departure_time=str(payload.get("departure_time","09:00"))
    try:
        from datetime import time
        time.fromisoformat(departure_time)
    except ValueError: raise ValueError("Enter a valid local departure time (HH:MM).")
    try: duration=float(payload.get("duration_hours",6))
    except (ValueError,TypeError): raise ValueError("Flight duration must be a number of hours.")
    if not 1 <= duration <= 16: raise ValueError("Estimated flight duration must be from 1 to 16 hours.")
    try: windows=route_windows(origin,destination,travel_date.isoformat(),departure_time,duration)
    except (ValueError,ZoneInfoNotFoundError) as exc: raise ValueError(f"Could not calculate airport-local times: {exc}")
    route={"origin":origin_code,"origin_name":origin["name"],"origin_timezone":origin["timezone"],
           "destination":destination_code,"destination_name":destination["name"],"destination_timezone":destination["timezone"]}
    if payload.get("mode")=="demo": return demo({"date":travel_date.isoformat(),"departure_time":departure_time,"duration_hours":duration},route,windows)
    jobs=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8,thread_name_prefix="source") as pool:
        for code,airport,start,end in [(origin_code,origin,windows["origin_start_utc"],windows["origin_end_utc"]),(destination_code,destination,windows["destination_start_utc"],windows["destination_end_utc"])]:
            jobs.extend([pool.submit(nws.fetch_point,code,airport,start,end),
                         pool.submit(aviation_weather.airport_taf,code,airport,start,end),
                         pool.submit(open_meteo.forecast,code,airport,start,end)])
        jobs.append(pool.submit(aviation_weather.route_sigmets,origin_code,origin,destination_code,destination,
                                windows["depart_utc"],windows["arrive_utc"],SETTINGS["sigmet_corridor_nm"]))
        jobs.append(pool.submit(faa.airport_events,[origin_code,destination_code]))
        results=[]
        for job in jobs:
            try: results.append(job.result())
            except Exception as exc: results.append(([],SourceStatus("Assessment worker","source adapter","failed",str(exc)[:180])))
    evidence=[]; statuses=[]
    for items,status in results:
        evidence.extend(items)
        statuses.extend(status if isinstance(status,list) else [status])
    eligible=[s for s in statuses if s.state in {"data","clear","no_data","stale"}]
    failed_count=sum(s.state=="failed" for s in statuses)
    responding_sources={s.source for s in eligible}
    score_value,band=score(evidence)
    if len(eligible)<4 or len(responding_sources)<2:
        score_value,band=None,"Insufficient evidence"
    confidence="Higher" if len(eligible)>=7 and failed_count==0 else "Moderate" if len(eligible)>=4 else "Low"
    if (travel_date-today).days>=4: confidence="Low"
    if score_value is None: confidence="Low"
    action,reasons=recommendation(band,evidence)
    assumptions=[f"Departure time is {departure_time} at {origin_code} local time ({origin['timezone']}).",
                 f"Arrival is estimated using a {duration:g}-hour user-selected duration, at {destination_code} local time ({destination['timezone']}).",
                 "Weather windows are approximate: two hours before/after estimated departure and arrival.",
                 f"SIGMET matching samples the great-circle route every 25 nautical miles; corridor tolerance is approximately {SETTINGS['sigmet_corridor_nm']} nautical miles and is not a flight path.",
                 "Risk index is heuristic and not calibrated to flight outcomes; weather sources may overlap."]
    if windows["dst_ambiguous"]: assumptions.append("The selected departure time occurs twice during the daylight-saving clock change; the first occurrence was used.")
    coverage={"checks_total":len(statuses),"checks_responded":len(eligible),"checks_failed":failed_count,
              "sources_responded":sorted(responding_sources),"minimum_coverage_met":len(eligible)>=4 and len(responding_sources)>=2}
    return Assessment({**route,"date":travel_date.isoformat(),"departure_local":departure_time,"estimated_duration_hours":duration,
                       "estimated_departure_utc":windows["depart_utc"].isoformat(timespec="minutes"),
                       "estimated_arrival_local":windows["arrival_local"].isoformat(timespec="minutes"),
                       "estimated_arrival_utc":windows["arrive_utc"].isoformat(timespec="minutes")},score_value,band,confidence,action,reasons,evidence,statuses,
                      coverage,datetime.now(timezone.utc).isoformat(timespec="seconds"),assumptions).to_dict()
