import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # httpx logs every request URL at INFO; keep OpenAI/Chroma traffic quiet.
    logging.getLogger("httpx").setLevel(logging.WARNING)
