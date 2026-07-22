# foreign-ghs-classifications-rdf

RDF for the distinct Malaysian evidence in the pinned
`foreign-ghs-classifications` source brick. The graph contains 228 eligible
chemicals from Malaysia DOSH's 2014 Industry Code of Practice, with one
observation per assigned GHS hazard classification. One final Zirconium row is
explicitly excluded because the PDF extractor folded the document's
3,252-fragment classification-code appendix into that row.

Australia and Korea are deliberately not copied. The Australia HCIS evidence is
already represented by `pubchem-ghs-kg`; the 2,500-row Korea table is the source
used by `korea-ghs-kg`. This repository therefore prevents duplicated assertions
while adding the previously absent Malaysian jurisdiction.

The source PDF states Department of Occupational Safety and Health copyright and
does not state an open redistribution license. The transformation code, tests,
and aggregate health reports are public, but publishing the derived RDF artifact
requires a reuse/licensing decision. This is tracked as an artifact-publication
blocker rather than as a failed transformation.

Each classification observation reuses the shared GHS endpoint class,
`IAO:0000136` (*is about*), `rdf:value`, `bb:classification`, DCTERMS, and PROV.
Compound nodes carry CAS Registry Numbers as `skos:notation`. n-Hexane additionally
links to PubChem CID 8058 and carries standard InChIKey
`VLKZOEOYAKHREP-UHFFFAOYSA-N`.

Build against a checked-out source brick:

```sh
uv run python stages/convert.py --source /path/to/foreign-ghs-classifications/brick/malaysia_ghs.parquet
uv run pytest
```

Latest local build: 228/228 eligible rows, one explicitly excluded parse-failure
row, 1,186 classification observations, and 18,600 distinct parsed triples.
All six source fields are represented; ontology health scores 85 with no novel
classes or predicates. The
Australia and Korea exclusions are recorded in `health/deduplication.json`.
