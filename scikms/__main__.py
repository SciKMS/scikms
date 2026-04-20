"""Allow running the package with ``python -m scikms``."""


def main() -> None:
    raise SystemExit(
        "scikms has no default entry point. Wire your own in pyproject.toml "
        "under [project.scripts], or implement main() here."
    )


if __name__ == "__main__":
    main()
