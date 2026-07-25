import gzip
from pathlib import Path

import pytest

from slatesignal.pipelines.actuals import parse_wikipedia_usd_gross
from slatesignal.pipelines.buzz import _growth, _timeline_values, _youtube_id
from slatesignal.pipelines.imdb import ImdbDatasetSync


@pytest.mark.parametrize(
    ("wikitext", "expected"),
    [
        ("{{Infobox film\n| gross = $402.2 million\n}}", 402_200_000),
        ("{{Infobox film\n|gross={{US$|1.92|billion}}\n}}", 1_920_000_000),
        ("{{Infobox film\n| gross = US$51,092,296<ref>x</ref>\n}}", 51_092_296),
    ],
)
def test_wikipedia_parser_accepts_only_explicit_single_usd_amounts(
    wikitext: str,
    expected: float,
) -> None:
    assert parse_wikipedia_usd_gross(wikitext) == expected


def test_wikipedia_parser_rejects_ranges_and_non_usd_values() -> None:
    assert parse_wikipedia_usd_gross("{{Infobox film\n| gross = $50-80 million\n}}") is None
    assert parse_wikipedia_usd_gross("{{Infobox film\n| gross = EUR 20 million\n}}") is None


def test_buzz_helpers_preserve_real_source_counts() -> None:
    payload = {
        "timeline": [
            {
                "data": [
                    {"value": "2"},
                    {"value": 5},
                    {"value": "not-a-number"},
                ]
            }
        ]
    }

    assert _timeline_values(payload) == [2.0, 5.0]
    assert _growth(14, 7) == 1
    assert _youtube_id("https://www.youtube.com/watch?v=abcDEF_123") == "abcDEF_123"


def test_imdb_reader_selects_only_requested_canonical_ids(tmp_path: Path) -> None:
    dataset = tmp_path / "title.basics.tsv.gz"
    with gzip.open(dataset, "wt", encoding="utf-8", newline="") as handle:
        handle.write("tconst\tprimaryTitle\truntimeMinutes\n")
        handle.write("tt0000001\tFirst Film\t90\n")
        handle.write("tt0000002\tSecond Film\t110\n")

    rows = ImdbDatasetSync._matching_rows(
        dataset,
        "tconst",
        {"tt0000002"},
    )

    assert list(rows) == ["tt0000002"]
    assert rows["tt0000002"]["primaryTitle"] == "Second Film"
