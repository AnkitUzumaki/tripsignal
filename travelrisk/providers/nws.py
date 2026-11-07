"""National Weather Service forecasts and point alerts."""
from ..http_client import get_json
from .common import evidence, status

BASE = "https://api.weather.gov"

def fetch_point(code, airport, start_utc, end_utc):
    lat, lon = airport["lat"], airport["lon"]
    point_url = f"{BASE}/points/{lat:.4f},{lon:.4f}"
    out = []; statuses=[]; scope = f"{code} flight window"
    try:
        point, pm = get_json(point_url)
        if point is None:
            out.append(evidence("National Weather Service","No point data returned", "NWS returned an empty point response for this airport.",point_url,severity="unknown",signal_id=f"nws-point-empty-{code}"))
            statuses.append(status("National Weather Service",f"{code} hourly forecast","no_data","NWS returned no point metadata."))
            forecast_url=point_url; fc={"properties":{"periods":[]}}; meta={"no_data":True}
        else:
            forecast_url = point["properties"]["forecastHourly"]
            fc, meta = get_json(forecast_url)
        forecast_empty=fc is None
        if forecast_empty: fc={"properties":{"periods":[]}}
        periods = []
        for p in fc.get("properties", {}).get("periods", []):
            try:
                import datetime as dt
                t = dt.datetime.fromisoformat(p["startTime"].replace("Z", "+00:00"))
                if start_utc <= t <= end_utc: periods.append(p)
            except (ValueError, KeyError): continue
        if periods:
            phrases = list(dict.fromkeys(p.get("shortForecast", "") for p in periods if p.get("shortForecast")))
            hazards = [p for p in periods if any(x in p.get("shortForecast", "").lower() for x in ("thunder", "snow", "ice", "freezing", "blizzard", "hurricane"))]
            precip_values=[p.get("probabilityOfPrecipitation",{}).get("value") for p in periods if isinstance(p.get("probabilityOfPrecipitation"),dict)]
            max_precip=max((value for value in precip_values if isinstance(value,(int,float))),default=None)
            wet_likely=max_precip is not None and max_precip>=70 and any(any(word in phrase.lower() for word in ("rain","shower","snow","sleet")) for phrase in phrases)
            detail = "; ".join(phrases[:5]) or "Hourly forecast available for this flight window."
            if max_precip is not None: detail+=f" Forecast precipitation chance reaches {max_precip}% in the selected window."
            out.append(evidence("National Weather Service", f"Hourly weather near {code}", detail, forecast_url,
                                fc.get("properties",{}).get("generatedAt"), "high" if hazards else "moderate" if wet_likely else "info", signal_id=f"nws-weather-{code}", meta=meta))
            fstate, fmsg = ("stale" if meta.get("cache")=="stale" else "data"), f"Hourly forecast covers the approximate {code} flight window."
        else:
            message="The source returned an empty forecast response." if forecast_empty else "The API returned a forecast but no hourly period matched the approximate flight window."
            out.append(evidence("National Weather Service", f"No hourly periods for {code} window", message, forecast_url, severity="unknown", signal_id=f"nws-window-{code}", meta=meta))
            fstate, fmsg = ("stale" if meta.get("cache")=="stale" else "no_data"), "No forecast payload or no periods matched the requested time window."
        if not any(s.scope==f"{code} hourly forecast" for s in statuses):
            statuses.append(status("National Weather Service", f"{code} hourly forecast", fstate, fmsg, meta))
    except Exception as exc:
        unsupported=getattr(exc,"status_code",None)==404
        state="unsupported" if unsupported else "failed"
        title="NWS does not cover this point" if unsupported else f"Hourly forecast failed for {code}"
        message="This source does not cover the requested point." if unsupported else "Forecast request failed; no current forecast is available."
        out.append(evidence("National Weather Service", title, str(exc)[:220], point_url, severity="unknown", signal_id=f"nws-forecast-failed-{code}"))
        statuses.append(status("National Weather Service",f"{code} hourly forecast",state,message))
    try:
        alerts_url = f"{BASE}/alerts/active?point={lat:.4f},{lon:.4f}"
        alerts, am = get_json(alerts_url)
        alerts_empty=alerts is None
        if alerts_empty: alerts={"features":[]}
        features = alerts.get("features", [])
        relevant = []
        for a in features:
            p = a.get("properties", {})
            # Include active alerts overlapping the approximate event window when validity bounds are present.
            try:
                import datetime as dt
                onset = dt.datetime.fromisoformat((p.get("onset") or p.get("effective") or "").replace("Z", "+00:00"))
                ends = dt.datetime.fromisoformat((p.get("ends") or p.get("expires") or "").replace("Z", "+00:00"))
                if ends < start_utc or onset > end_utc: continue
            except (ValueError, TypeError): pass
            relevant.append(p)
        for p in relevant[:5]:
            event = p.get("event", "Weather alert")
            out.append(evidence("National Weather Service", f"{event} near {code}", p.get("headline") or (p.get("description") or "")[:300], p.get("web") or alerts_url,
                                p.get("sent"), "high" if any(x in event.lower() for x in ("warning", "tornado", "severe", "blizzard", "hurricane")) else "moderate",
                                signal_id=f"nws-alert-{code}-{event}", meta=am))
        if not relevant:
            out.append(evidence("National Weather Service", f"No active alert matched {code} window", "No matching point alert was returned. This is not a guarantee of normal conditions.", alerts_url,
                                severity="info", signal_id=f"nws-no-alert-{code}", meta=am))
            default_state="no_data" if alerts_empty else "clear"
            astate,amsg=("stale" if am.get("cache")=="stale" else default_state),"No active point alert matched this flight window."
        else:
            astate,amsg=("stale" if am.get("cache")=="stale" else "data"),f"{len(relevant)} active alert(s) overlap the approximate window."
        statuses.append(status("National Weather Service", f"{code} alerts", astate, amsg, am))
    except Exception as exc:
        alerts_url = f"{BASE}/alerts/active?point={lat:.4f},{lon:.4f}"
        unsupported=getattr(exc,"status_code",None)==404
        state="unsupported" if unsupported else "failed"
        out.append(evidence("National Weather Service",f"Alert lookup {'not supported' if unsupported else 'failed'} for {code}",str(exc)[:220],alerts_url,severity="unknown",signal_id=f"nws-alert-failed-{code}"))
        statuses.append(status("National Weather Service",f"{code} alerts",state,"This source does not cover the requested point." if unsupported else "Alert request failed; no current result is available."))
    return out,statuses
