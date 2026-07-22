import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, SKOS

from stages.convert import COMPOUND, ENDPOINT, convert


def fixture(path: Path):
    pq.write_table(pa.Table.from_pylist([
        {"no": 113, "chemical_name": "n-Hexane", "cas_number": "110-54-3",
         "classification": "Flam. Liq. 2 | Repr. 2", "hazard_statement_codes": "H225, H361f",
         "signal_word": "Danger"},
        {"no": 114, "chemical_name": "broken", "cas_number": "not-a-cas",
         "classification": "Acute Tox. 4", "hazard_statement_codes": "H302", "signal_word": "Warning"},
        {"no": 229, "chemical_name": "appendix bleed", "cas_number": "7440-67-7",
         "classification": " | ".join(f"fragment-{n}" for n in range(51)),
         "hazard_statement_codes": "H000", "signal_word": "Danger"},
    ]), path)


def test_conversion_counts_and_parses(tmp_path):
    source, output, report = tmp_path / "source.parquet", tmp_path / "out.nt", tmp_path / "report.json"
    fixture(source)
    result = convert(source, output, report)
    assert result["source"]["eligible_rows"] == 1
    assert result["source"]["excluded_rows"] == 2
    assert result["rdf"]["classification_observations"] == 2
    graph = Graph().parse(output, format="nt")
    assert len(graph) == result["rdf"]["triples"]
    assert json.loads(report.read_text()) == result


def test_standard_n_hexane_identifiers(tmp_path):
    source, output = tmp_path / "source.parquet", tmp_path / "out.nt"
    fixture(source)
    convert(source, output, tmp_path / "report.json")
    graph = Graph().parse(output, format="nt")
    compound = URIRef(COMPOUND + "110-54-3")
    assert (compound, SKOS.notation, None) in graph
    assert (compound, OWL.sameAs, URIRef("http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID8058")) in graph
    assert sum(1 for _ in graph.subjects(RDF.type, ENDPOINT)) == 2


def test_deduplication_contract():
    root = Path(__file__).parents[1]
    decisions = json.loads((root / "health/deduplication.json").read_text())["source_tables"]
    assert decisions["korea_ghs"]["existing_graph"] == "korea-ghs-kg"
    assert decisions["australia_ghs"]["existing_graph"] == "pubchem-ghs-kg"
    assert decisions["malaysia_ghs"]["decision"] == "included-distinct-jurisdiction"
