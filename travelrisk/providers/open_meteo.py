"""Independent forecast context from Open-Meteo; not a delay prediction."""
from urllib.parse import urlencode
from ..http_client import get_json
from .common import evidence, status, failed

def forecast(code, airport, start_utc, end_utc):
    params=urlencode({"latitude":airport["lat"],"longitude":airport["lon"],"hourly":"precipitation_probability,wind_gusts_10m,weather_code","forecast_days":7,"timezone":"UTC"})
    url="https://api.open-meteo.com/v1/forecast?"+params
    try:
        data,meta=get_json(url)
        if data is None:
            return [evidence("Open-Meteo",f"No forecast returned for {code}","The source returned a valid empty response.",url,severity="unknown",signal_id=f"om-empty-{code}")],status("Open-Meteo",code,"no_data","The source returned no forecast payload.",meta)
        hourly=data.get("hourly",{}); times=hourly.get("time",[]); indexes=[]
        import datetime as dt
        for i,value in enumerate(times):
            try:
                stamp=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
                if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=dt.timezone.utc)
                if start_utc <= stamp <= end_utc: indexes.append(i)
            except ValueError: continue
        if not indexes:
            state="stale" if meta.get("cache")=="stale" else "no_data"
            return [evidence("Open-Meteo",f"No forecast window for {code}","Forecast response contained no hours for the estimated flight window.",url,severity="unknown",signal_id=f"om-none-{code}",meta=meta)], status("Open-Meteo",code,state,"No forecast hours matched the flight window.",meta)
        probs=hourly.get("precipitation_probability",[]); gusts=hourly.get("wind_gusts_10m",[])
        codes=hourly.get("weather_code",[])
        maxp=max((probs[i] for i in indexes if i<len(probs) and isinstance(probs[i],(int,float))),default=None)
        maxg=max((gusts[i] for i in indexes if i<len(gusts) and isinstance(gusts[i],(int,float))),default=None)
        maxcode=max((codes[i] for i in indexes if i<len(codes) and isinstance(codes[i],(int,float))),default=None)
        rain_code=maxcode is not None and (51<=maxcode<=67 or 80<=maxcode<=82)
        snow_or_storm=maxcode is not None and (71<=maxcode<=77 or 85<=maxcode<=86 or 95<=maxcode<=99)
        detail=f"Window maximum: precipitation probability {maxp if maxp is not None else 'n/a'}%; wind gust {maxg if maxg is not None else 'n/a'} km/h; WMO weather code {maxcode if maxcode is not None else 'n/a'}. Independent model context only; not a flight-delay prediction."
        severity="high" if snow_or_storm else "moderate" if rain_code and (maxp or 0)>=70 else "info"
        return [evidence("Open-Meteo",f"Independent forecast context near {code}",detail,url,severity=severity,signal_id=f"openmeteo-{code}",meta=meta)], status("Open-Meteo",code,"stale" if meta.get("cache")=="stale" else "data","Independent weather values returned for the estimated flight window.",meta)
    except Exception as exc: return failed("Open-Meteo",code,url,exc)
