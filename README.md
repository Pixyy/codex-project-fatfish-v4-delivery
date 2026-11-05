# codex-project-fatfish-v4-delivery

# FatFish v4 — preserved Codex project

This is a preservation copy of the completed project. The original workspace was not modified and the original implementation tasks were not rerun.

- `fatfish/`: complete project source, tests, assets, documentation and original directory layout. Start with `fatfish/README.md`.
- `generated_images/`: original generated artwork.
- `library-files/`: the original final v4 delivery ZIP, standalone interactive HTML introduction, one-page PDF, demonstration video and SHA-256 checksums.

## Run

Requires Python 3.10+ (64-bit). From `fatfish/`, run `python launcher.py` for the control panel, or `python launcher.py --desktop` for the desktop pet (first launch installs optional Qt components). DeepSeek credentials are configured locally through the UI.

## Privacy and licensing

Runtime `data/`, API keys, credentials, chat history, environment files, caches, temporary workspaces and duplicate ZIP archives are excluded; the final v4 delivery ZIP is preserved. Documentation and tests may contain explicitly fake/example credential strings; they are not live keys.

Code and character assets have separate licenses. Preserve `fatfish/ATTRIBUTION.md` and `fatfish/references/licenses/`. Community character assets are for noncommercial use under their applicable licenses; a private repository does not change those terms.
