"""Read only task metadata. Never read the owner's Windows .env or process secrets."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

WORK = Path(__file__).resolve().parent
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=8', 'yanelmoserver']
CODE = '''import json,sys,socket,os,re,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/opt/data/sarashina-support')
import control,prepare,key_entry
def read(p):
    return json.loads(p.read_text()) if p.exists() else {}
def select(d,names):
    return {n:d.get(n) for n in names if n in d}
def runtime(home,live_pid):
    d=read(home/'gateway_state.json')
    platform=d.get('platforms',{}).get('discord',{})
    out=select(d,('gateway_state','desired_state','active_agents','pid','start_time','updated_at'))
    out['discord']=select(platform,('state','error_code','needs_attention','writer_pid','writer_start_time','updated_at'))
    out['discord_current_writer']=bool(live_pid) and platform.get('writer_pid')==live_pid and platform.get('writer_start_time')==d.get('start_time')
    return out
m=control.verify_prepared()
root_pid=control.gateway_pid(prepare.ROOT)
candidate_pid=control.gateway_pid(prepare.PROFILE)
h=key_entry.read_state()
sock=socket.socket();sock.settimeout(1)
try:listening=sock.connect_ex(('127.0.0.1',18761))==0
finally:sock.close()
s6=subprocess.run(['/command/s6-svstat','/run/service/gateway-default'],capture_output=True,text=True,timeout=5)
result={'prepared_verified':True,'original_files_unchanged':prepare.protected_hashes(prepare.ROOT)==m['original_hashes'],
'original_gateway_pid':root_pid,'sarashina_gateway_pid':candidate_pid,'proxy_listening':listening,
'controller':select(control.read_state(),('controller_pid','state','gateway_pid','proxy_port','updated_at_utc','error_type')),
'holder':{**select(h,('state','holder_pid','has_memory_key','key_saved_to_file','accepted_at_utc','expires_at_utc','updated_at_utc','error_type')),'holder_alive':key_entry.alive(h)},
'probe':select(read(control.PROBE_DIAGNOSTIC),('ok','at_utc','http_status','json_content_type','response_object_valid','choices_count','assistant_role_valid','text_present','text_characters','finish_reason','model_matches_request','valid_response','response_body_saved','key_saved','elapsed_ms','error_type','tools_ok','tool_http_status','tool_sse','tool_call_valid','tool_arguments_valid','tool_result_http_status','tool_result_sse','tool_result_text_present','tool_result_used')),
'original_runtime':runtime(prepare.ROOT,root_pid),'sarashina_runtime':runtime(prepare.PROFILE,candidate_pid),
's6_status':s6.stdout.strip(),'profile_uid':prepare.PROFILE.stat().st_uid,'profile_gid':prepare.PROFILE.stat().st_gid,
'new_auth_file_exists':(prepare.PROFILE/'auth.json').exists(),
'shared_resources_match':all((prepare.PROFILE/n).is_symlink() and (prepare.PROFILE/n).resolve()==(prepare.ROOT/n).resolve() for n in m['shared_existing_resources'])}
print(json.dumps(result))
'''

def ssh_read(command, code):
    result = subprocess.run(SSH + [command], input=code.encode(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=40)
    if result.returncode:
        raise SystemExit('Metadata observation did not complete; no service action was requested.')
    return json.loads(result.stdout)

container = ssh_read('docker exec -i --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python -', CODE)
host = ssh_read('python3 -', '''import json,subprocess
repo='/home/ktakahiro150397/repo/backup-secretary'
g=subprocess.run(['git','-C',repo,'--no-optional-locks','status','--short'],capture_output=True,text=True,check=True)
d=subprocess.run(['docker','inspect','--format','{{.Name}}|{{.State.Status}}|{{.State.Health.Status}}','backup-secretary-hermes-owashota','backup-secretary-hermes-main'],capture_output=True,text=True,check=True)
print(json.dumps({'git_status':g.stdout.splitlines(),'containers':d.stdout.splitlines()}))
''')
tests = json.loads((WORK / 'owashota-test-result.txt').read_text(encoding='utf-8').split('RESULT_JSON=', 1)[1].strip())
expected = {' M runtime/main/hermes-data/config.yaml', ' M runtime/owashota/hermes-data/SOUL.md',
            ' M runtime/owashota/hermes-data/config.yaml'}
report = {'at_utc':datetime.now(timezone.utc).isoformat(),'target':'owashota','container':container,
          'host':host,'offline_tests':tests,'original_dirty_paths_preserved':expected<=set(host['git_status']),
          'credential_value_exposed_to_chat':False,'discord_test_posts':0}
(WORK / 'owashota-live-observation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
progress_path = WORK / 'owashota-current-progress.json'
progress = json.loads(progress_path.read_text(encoding='utf-8-sig')) if progress_path.exists() else {}
active = container['controller'].get('state')=='active' and bool(container['sarashina_gateway_pid'])
progress.update(at_utc=report['at_utc'],offline_tests_passed=tests['tests'],live_switch_performed=active,
                key_handoff=container['holder'],api_probe=container['probe'],
                evidence='owashota-live-observation.json',
                pending=[] if active else ['Owner-started key handoff and/or activation remains pending'])
progress_path.write_text(json.dumps(progress, indent=2),encoding='utf-8')
print(json.dumps(report, indent=2))
