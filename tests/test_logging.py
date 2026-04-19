from pathlib import Path

from localscript.logs import configure_logging, get_logger


def test_configure_logging_writes_to_runtime_logs_directory(tmp_path: Path) -> None:
    log_file = configure_logging(tmp_path)
    logger = get_logger("localscript.test")
    logger.error("backend failure for test")
    for handler in logger.parent.handlers:
        handler.flush()

    assert log_file == tmp_path / "logs" / "localscript.log"
    assert log_file.is_file()
    assert "backend failure for test" in log_file.read_text(encoding="utf-8")
