"""Reference-lap profile generation from recorded observations, not control labels."""
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import statistics
import uuid

MAX_PROFILE_BYTES=20*1024*1024

def load_jsonl(path):
    rows=[]
    if not path.exists():return rows
    with path.open(encoding="utf-8") as f:
        for number,line in enumerate(f,1):
            try:rows.append(json.loads(line))
            except json.JSONDecodeError as exc:raise ValueError(f"Corrupt {path.name} at line {number}") from exc
    return rows

def value(row,module):return row.get("modules",{}).get(module,{}).get("value")

def lap_intervals(observations,events):
    manual=sorted(set(e["timestamp"] for e in events if e.get("type")=="lap_boundary"))
    if len(manual)>=2:return [(a,b,"manual") for a,b in zip(manual,manual[1:]) if b-a>=5]
    # Require two successive observations of a new number; unknown gaps don't create laps.
    boundaries=[];last=None;candidate=None;streak=0;candidate_time=None
    for row in observations:
        lap=value(row,"lap_number")
        if lap is None:continue
        if lap==candidate:streak+=1
        else:candidate=lap;streak=1;candidate_time=row["timestamp"]
        if streak==2:
            if last is not None and lap==last+1:boundaries.append(candidate_time)
            last=lap
    return [(a,b,"ocr_lap_number") for a,b in zip(boundaries,boundaries[1:]) if b-a>=5]

def generate_profile(session_paths,circuit,category="unspecified",model="unspecified",weather="unspecified",bins=40):
    if not circuit.strip():raise ValueError("Enter a circuit name")
    laps=[];samples=[];landmarks=[];lines=[];corners=[];braking=[];sources=set()
    for session_path in session_paths:
        session=Path(session_path);manifest=json.loads((session/"manifest.json").read_text(encoding="utf-8"))
        if not manifest.get("complete"):raise ValueError(f"Session {session.name} is incomplete; use a cleanly stopped session")
        observations=sorted(load_jsonl(session/"observations.jsonl"),key=lambda r:r["timestamp"])
        events=load_jsonl(session/"events.jsonl")
        source=manifest.get("source","unknown");sources.add(source)
        labels=manifest.get("reference_labels",{})
        if labels.get("circuit_label") and labels["circuit_label"]!=circuit:raise ValueError("Selected sessions use a different circuit label")
        for key,expected in (("category",category),("model",model),("weather",weather)):
            if labels.get(key) and labels[key]!=expected:raise ValueError(f"Selected sessions have different {key}; use separate profiles")
        for start,end,method in lap_intervals(observations,events):
            rows=[r for r in observations if start<=r["timestamp"]<end]
            usable=[r for r in rows if value(r,"speed") is not None and r["modules"]["speed"]["confidence"]>=.8 and value(r,"gameplay_state") not in ("pause","loading","crash","recovery")]
            if len(usable)<5:continue
            lap_id=f"{session.name}:{len(laps)+1}";duration=end-start
            laps.append({"id":lap_id,"session":session.name,"source":source,"start_timestamp":start,"end_timestamp":end,"duration_s":duration,"boundary_method":method,"speed_samples":len(usable),"builtin_assists_enabled_or_unknown":labels.get("builtin_assists_enabled_or_unknown",True)})
            for row in usable:
                progress=(row["timestamp"]-start)/duration
                samples.append({"progress":progress,"speed_kmh":value(row,"speed"),"confidence":row["modules"]["speed"]["confidence"],"lap":lap_id})
            previous_direction="straight";entry=None
            for row in rows:
                progress=(row["timestamp"]-start)/duration
                corner=value(row,"corner")
                direction=corner["direction"] if corner else "unknown"
                if direction!=previous_direction:
                    if entry is not None:corners.append({"lap":lap_id,"direction":previous_direction,"entry":entry,"exit":progress,"confidence":row["modules"]["corner"]["confidence"]})
                    entry=progress if direction in ("left","right") else None;previous_direction=direction
                landmark=value(row,"landmarks")
                if landmark and (not landmarks or landmarks[-1]["lap"]!=lap_id or progress-landmarks[-1]["progress"]>.05):landmarks.append({"lap":lap_id,"progress":progress,"sequence":row["sequence"],"features":landmark,"confidence":row["modules"]["landmarks"]["confidence"]})
                line=value(row,"racing_line")
                if line:
                    lines.append({"lap":lap_id,"progress":progress,"sequence":row["sequence"],"sections":line["sections"],"confidence":row["modules"]["racing_line"]["confidence"]})
                    if any(s["color"] in ("red","yellow") for s in line["sections"]):braking.append({"lap":lap_id,"progress":progress,"colors":line["colors"],"confidence":row["modules"]["racing_line"]["confidence"]})
            if entry is not None:corners.append({"lap":lap_id,"direction":previous_direction,"entry":entry,"exit":1.0,"confidence":.4})
    if len(laps)<2:raise ValueError("Need at least two complete laps with five reliable speed readings each. Mark start/finish with F5, or calibrate lap-number OCR and record through several lap changes.")
    if len(sources)>1:raise ValueError("Do not combine simulation, video and Windows reference sessions in one profile")
    reference=[]
    for index in range(bins):
        rows=[s for s in samples if min(bins-1,int(s["progress"]*bins))==index]
        if rows:reference.append({"progress":(index+.5)/bins,"speed_kmh":round(statistics.median(r["speed_kmh"] for r in rows),2),"confidence":round(statistics.mean(r["confidence"] for r in rows),3),"samples":len(rows),"laps":len(set(r["lap"] for r in rows))})
    # Turn consecutive colored observations into intervals within each lap.
    zones=[]
    for point in braking:
        if zones and zones[-1]["lap"]==point["lap"] and point["progress"]-zones[-1]["exit"]<=.06:
            zone=zones[-1];zone["exit"]=point["progress"];zone["colors"]=sorted(set(zone["colors"]+point["colors"]));zone["confidence"]=min(zone["confidence"],point["confidence"])
        else:zones.append({"lap":point["lap"],"entry":point["progress"],"exit":point["progress"],"colors":point["colors"],"confidence":point["confidence"]})
    coverage=len(reference)/bins
    profile={"schema_version":1,"id":str(uuid.uuid4()),"created_at":datetime.now(timezone.utc).isoformat(),"circuit":circuit.strip(),"category":category,"model":model,"weather":weather,"version":1,"source":next(iter(sources)),"confidence":round(min(.8,coverage*statistics.mean(s["confidence"] for s in samples)),3),"progress_basis":"normalized elapsed lap time; NOT world position or a live localization system","assisted_reference_warning":"Recorded physical controls exclude internal game assistance corrections. Visual line colors are candidate braking zones, not physical brake labels.","reference_laps":laps,"best_reference_lap_s":min(l["duration_s"] for l in laps),"reference_speed_profile":reference,"corners":corners,"visual_braking_zones":zones,"landmarks":landmarks,"racing_line":lines,"coverage":round(coverage,3),"review_required":True}
    validate_profile(profile);return profile

