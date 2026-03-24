from pathlib import Path

from backend.eeg_library import EEGFileScanner


def test_folder_scan_only_edf(tmp_path: Path):
    eeg = tmp_path / "eeg"
    eeg.mkdir()
    (eeg / "a.edf").write_bytes(b"1")
    (eeg / "b.EDF").write_bytes(b"2")
    (eeg / "notes.txt").write_text("x")

    files = list(EEGFileScanner(eeg).iter_eeg_files())
    names = sorted([f.name for f in files])
    assert names == ["a.edf", "b.EDF"]
