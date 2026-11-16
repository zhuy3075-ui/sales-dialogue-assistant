# Bundled source provenance and modifications

- Project: https://github.com/freestylefly/wechat-cli
- Input: user-provided `wechat-cli-main(5).zip`, upstream package version 0.2.4.
- Input SHA256: `280a2d7f31df44c91036ad75691179680adee83d8ba485979e8ff50758351969`.
- Local package version: `0.2.4+sales.1`; modified for sales-dialogue-assistant 2.8.0 on 2026-11-16.
- License: Apache-2.0; original LICENSE retained. Only source, package metadata and license included; original binaries/screenshots omitted.

Changes: optional private state directory; noninteractive multi-account refusal; alias in contact search; explicit plaintext export mode; account-isolated caches and path checks; structured history with source IDs, speaker IDs and stable same-second ordering; missing-shard coverage and empty-history output; explicit PID selection; POSIX private permissions; redacted key diagnostics. macOS automatic re-signing removed and scanner output redirected to the private state directory; scanner binary compiled for selected architecture at install time.

The original command names remain available in the isolated dependency. Agents should use `scripts/wechat_context.py`, which restricts the workflow to one uniquely resolved private contact and does not expose sending or arbitrary commands. Platform implementation is not evidence of cross-platform runtime validation; see integration documentation and verification report.

Additional review fixes: filter verified/service accounts as well as username prefixes; omit raw media XML/transport credentials from structured outputs; explicit empty/partial history; refuse automatic multi-process scanning; correct Windows pointer-sized API signatures; limit the macOS C scanner to the selected database directory and verify extracted candidates against that account's database pages. Scanner extraction paths are not claimed as tested on other operating systems.
