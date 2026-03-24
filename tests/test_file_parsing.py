from pathlib import Path

from backend.parser import BrainWinReader, ReaderFactory


def test_brainwin_parser_fallback(tmp_path: Path):
    f = tmp_path / "subj01_age29_m_baseline_10hz_19ch.edf"
    f.write_bytes(b"0" * 4096)
    parsed = BrainWinReader().parse(f)

    assert parsed.parser_type == "brainwin_like"
    assert parsed.subject_code.startswith("subj01")
    assert parsed.age == "29"
    assert parsed.sex == "M"
    assert parsed.record_type == "baseline"
    assert parsed.stimulation_frequency == "10"


def test_reader_factory_returns_reader(tmp_path: Path):
    f = tmp_path / "x.edf"
    f.write_bytes(b"1")
    reader = ReaderFactory().create(f)
    assert reader is not None
