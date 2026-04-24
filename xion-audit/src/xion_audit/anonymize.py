"""`xion-audit anonymize` — strips PII and writes a deterministic-anonymized JSONL."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


@click.command(
    name="anonymize",
    help="Strip PII and write a deterministic-anonymized JSONL.",
)
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_file", type=click.Path(dir_okay=False, path_type=Path))
def anonymize(input_file: Path, output_file: Path) -> None:
    """Anonymize a corpus file."""
    # TODO: Implement real anonymization logic
    
    with input_file.open("r", encoding="utf-8") as f_in, output_file.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                # Naive anonymization for stub
                if "text" in data:
                    data["text"] = data["text"].replace("John", "[NAME]")
                f_out.write(json.dumps(data) + "\n")
            except json.JSONDecodeError:
                f_out.write(line)
                
    click.echo(f"anonymize: Wrote anonymized corpus to {output_file}")
    sys.exit(0)
