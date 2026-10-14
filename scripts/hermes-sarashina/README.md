# owashota Sarashina switch

Code-only deployment and recovery helpers for the existing `hermes-owashota`
Compose service. The main bot and Windows-native Hermes are outside this scope.

Read [the runbook](owashota-sarashina/RUNBOOK.md) before using these helpers.
The operator's existing credential file is deliberately excluded from Git and
every code bundle. The helper sends its value on encrypted SSH stdin only;
the live proxy keeps the credential in memory.

From a Windows checkout with the existing `yanelmoserver` SSH alias:

```powershell
python .\run_owashota_bundle.py test
python .\run_owashota_bundle.py key-test
# For a previously prepared inactive profile after a reviewed code change:
python .\run_owashota_bundle.py refresh
& .\Submit-OwashotaSarashinaKey.ps1 -EnvFile '<existing dedicated env file>'
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes yanelmoserver 'docker exec --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/key_entry.py proceed'
python .\observe_owashota.py
```

Initial preparation uses `preview`, then `apply`, then `key-install`; it refuses
to overwrite an existing profile. Do not use `apply` to update an existing one.

Activation requires valid HTTP/text and a streamed function/result round trip
before stopping Codex. The native Hermes file-tool path is also covered by the
offline suite. The controller validates the original PID against machine-readable
s6 output and writes its planned-stop marker explicitly, since the installed
Hermes text parser does not recognize s6's `pgid` field. An exited zombie
controller cannot block a retry. No blanket provider/tool reduction is applied.

Restore needs no Sarashina credential:

```powershell
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes yanelmoserver 'docker exec --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/control.py restore'
```

Runtime configuration, memories, conversation databases, manifests, logs and
credentials are not part of this source bundle. See [validation](VALIDATION.md)
for what was exercised and the remaining operational limitations.
