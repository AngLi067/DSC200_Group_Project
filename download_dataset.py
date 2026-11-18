"""Download the Retailrocket e-commerce dataset with KaggleHub."""

import argparse
from pathlib import Path
import shutil

import kagglehub

from retailrocket_tools.contracts import SCHEMAS

DATASET_HANDLE = "retailrocket/ecommerce-dataset"
EXPECTED_FILES = set(SCHEMAS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/retailrocket"))
    parser.add_argument("--source-dir", type=Path, help="Reuse an existing dataset directory without downloading")
    args = parser.parse_args()
    if args.source_dir is not None:
        dataset_path = args.source_dir.expanduser().resolve()
    else:
        dataset_path = Path(kagglehub.dataset_download(DATASET_HANDLE)).expanduser().resolve()
    print(f"Dataset cache path: {dataset_path}")

    found = {path.name: path for path in dataset_path.rglob("*.csv")}
    missing = sorted(EXPECTED_FILES - found.keys())
    if missing:
        parser.error(f"Expected CSV files not found: {', '.join(missing)}")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(EXPECTED_FILES):
        destination = output_dir / name
        if found[name].resolve() != destination.resolve():
            shutil.copy2(found[name], destination)
    print(f"All four dataset CSV files are ready in: {output_dir}")


if __name__ == "__main__":
    main()
