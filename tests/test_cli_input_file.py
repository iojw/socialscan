import asyncio

import pytest

from socialscan import cli


def test_missing_input_file_is_usage_error_not_traceback(monkeypatch, capsys):
    missing = "does-not-exist-xyz.txt"
    monkeypatch.setattr("sys.argv", ["socialscan", "--input", missing])

    with pytest.raises(SystemExit) as excinfo:
        asyncio.run(cli.main())

    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert missing in err
    assert "Traceback" not in err
