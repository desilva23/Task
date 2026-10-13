"""python -m datagen [--seed N] [--out DIR] — write the demo store's six CSV files."""

import argparse
from pathlib import Path

from datagen.build import DEFAULT_SEED, STORE_ID, write_store

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
parser.add_argument("--out", type=Path, default=Path("data") / STORE_ID)
args = parser.parse_args()
write_store(args.out, args.seed)
print(f"wrote {args.out} (seed {args.seed})")
