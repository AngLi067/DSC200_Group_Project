"""Strict CSV structure checks, source fingerprints, and atomic JSON output."""

import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .contracts import SCHEMAS


def write_json(path: Path, value) -> None:
    """Replace one complete JSON document; preserve the old file on failure."""
    path = Path(path)
    payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def file_signature(path: Path) -> tuple[int, int, int, int]:
    stat = Path(path).stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def fingerprint(path: Path) -> dict:
    path = Path(path)
    before = file_signature(path)
    digest = hashlib.sha256()
    newlines, byte_count, last = 0, 0, b""
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
            newlines += chunk.count(b"\n")
            byte_count += len(chunk)
            last = chunk[-1:]
    if before != file_signature(path):
        raise ValueError(f"Source file changed while hashing: {path.name}")
    # Physical lines are NOT CSV record counts (quoted fields can contain newlines).
    return {"filename": path.name, "bytes": byte_count, "sha256": digest.hexdigest(),
            "physical_lines": newlines + int(bool(last) and last != b"\n")}


def read_rows(path: Path):
    """Yield (ending physical line, row); allow reordered columns and a UTF-8 BOM."""
    path = Path(path)
    expected = SCHEMAS[path.name]
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)):
            raise ValueError(f"{path.name}: duplicate column names")
        missing, extra = set(expected) - set(header), set(header) - set(expected)
        if missing or extra:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}; unexpected columns {sorted(extra)}")
        for values in reader:
            if not values:  # Empty physical lines are not data records.
                continue
            if len(values) != len(header):
                raise ValueError(f"{path.name} line {reader.line_num}: expected {len(header)} fields, got {len(values)}")
            yield reader.line_num, dict(zip(header, values))