def validate_profile(profile):
    if not isinstance(profile,dict) or profile.get("schema_version")!=1:raise ValueError("Unsupported track profile schema")
    for key in ("id","circuit","category","model","weather","source","progress_basis","assisted_reference_warning"):
        if not isinstance(profile.get(key),str) or not profile[key] or len(profile[key])>2000:raise ValueError(f"Invalid {key}")
    try:uuid.UUID(profile["id"])
    except (ValueError,TypeError):raise ValueError("Invalid profile ID")
    if not isinstance(profile.get("version"),int) or profile["version"]<1:raise ValueError("Invalid profile version")
    def number(value,lo,hi):return isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value) and lo<=value<=hi
    if not number(profile.get("confidence"),0,1):raise ValueError("Invalid confidence")
    for name in ("reference_laps","reference_speed_profile","corners","visual_braking_zones","landmarks","racing_line"):
        if not isinstance(profile.get(name),list) or len(profile[name])>100000:raise ValueError(f"Invalid {name}")
    if len(profile["reference_laps"])<2:raise ValueError("At least two reference laps required")
    for point in profile["reference_speed_profile"]:
        if not isinstance(point,dict) or not number(point.get("progress"),0,1) or not number(point.get("speed_kmh"),0,400) or not number(point.get("confidence"),0,1):raise ValueError("Invalid reference speed point")
    for corner in profile["corners"]:
        if not isinstance(corner,dict) or corner.get("direction") not in ("left","right") or not number(corner.get("entry"),0,1) or not number(corner.get("exit"),corner["entry"],1):raise ValueError("Invalid corner")
    # Reject NaN/Infinity anywhere, excessive size and non-JSON types before storage.
    try:encoded=json.dumps(profile,allow_nan=False).encode()
    except (ValueError,TypeError) as exc:raise ValueError("Profile must contain finite JSON data") from exc
    if len(encoded)>MAX_PROFILE_BYTES:raise ValueError("Profile exceeds 20 MiB limit")
    return profile

def import_profile(path):
    path=Path(path)
    if path.stat().st_size>MAX_PROFILE_BYTES:raise ValueError("Profile exceeds 20 MiB limit")
    return validate_profile(json.loads(path.read_text(encoding="utf-8")))

def export_profile(profile,path):
    validate_profile(profile);path=Path(path);temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(profile,indent=2,allow_nan=False),encoding="utf-8");temporary.replace(path)
