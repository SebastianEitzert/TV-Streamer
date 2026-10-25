# Contributing

Thanks for helping! Bug reports, test results with other TVs and pull requests are welcome.

## Reporting TV results
The TV type presets only contain settings confirmed on real TVs. If you run TV Streamer on another model, please open an
issue with the template "TV report": model, webOS version, video path (MSE / WebRTC / Moonlight), picture size and what
worked.

## Development
```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```
- Home Assistant integration: `custom_components/tv_streamer/`
- Streamer image: `custom_components/tv_streamer/streamer/` (build: `docker build custom_components/tv_streamer/streamer`)
- User-facing texts exist in English and German (`translations/en.json`, `translations/de.json`, `README.md`,
  `README.de.md`) – please update both.
- Never commit IP addresses, tokens or other personal data. Use example addresses like `192.168.1.42`.

## Pull requests
Keep them focused, describe what you tested, and add an entry to `CHANGELOG.md`.
