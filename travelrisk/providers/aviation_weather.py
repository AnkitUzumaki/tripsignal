"""Aviation Weather Center TAF and current combined SIGMET feed."""
import json
from urllib.parse import urlencode
from ..http_client import get_json
from .common import evidence, status, failed
from ..taf import assess_taf

BASE = "https://aviationweather.gov/api/data"

def airport_taf(code, airport, start_utc, end_utc):
    params = urlencode({"ids": airport["icao"], "format": "json"}); url = f"{BASE}/taf?{params}"
    try:
        rows, meta = get_json(url)
        if not isinstance(rows, list) or not rows:
            default_state="no_data" if payload is None else "clear"
            state="stale" if meta.get("cache")=="stale" else default_state
            return [evidence("Aviation Weather Center", f"No TAF returned for {code}", "The endpoint returned no terminal forecast for this station.", url, severity="unknown", signal_id=f"taf-none-{code}", meta=meta)], status("Aviation Weather Center", code, state, "No terminal forecast was returned.", meta)
        item = rows[0]; raw = item.get("rawTAF") or item.get("rawTAFString") or item.get("raw_text") or json.dumps(item, ensure_ascii=False)
        matched,category,hazards,severity=assess_taf(raw,start_utc,end_utc)
        if matched:
            assessment=f"Estimated-window category: {category or 'not determined'}"+(f"; weather groups: {', '.join(hazards)}" if hazards else "")+". TAF remains available below for inspection."
            state="stale" if meta.get("cache")=="stale" else "data"
            message="A TAF forecast group overlaps the estimated airport window."
        else:
            assessment="No decoded TAF forecast group could be aligned to this estimated window; source text is shown for inspection."
            state="stale" if meta.get("cache")=="stale" else "no_data"
            message="TAF was returned, but no group could be aligned to the estimated window."
        return [evidence("Aviation Weather Center", f"TAF for {code}", assessment+"\n"+raw[:1200], url, item.get("issueTime") or item.get("issue_time"), severity, signal_id=f"taf-{code}", meta=meta)], status("Aviation Weather Center", code, state, message, meta)
    except Exception as exc: return failed("Aviation Weather Center", code, url, exc)

def _polygons(geometry):
    if not geometry: return []
    if geometry.get("type") == "Polygon": return geometry.get("coordinates", [])[:1]
    if geometry.get("type") == "MultiPolygon": return [poly[0] for poly in geometry.get("coordinates", []) if poly]
    return []

def _inside(point, ring):
    x, y = point[1], point[0]; inside = False
    for i in range(len(ring)):
        x1,y1=ring[i][0],ring[i][1]; x2,y2=ring[(i+1)%len(ring)][0],ring[(i+1)%len(ring)][1]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1+1e-15)+x1: inside=not inside
    return inside

def _distance_nm(a, b):
    import math
    lat1,lon1=map(math.radians,a); lat2,lon2=map(math.radians,b)
    dlat=lat2-lat1; dlon=lon2-lon1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 3440.065*2*math.asin(min(1,math.sqrt(h)))

def _point_segment_nm(point, a, b):
    # Local equirectangular approximation is adequate for the 50 NM buffer.
    import math
    lat0=math.radians(point[0]); scale_y=60.0; scale_x=60.0*math.cos(lat0)
    px,py=point[1]*scale_x,point[0]*scale_y
    ax,ay=a[0]*scale_x,a[1]*scale_y; bx,by=b[0]*scale_x,b[1]*scale_y
    dx,dy=bx-ax,by-ay; denom=dx*dx+dy*dy
    t=0 if denom==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/denom))
    return math.hypot(px-(ax+t*dx),py-(ay+t*dy))

def _near_ring(point, ring, tolerance_nm):
    if _inside(point,ring): return True
    return any(_point_segment_nm(point,(ring[i][1],ring[i][0]),(ring[(i+1)%len(ring)][1],ring[(i+1)%len(ring)][0]))<=tolerance_nm for i in range(len(ring)))

def _route_samples(origin, destination, spacing_nm=25):
    # Spherical linear interpolation along the great-circle arc.
    import math
    lat1,lon1=map(math.radians,(origin["lat"],origin["lon"])); lat2,lon2=map(math.radians,(destination["lat"],destination["lon"]))
    v1=(math.cos(lat1)*math.cos(lon1),math.cos(lat1)*math.sin(lon1),math.sin(lat1)); v2=(math.cos(lat2)*math.cos(lon2),math.cos(lat2)*math.sin(lon2),math.sin(lat2))
    dot=max(-1,min(1,sum(x*y for x,y in zip(v1,v2)))); omega=math.acos(dot); dist=3440.065*omega
    count=max(2,int(dist/spacing_nm)+1); points=[]
    for i in range(count+1):
        f=i/count
        if omega<1e-9: v=v1
        else: v=tuple(math.sin((1-f)*omega)/math.sin(omega)*v1[j]+math.sin(f*omega)/math.sin(omega)*v2[j] for j in range(3))
        points.append((math.degrees(math.atan2(v[2],math.hypot(v[0],v[1]))),math.degrees(math.atan2(v[1],v[0]))))
    return points

def route_sigmets(origin_code, origin, destination_code, destination, depart_utc, arrive_utc, corridor_nm=50):
    url=f"{BASE}/sigmet?format=geojson"
    try:
        payload, meta = get_json(url)
        features=payload.get("features",[]) if isinstance(payload,dict) else []
        samples=_route_samples(origin,destination); hits=[]
        for feature in features:
            props=feature.get("properties",{}); geometry=feature.get("geometry")
            # Ignore SIGMETs with explicit validity that misses the estimated route time.
            try:
                import datetime as dt
                start=dt.datetime.fromisoformat((props.get("validTimeFrom") or props.get("valid_from") or "").replace("Z","+00:00"))
                end=dt.datetime.fromisoformat((props.get("validTimeTo") or props.get("valid_to") or "").replace("Z","+00:00"))
                if end < depart_utc or start > arrive_utc: continue
            except (ValueError,TypeError): pass
            intersects=False
            for ring in _polygons(geometry):
                if any(_near_ring(p,ring,corridor_nm) for p in samples): intersects=True; break
            if intersects: hits.append((props, feature))
        if not hits:
            ev=evidence("Aviation Weather Center", "No SIGMET intersected the estimated route", f"Checked active SIGMET GeoJSON against a great-circle route with 25 NM sample spacing and a {corridor_nm} NM intended corridor. Because the provider geometry and corridor handling may vary, this check is approximate.", url, severity="info", signal_id="sigmet-none", meta=meta)
            state="stale" if meta.get("cache")=="stale" else "no_data"
            return [ev], status("Aviation Weather Center", f"{origin_code}–{destination_code} route", state, "No matching active SIGMET geometry was found on the sampled route.", meta)
        out=[]
        for i,(props,feature) in enumerate(hits[:8]):
            label=props.get("hazard") or props.get("phenomenon") or props.get("rawAirSigmet") or props.get("raw_text") or json.dumps(props,ensure_ascii=False)
            out.append(evidence("Aviation Weather Center", "SIGMET near estimated route", str(label)[:600], url, props.get("issueTime") or props.get("issue_time"), "high", signal_id=f"sigmet-{i}", meta=meta))
        return out, status("Aviation Weather Center", f"{origin_code}–{destination_code} route", "stale" if meta.get("cache")=="stale" else "data", f"{len(hits)} active SIGMET feature(s) intersected the sampled route.", meta)
    except Exception as exc: return failed("Aviation Weather Center", f"{origin_code}–{destination_code} route", url, exc)
