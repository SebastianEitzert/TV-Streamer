# Security

Please report vulnerabilities privately via GitHub: *Security → Report a vulnerability*. Do not open a public issue.

## Design notes
- The VM fetches its configuration and the streamer image from Home Assistant with its own **VM token**
  (`Authorization: Bearer …`), not with a Home Assistant user. The token is created per config entry and only shown in
  *Configure → VM setup*.
- The streamer pages on the VM (`http://<vm>:8091/` …) have **no password**: anyone in your LAN who opens them sees and
  controls the logged-in browser. Restrict access with the `ALLOW` setting or your firewall, and use a dedicated Home
  Assistant user with limited rights for the TVs.
- LG developer mode session tokens are stored in the Home Assistant config entry only, never in logs, diagnostics or the
  compose file. Home Assistant keeps config entries unencrypted in `.storage/` – protect your backups.
- Downloads in the streamer image (go2rtc, PyAV, Sunshine) are pinned to a version and verified with SHA-256.
