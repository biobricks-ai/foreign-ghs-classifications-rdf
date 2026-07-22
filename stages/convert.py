#!/usr/bin/env python3
"""Convert only the distinct Malaysia DOSH GHS table to deterministic N-Triples."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pyarrow.parquet as pq
from rdflib import Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS
from rdflib.plugins.serializers.nt import _quoteLiteral

ROOT = Path(__file__).parents[1]
DEFAULT_SOURCE = Path("/mnt/raid2/biobricks/foreign-ghs-classifications/brick/malaysia_ghs.parquet")
OUT = ROOT / "brick/foreign-ghs-classifications-rdf.nt"
REPORT = ROOT / "reports/source-coverage.json"
BASE = "https://biobricks.ai/malaysia-ghs/"
COMPOUND = "https://biobricks.ai/compound/unmapped/cas/"
ENDPOINT = URIRef("https://biobricks.ai/endpoint/ghs-hazard-classification")
CLASSIFICATION = URIRef("https://biobricks.ai/ontology/classification")
IS_ABOUT = URIRef("http://purl.obolibrary.org/obo/IAO_0000136")
CHEMINF_KEY = URIRef("http://semanticscience.org/resource/CHEMINF_000059")
SOURCE = URIRef("https://dosh.gov.my/en/pengurusan-kimia/")
REPO = URIRef("https://github.com/biobricks-ai/foreign-ghs-classifications-rdf")
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def nt(term):
    return f"<{term}>" if isinstance(term, URIRef) else _quoteLiteral(term)


def valid_cas(value: str) -> bool:
    if not CAS_RE.match(value):
        return False
    first, second, check = value.split("-")
    digits = first + second
    return int(check) == sum((i + 1) * int(d) for i, d in enumerate(reversed(digits))) % 10


def items(value: object, separator: str) -> list[str]:
    if value is None:
        return []
    return [x.strip() for x in str(value).split(separator) if x.strip()]


def convert(source: Path, output: Path = OUT, report: Path = REPORT) -> dict:
    rows = pq.read_table(source).to_pylist()
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    triples: set[tuple[object, object, object]] = set()

    def add(s, p, o):
        triples.add((s, p, o))

    add(ENDPOINT, RDF.type, OWL.Class)
    add(ENDPOINT, RDFS.subClassOf, URIRef("http://purl.obolibrary.org/obo/IAO_0000030"))
    add(ENDPOINT, RDFS.label, Literal("GHS hazard classification"))
    eligible = excluded = observations = identifier_rows = 0
    mapped_cells = total_cells = eligible_cells = 0

    for row in rows:
        populated = sum(v is not None and str(v).strip() != "" for v in row.values())
        total_cells += populated
        cas = str(row.get("cas_number") or "").strip()
        classes = items(row.get("classification"), "|")
        # The final PDF-extracted row absorbs the document's classification-code
        # appendix (3,252 fragments). Count it as a parse failure, not evidence.
        if not valid_cas(cas) or not classes or len(classes) > 50:
            excluded += 1
            continue
        eligible += 1
        identifier_rows += 1
        eligible_cells += populated
        mapped_cells += populated
        name = str(row.get("chemical_name") or "").strip()
        number = str(row.get("no") or "").strip()
        hcodes = items(row.get("hazard_statement_codes"), ",")
        signal = str(row.get("signal_word") or "").strip()
        compound = URIRef(COMPOUND + cas)
        add(compound, RDF.type, URIRef("http://purl.obolibrary.org/obo/CHEBI_24431"))
        add(compound, SKOS.notation, Literal("CAS-RN:" + cas))
        if name:
            add(compound, RDFS.label, Literal(name))
        if cas == "110-54-3":
            add(compound, OWL.sameAs, URIRef("http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID8058"))
            add(compound, CHEMINF_KEY, Literal("VLKZOEOYAKHREP-UHFFFAOYSA-N"))
        for index, classification in enumerate(classes):
            digest = hashlib.sha256(f"{number}|{cas}|{classification}|{index}".encode()).hexdigest()[:20]
            obs = URIRef(BASE + "classification/" + digest)
            add(obs, RDF.type, ENDPOINT)
            add(obs, RDFS.label, Literal(f"Malaysia GHS classification for {name or cas}: {classification}"))
            add(obs, IS_ABOUT, compound)
            add(obs, RDF.value, Literal(classification))
            add(obs, CLASSIFICATION, Literal(classification))
            for code in hcodes:
                add(obs, SKOS.notation, Literal(code))
            if signal:
                add(obs, RDFS.comment, Literal("Signal word: " + signal))
            add(obs, DCTERMS.identifier, Literal(f"MY-ICOP-2014:{number}:{index + 1}"))
            add(obs, DCTERMS.source, SOURCE)
            add(obs, PROV.wasDerivedFrom, REPO)
            observations += 1

    ordered = sorted(triples, key=lambda t: tuple(str(x) for x in t))
    with output.open("w") as stream:
        for s, p, o in ordered:
            stream.write(f"{nt(s)} {nt(p)} {nt(o)} .\n")
    result = {
        "source": {"tables": 1, "rows": len(rows), "eligible_rows": eligible,
                   "excluded_rows": excluded, "nonempty_cells": total_cells},
        "rdf": {"triples": len(ordered), "classification_observations": observations},
        "coverage": {"record_count_coverage": eligible / eligible if eligible else 0,
                     "identifier_row_coverage": identifier_rows / eligible if eligible else 0,
                     "mapped_cell_coverage": mapped_cells / eligible_cells if eligible_cells else 0},
        "deduplication": {"included_table": "malaysia_ghs",
                          "excluded_existing_tables": ["australia_ghs", "korea_ghs"]},
    }
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    print(json.dumps(convert(args.source), indent=2))
