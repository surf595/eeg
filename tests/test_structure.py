from pathlib import Path


def test_required_dirs_exist():
    required = ["frontend", "backend", "workers", "shared", "tests", "docs", "eeg"]
    for name in required:
        assert Path(name).exists(), f"Missing required directory: {name}"
