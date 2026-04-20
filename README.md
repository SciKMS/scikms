# scikms

A PyQt6 application scaffold extracted from [FeelUOwn](https://github.com/feeluown/FeelUOwn).

## What's in the box

- `scikms/app/` — app lifecycle modes (cli / gui / server / mixed) via `AppMode`
- `scikms/plugin.py` — module-based plugin loader (filesystem + entry points)
- `scikms/fuoexec/` — DSL parser and evaluator (lexer / parser / eval)
- `scikms/i18n/` — Mozilla Fluent-based internationalization
- `scikms/serializers/` — abstract `Serializer` / `Deserializer` registry
- `scikms/server/` — DSL + JSON-RPC + pub/sub TCP server (bring your own handler)
- `scikms/utils/` — signals, async helpers, caching, reader pattern, Qt compat
- `scikms/gui/` — PyQt6 scaffolding: theme, hotkeys, drawers, widgets, components, assets
- `tests/` — pytest scaffold (asyncio + qt + mock + cov)

## What was stripped (music-player code from FeelUOwn)

`player/`, `local/`, `library/`, `nowplaying/`, `webserver/`, `entry_points/`, `ai/`, `mpv.py`, `mcpserver.py`, `media.py`, `collection.py`, `argparser.py`, music-specific widgets/components/pages, music serializers, music server handlers, PyInstaller bundling, integration tests, music assets.

## Requirements

- Python `>=3.10`
- `uv` (see [installation](https://docs.astral.sh/uv/getting-started/installation/))

## Quickstart

```sh
uv sync
uv run pytest
```

## Wire your own entry point

```python
# scikms/__main__.py
def main() -> None:
    ...  # build your app
```

Expose it in `pyproject.toml` under `[project.scripts]`.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE) for full text and attribution to
FeelUOwn (scaffold), SciKMS v3.1 / y-khoa (domain), and PyQt6-Fluent-Widgets
(UI styling — also GPL-3.0).
