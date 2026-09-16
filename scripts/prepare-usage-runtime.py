"""Prepare a separate private overlay against an inspected LIVE Compose file.

No existing configuration is edited. --apply requires both gateways idle and
recreates only the two named services; credentials/data mounts remain intact.
Requires Python + PyYAML on the deployment host.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import yaml

p=argparse.ArgumentParser()
p.add_argument("--compose",type=Path,required=True)
p.add_argument("--main-service",default="hermes-main")
p.add_argument("--second-service",default="hermes-owashota")
p.add_argument("--image",required=True,help="tested immutable Docker image ID")
p.add_argument("--output",type=Path,required=True)
p.add_argument("--apply",action="store_true")
p.add_argument("--only",nargs="+",help="Apply only these named idle gateways; still prepare the full overlay")
a=p.parse_args()
compose=a.compose.resolve()
base=["docker","compose","-f",str(compose)]
original=json.loads(subprocess.check_output(base+["config","--format","json"]))
image=json.loads(subprocess.check_output(["docker","image","inspect",a.image]))[0]
assert image["Id"]==a.image,"use a verified immutable image ID"
a.output.mkdir(parents=True,exist_ok=True,mode=0o700)
here=Path(__file__).resolve().parents[1]
overlay={"services":{}}
protected={}
old_images={}
for name,profile in [(a.main_service,"main"),(a.second_service,"owashota")]:
    service=original["services"][name]
    cid=subprocess.check_output(base+["ps","-q",name],text=True).strip()
    assert cid,"gateway is not running"
    info=json.loads(subprocess.check_output(["docker","inspect",cid]))[0]
    old_images[name]=info["Image"]
    # Inspect ONLY the active count; never copy conversation/session state.
    state=json.loads(subprocess.check_output(["docker","exec",cid,"python","-c",
        'import json; p=json.load(open("/opt/data/gateway_state.json")); a=p.get("active_agents"); print(json.dumps({"idle":a==0 or a==[] or a=={}}))']))
    if not a.only or name in a.only:
        assert state["idle"],name+" has active or unknown agents; retry after they finish"
    for volume in service.get("volumes",[]):
        if volume.get("target")=="/opt/data":
            for file in ("config.yaml","SOUL.md"):
                path=Path(volume["source"])/file
                if path.exists():protected[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    config=(a.output/(profile+"-windows.yaml")).resolve()
    shutil.copy2(here/"observability/hermes-otel"/(profile+"-windows.yaml"),config)
    overlay["services"][name]={"image":a.image,
       "environment":{"HERMES_OTEL_USAGE_ONLY":"true","OTEL_EXPORTER_OTLP_TRACES_TIMEOUT":"3"},
       "volumes":[str(config)+":/opt/data/.hermes/plugins/hermes_otel/config.yaml:ro"]}
path=(a.output/"compose.usage.local.yaml").resolve()
path.write_text(yaml.safe_dump(overlay,sort_keys=False))
combined=base+["-f",str(path)]
merged=json.loads(subprocess.check_output(combined+["config","--format","json"]))
for name in original["services"]:
    before=original["services"][name]
    after=merged["services"][name]
    if name not in overlay["services"]:
        assert before==after,"unrelated service changed"
        continue
    for key in before:
        if key not in ("image","environment","extra_hosts","volumes"):
            assert before[key]==after[key],"unexpected service field change: "+key
    for key,value in before.get("environment",{}).items():
        if key not in ("HERMES_OTEL_USAGE_ONLY","OTEL_EXPORTER_OTLP_TRACES_TIMEOUT"):
            assert after["environment"][key]==value,"existing environment changed"
    mounts={v["target"]:v for v in after.get("volumes",[])}
    for v in before.get("volumes",[]):
        if v["target"]!="/opt/data/.hermes/plugins/hermes_otel/config.yaml":
            assert mounts[v["target"]]==v,"existing data mount changed"
rollback=a.output/"rollback.local.json"
if not rollback.exists():
    rollback.write_text(json.dumps({"old_images":old_images,"protected_hashes":protected},indent=2))
print("OVERLAY_VALIDATED: only image, usage flags, collector alias and plugin config mount change",flush=True)
if a.apply:
    targets=a.only or [a.main_service,a.second_service]
    assert set(targets)<=set(overlay["services"]),"unknown --only service"
    subprocess.run(combined+["up","-d","--no-deps","--no-build","--timeout","60"]+targets,check=True)
    for path,digest in protected.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,"protected config changed"
    print("DEPLOYED: existing config/SOUL hashes preserved; verify gateway health",flush=True)
