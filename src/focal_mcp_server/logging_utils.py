from __future__ import annotations

import logging

logger = logging.getLogger("focal_mcp")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("FOCAL MCP %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
