# Offline policy files

The Python desktop prototype and local service can load the same validated
policy file. The service can also persist authenticated `/configure` changes.
This is a local research configuration mechanism, not integration with MOSIP's
configuration server or a signed policy distribution service.

Copy `config/policy.example.json` to a private writable location, then set
`MOSIP_PAD_POLICY_FILE` to that file before launching either application.
The example uses strict ONNX mode and includes all three workflow policies.
Runtime model paths and API tokens are not included in policy documents.

```powershell
$env:MOSIP_PAD_POLICY_FILE = 'D:\FacePAD\policy.json'
python run_mds_service.py
```

The desktop entry point is `python run_desktop_app.py`. Both applications read
the file on startup. The service writes it after accepted `/configure` requests;
a desktop process already running does not hot-reload changes from another
process. With no environment variable, configuration remains in memory.

The file has schema version 1 and one update for each workflow. Global fields
must agree across those updates. Unknown fields, duplicate/missing workflows,
out-of-range values and disabled mandatory actions are rejected. A malformed
existing file prevents startup rather than silently falling back to a different
policy. A missing file uses the validated defaults until the first accepted
service configuration save.

Writes use a temporary file in the destination directory, flush the data and
replace the destination. A failed save returns HTTP 503 and leaves the running
configuration unchanged. Tests cover read/write round trips, invalid documents,
conflicting global settings, mandatory-action protection and a failed replace
that preserves the original file. This is not a power-loss certification.

The policy file is trusted local input. Keep it under the operator's account
permissions. It does not carry identity credentials or provide online signing,
revocation, policy-server authentication or vendor-specific configuration.
