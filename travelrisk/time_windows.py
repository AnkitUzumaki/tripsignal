"""Convert user-entered local departure date/time into explicit approximate UTC windows."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

def route_windows(origin, destination, travel_date, departure_time, duration_hours):
    day=date.fromisoformat(travel_date); clock=time.fromisoformat(departure_time)
    zone=ZoneInfo(origin["timezone"]); local=datetime.combine(day,clock)
    start=local.replace(tzinfo=zone,fold=0)
    if start.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)!=local:
        raise ValueError("That local departure time does not exist because of a daylight-saving clock change.")
    dst_ambiguous=start.utcoffset()!=local.replace(tzinfo=zone,fold=1).utcoffset()
    depart=start.astimezone(timezone.utc); arrive=depart+timedelta(hours=duration_hours)
    # Check a 2-hour operating window on either side of departure/estimated arrival.
    return {"depart_utc":depart,"arrive_utc":arrive,
            "origin_start_utc":depart-timedelta(hours=2),"origin_end_utc":depart+timedelta(hours=2),
            "destination_start_utc":arrive-timedelta(hours=2),"destination_end_utc":arrive+timedelta(hours=2),
            "arrival_local":arrive.astimezone(ZoneInfo(destination["timezone"])),"dst_ambiguous":dst_ambiguous}
