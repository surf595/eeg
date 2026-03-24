import importlib


def test_default_eeg_data_dir(monkeypatch):
    monkeypatch.delenv("EEG_DATA_DIR", raising=False)
    import backend.config as config
    importlib.reload(config)
    assert str(config.PRIMARY_LIBRARY_PATH).endswith("/eeg")
