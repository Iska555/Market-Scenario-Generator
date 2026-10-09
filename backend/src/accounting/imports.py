"""Reviewed canonical CSV; deliberately does not guess undocumented broker layouts."""

import csv
import io

from pydantic import ValidationError

from src.accounting.contracts import Batch, CsvImport, TransactionCreate


def parse_csv(request: CsvImport) -> Batch:
    allowed = set(TransactionCreate.model_fields) - {"source"}
    try:
        reader = csv.DictReader(io.StringIO(request.csv_text.lstrip("\ufeff")), strict=True)
        headers = reader.fieldnames or []
        required = {"type", "effective_at", "currency", "external_reference"}
        if (
            not required.issubset(headers)
            or len(headers) != len(set(headers))
            or not set(headers).issubset(allowed)
        ):
            raise ValueError(
                "Use canonical CSV headers; native Lightyear layout is not yet verified"
            )
        rows: list[TransactionCreate] = []
        for row in reader:
            if len(rows) >= 1000:
                raise ValueError("CSV exceeds 1000 transactions")
            if None in row or None in row.values():
                raise ValueError(f"CSV line {reader.line_num}: field count does not match header")
            try:
                rows.append(
                    TransactionCreate.model_validate(
                        {key: value for key, value in row.items() if value.strip()}
                        | {"source": request.source}
                    )
                )
            except ValidationError as exc:
                raise ValueError(
                    f"CSV line {reader.line_num}: invalid or unsupported transaction fields"
                ) from exc
        return Batch(expected_version=request.expected_version, transactions=rows)
    except csv.Error as exc:
        raise ValueError("Malformed CSV quoting or record length") from exc
