# Third-party components

## WeChat CLI

Source: https://github.com/freestylefly/wechat-cli . The user-provided source package identifies version 0.2.4 and includes Apache License 2.0. Bundled source, license and modification record are in `vendor/wechat-cli/`. Local changes are identified as `0.2.4+sales.1`. Upstream authors retain their rights; this project does not claim authorship of their work.

## ChatLab CLI

Source: https://github.com/ChatLab/ChatLab . Reviewed source commit: `bb292e35a00d68132de203e8b2d52e2d7e74dcd3`. Installer selects npm `chatlab-cli@0.37.7`, distributed under AGPL-3.0. ChatLab source and binaries are not embedded in this Skill; npm installs it into the user's separate runtime and its license remains there. The Skill invokes the documented CLI in a separate process. See upstream license for obligations when modifying or redistributing that program; this notice does not relicense it.

## Runtime dependencies

Pinned Python runtime dependencies: Click 8.3.1 (BSD-3-Clause), PyCryptodome 3.23.0 (upstream BSD/public-domain terms), Zstandard 0.25.0 (BSD-3-Clause). npm direct and transitive versions/integrities are recorded in `assets/wechat-runtime/package-lock.json`; individual package licenses remain in the installed runtime. Optional bootstrap downloads Node.js 24.11.1 and uv 0.7.22 from their official distributions with SHA256 verification; Python can be managed by uv. No runtime executables, account credentials or chat data are included in the distributable Skill.
