"""Behaviour of the standalone skill validator scripts.

Each skill ships its ``scripts/`` directory on its own, so the four validators are
stdlib-only and self-contained. They are exercised here the way a user runs them:
as a subprocess over files written into ``tmp_path``.
"""

import gzip
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "skills"

ACCESSIBILITY = SKILLS / "accessibility-aggregation" / "scripts" / "validate_peaks.py"
HISTONE = SKILLS / "histone-aggregation" / "scripts" / "validate_peaks.py"
LOOPS = SKILLS / "hic-aggregation" / "scripts" / "validate_loops.py"
METHYLATION = SKILLS / "methylation-aggregation" / "scripts" / "validate_methylation.py"


def run_script(script, *args):
    """Run a validator script and return its exit code and combined output."""
    result = subprocess.run(
        [sys.executable, str(script), *[str(arg) for arg in args]],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def as_tsv(rows):
    return "".join("\t".join(str(field) for field in row) + "\n" for row in rows)


def write_lines(path, rows):
    path.write_text(as_tsv(rows))
    return path


def write_gzipped(path, rows):
    with gzip.open(path, "wt") as handle:
        handle.write(as_tsv(rows))
    return path


def narrow_peak_row(chrom="chr1", start=1000, end=1200, signal=5.0, pvalue=10.0, qvalue=5.0):
    """A 10-column narrowPeak record."""
    return [chrom, start, end, "peak", 500, ".", signal, pvalue, qvalue, 100]


def bedpe_row(chr1="chr1", start1=1_000_000, end1=1_010_000, chr2="chr1", start2=1_500_000, end2=1_510_000):
    """A 7-column BEDPE loop record."""
    return [chr1, start1, end1, chr2, start2, end2, 10]


def encode_methyl_row(chrom="chr1", start=1000, end=1001, strand="+", coverage=10, methylation=50):
    """An 11-column ENCODE bedMethyl record (column 11 is a percentage)."""
    return [chrom, start, end, "CpG", 0, strand, start, end, "0,0,0", coverage, methylation]


def minimal_methyl_row(chrom="chr1", start=1000, end=1001, strand="+", coverage=10, methylation=0.5):
    """An 8-column minimal bedMethyl record."""
    return [chrom, start, end, "CpG", 0, strand, coverage, methylation]


# --- C1: the methylation scale is decided once per file ---------------------------------------


def test_methylation_encode_percentages_are_not_rescaled_per_value(tmp_path):
    # Arrange: an ENCODE bedMethyl whose percentages include the values 0 and 1
    path = tmp_path / "encode.bedMethyl"
    percentages = [0, 1, 1, 50, 99, 100, 100]
    write_lines(
        path,
        [
            encode_methyl_row(start=1000 + index * 10, end=1001 + index * 10, methylation=value)
            for index, value in enumerate(percentages)
        ],
    )

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 0, output
    assert re.search(r"25th:\s+1\.0%", output), output
    assert re.search(r"Median:\s+50\.0%", output), output
    assert re.search(r"Unmethylated \(0-10%\)\s+3\b", output), output
    assert re.search(r"Methylated \(90-100%\)\s+3\b", output), output
    assert "Mixed" not in output, output


def test_methylation_minimal_fraction_file_is_converted_to_percent(tmp_path):
    # Arrange: a genuine 0-1 fraction file in the 8-column minimal layout
    path = tmp_path / "fraction.bedMethyl"
    fractions = [0.0, 0.25, 0.5, 0.75, 1.0]
    write_lines(
        path,
        [
            minimal_methyl_row(start=1000 + index * 10, end=1001 + index * 10, methylation=value)
            for index, value in enumerate(fractions)
        ],
    )

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 0, output
    assert re.search(r"Median:\s+50\.0%", output), output
    assert re.search(r"Max:\s+100\.0%", output), output
    assert "fraction" in output, output


def test_methylation_scale_fraction_rejects_a_value_above_one(tmp_path):
    # Arrange: percentages in a file the user declares to be fractions
    path = tmp_path / "percent.bedMethyl"
    write_lines(path, [encode_methyl_row(methylation=50), encode_methyl_row(start=1010, end=1011, methylation=99)])

    # Act
    code, output = run_script(METHYLATION, path, "--scale", "fraction")

    # Assert
    assert code == 1, output
    assert "> 1" in output, output


def test_methylation_scale_percent_overrides_the_automatic_decision(tmp_path):
    # Arrange: a 0-1 file the user declares to already be percentages
    path = tmp_path / "fraction.bedMethyl"
    fractions = [0.0, 0.25, 0.5, 0.75, 1.0]
    write_lines(
        path,
        [
            minimal_methyl_row(start=1000 + index * 10, end=1001 + index * 10, methylation=value)
            for index, value in enumerate(fractions)
        ],
    )

    # Act
    code, output = run_script(METHYLATION, path, "--scale", "percent")

    # Assert
    assert code == 0, output
    assert re.search(r"Median:\s+0\.5%", output), output


# --- H2, H3: a reversed record is an error and enters no statistic ------------------------------


def test_histone_reversed_peak_is_excluded_from_size_statistics(tmp_path):
    # Arrange: three good peaks and one whose start is past its end
    path = tmp_path / "reversed.narrowPeak"
    write_lines(
        path,
        [
            narrow_peak_row(start=1000, end=1200),
            narrow_peak_row(start=2000, end=2200),
            narrow_peak_row(start=3000, end=3200),
            narrow_peak_row(start=9000, end=8000),
        ],
    )

    # Act
    code, output = run_script(HISTONE, path)

    # Assert
    assert code == 1, output
    assert "start (9000) >= end (8000)" in output, output
    assert "-1,000" not in output, output
    assert re.search(r"Valid peaks:\s+3", output), output


def test_loops_reversed_anchor_is_excluded_from_resolution_candidates(tmp_path):
    # Arrange: two good loops and one whose first anchor is reversed
    path = tmp_path / "reversed.bedpe"
    write_lines(
        path,
        [
            bedpe_row(start1=1_000_000, end1=1_010_000, start2=1_500_000, end2=1_510_000),
            bedpe_row(start1=2_000_000, end1=2_005_000, start2=2_500_000, end2=2_505_000),
            bedpe_row(start1=3_010_000, end1=3_000_000, start2=3_500_000, end2=3_525_000),
        ],
    )

    # Act
    code, output = run_script(LOOPS, path)

    # Assert
    assert code == 1, output
    assert "-10,000" not in output, output
    assert re.search(r"Valid loops:\s+2", output), output


def test_methylation_reversed_record_is_excluded_from_statistics(tmp_path):
    # Arrange: two good CpGs and one with reversed coordinates
    path = tmp_path / "reversed.bedMethyl"
    write_lines(
        path,
        [
            encode_methyl_row(start=1000, end=1001),
            encode_methyl_row(start=1010, end=1011),
            encode_methyl_row(start=2000, end=1000),
        ],
    )

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 1, output
    assert re.search(r"Valid CpGs:\s+2", output), output
    assert re.search(r"chr1\s+2\s+\(100\.0%\)", output), output


# --- M2: the suppression notice tells the truth -------------------------------------------------


@pytest.mark.parametrize(
    "script, filename, good_row, short_row",
    [
        (ACCESSIBILITY, "peaks.narrowPeak", narrow_peak_row(), ["chr1", 5000, 5200]),
        (HISTONE, "peaks.narrowPeak", narrow_peak_row(), ["chr1", 5000, 5200]),
        (LOOPS, "loops.bedpe", bedpe_row(), ["chr1", 5000, 5200]),
        (METHYLATION, "cpgs.bedMethyl", encode_methyl_row(), ["chr1", 5000, 5001]),
    ],
    ids=["accessibility", "histone", "loops", "methylation"],
)
def test_column_count_errors_stop_after_five_details(tmp_path, script, filename, good_row, short_row):
    # Arrange: one well-formed record so the layout is known, then eight truncated ones
    path = tmp_path / filename
    write_lines(path, [good_row] + [short_row] * 8)

    # Act
    code, output = run_script(script, path)

    # Assert
    assert code == 1, output
    assert len(re.findall(r"Line \d+: expected .*columns", output)) == 5, output
    assert output.count("suppressing further column-count errors") == 1, output


# --- M3: per-record tables are a share of the valid records -------------------------------------


def test_accessibility_chromosome_percentages_use_the_valid_peak_count(tmp_path):
    # Arrange: three good peaks and one truncated line
    path = tmp_path / "mixed.narrowPeak"
    rows = [narrow_peak_row(start=1000 + index * 100, end=1200 + index * 100) for index in range(3)]
    write_lines(path, rows + [["chr1", 5000, 5200]])

    # Act
    code, output = run_script(ACCESSIBILITY, path)

    # Assert
    assert code == 1, output
    assert re.search(r"Data lines:\s+4", output), output
    assert re.search(r"Valid peaks:\s+3", output), output
    assert re.search(r"Malformed lines:\s+1", output), output
    assert re.search(r"chr1\s+3\s+\(100\.0%\)", output), output


def test_loops_cis_percentage_uses_the_valid_loop_count(tmp_path):
    # Arrange: three good cis loops and one truncated line
    path = tmp_path / "mixed.bedpe"
    rows = [
        bedpe_row(
            start1=1_000_000 + index * 100_000,
            end1=1_010_000 + index * 100_000,
            start2=1_500_000 + index * 100_000,
            end2=1_510_000 + index * 100_000,
        )
        for index in range(3)
    ]
    write_lines(path, rows + [["chr1", 5000, 5200]])

    # Act
    code, output = run_script(LOOPS, path)

    # Assert
    assert code == 1, output
    assert re.search(r"Valid loops:\s+3", output), output
    assert "Cis loops (same chromosome): 3 (100.0%)" in output, output


def test_methylation_strand_percentages_use_the_valid_cpg_count(tmp_path):
    # Arrange: three good CpGs (two forward, one reverse) and one truncated line
    path = tmp_path / "mixed.bedMethyl"
    rows = [
        encode_methyl_row(start=1000, end=1001, strand="+"),
        encode_methyl_row(start=1010, end=1011, strand="+"),
        encode_methyl_row(start=1020, end=1021, strand="-"),
    ]
    write_lines(path, rows + [["chr1", 5000, 5001]])

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 1, output
    assert re.search(r"Valid CpGs:\s+3", output), output
    assert re.search(r"\+\s+2\s+\(\s*66\.7%\)", output), output


# --- M4: an invalid chromosome is one malformed line, and the row is skipped --------------------


def test_loops_row_with_two_invalid_chromosomes_counts_one_malformed_line(tmp_path):
    # Arrange: one good loop and one whose anchors both name a chromosome without the chr prefix
    path = tmp_path / "badchrom.bedpe"
    write_lines(path, [bedpe_row(), bedpe_row(chr1="1", chr2="2")])

    # Act
    code, output = run_script(LOOPS, path)

    # Assert
    assert code == 1, output
    assert re.search(r"Malformed lines:\s+1", output), output
    assert re.search(r"Valid loops:\s+1", output), output


# --- M5: only the two documented bedMethyl layouts are accepted ---------------------------------


def test_methylation_rejects_a_nine_column_layout(tmp_path):
    # Arrange: nine columns is neither the minimal nor the ENCODE layout
    path = tmp_path / "nine.bedMethyl"
    write_lines(path, [["chr1", 1000, 1001, "CpG", 0, "+", 1000, 1001, "0,0,0"]])

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 1, output
    assert "got 9" in output, output


def test_methylation_flags_a_line_that_does_not_match_the_detected_layout(tmp_path):
    # Arrange: a minimal file whose second record carries the full ENCODE column set
    path = tmp_path / "drifting.bedMethyl"
    write_lines(path, [minimal_methyl_row(), encode_methyl_row(start=2000, end=2001)])

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 1, output
    assert "expected 8 columns (minimal), got 11" in output, output


# --- L1: an input with no records is an error ---------------------------------------------------


@pytest.mark.parametrize(
    "script, filename",
    [
        (ACCESSIBILITY, "empty.narrowPeak"),
        (HISTONE, "empty.narrowPeak"),
        (LOOPS, "empty.bedpe"),
        (METHYLATION, "empty.bedMethyl"),
    ],
    ids=["accessibility", "histone", "loops", "methylation"],
)
def test_input_without_records_fails_with_a_no_data_rows_error(tmp_path, script, filename):
    # Arrange: a file holding only a comment and a blank line
    path = tmp_path / filename
    path.write_text("# only a comment\n\n")

    # Act
    code, output = run_script(script, path)

    # Assert
    assert code == 1, output
    assert "no data rows" in output.lower(), output


# --- L2, L5: bucket and threshold labels ---------------------------------------------------------


def test_loops_short_range_label_uses_bp_below_one_kilobase(tmp_path):
    # Arrange
    path = tmp_path / "loops.bedpe"
    write_lines(path, [bedpe_row()])

    # Act
    code, output = run_script(LOOPS, path, "--min-distance", "500")

    # Assert
    assert code == 0, output
    assert "<0kb" not in output, output
    assert "500bp" in output, output


def test_methylation_coverage_bucket_label_includes_fifty(tmp_path):
    # Arrange: a CpG whose coverage is exactly the bucket boundary
    path = tmp_path / "coverage.bedMethyl"
    write_lines(path, [encode_methyl_row(coverage=50), encode_methyl_row(start=1010, end=1011, coverage=60)])

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 0, output
    assert ">=50x" in output, output
    assert re.search(r"^\s*>50x", output, re.M) is None, output


def test_loops_distance_bucket_label_includes_five_megabases(tmp_path):
    # Arrange: a loop spanning exactly the bucket boundary
    path = tmp_path / "far.bedpe"
    write_lines(path, [bedpe_row(start1=1_000_000, end1=1_010_000, start2=6_000_000, end2=6_010_000)])

    # Act
    code, output = run_script(LOOPS, path)

    # Assert
    assert code == 0, output
    assert ">= 5Mb" in output, output
    assert re.search(r"^\s*> 5Mb", output, re.M) is None, output


# --- L3, L4: non-standard chromosomes warn, and dropped warnings are counted ---------------------


def test_accessibility_warns_about_a_non_standard_chromosome(tmp_path):
    # Arrange: one primary-assembly peak and one on an unplaced scaffold
    path = tmp_path / "scaffold.narrowPeak"
    write_lines(path, [narrow_peak_row(), narrow_peak_row(chrom="chr1_KI270706v1_random", start=2000, end=2200)])

    # Act
    code, output = run_script(ACCESSIBILITY, path)

    # Assert
    assert code == 0, output
    assert "non-standard chromosome 'chr1_KI270706v1_random'" in output, output


def test_histone_reports_how_many_chromosome_warnings_were_dropped(tmp_path):
    # Arrange: twenty-five scaffold peaks, five more than the warning cap
    path = tmp_path / "scaffolds.narrowPeak"
    write_lines(
        path,
        [
            narrow_peak_row(chrom="chr1_KI270706v1_random", start=1000 + index * 100, end=1200 + index * 100)
            for index in range(25)
        ],
    )

    # Act
    code, output = run_script(HISTONE, path)

    # Assert
    assert code == 0, output
    assert output.count("non-standard chromosome") == 20, output
    assert "5 more" in output, output


# --- L6: quartiles interpolate instead of picking an order statistic ----------------------------


@pytest.mark.parametrize("script", [ACCESSIBILITY, HISTONE], ids=["accessibility", "histone"])
def test_peak_size_quartiles_interpolate_between_neighbouring_peaks(tmp_path, script):
    # Arrange: four peaks of 100, 200, 300 and 400 bp
    path = tmp_path / "even.narrowPeak"
    write_lines(
        path,
        [
            narrow_peak_row(start=10_000 * index, end=10_000 * index + size)
            for index, size in enumerate([100, 200, 300, 400])
        ],
    )

    # Act
    code, output = run_script(script, path)

    # Assert
    assert code == 0, output
    assert re.search(r"25th:\s+175\.0 bp", output), output
    assert re.search(r"Median:\s+250\.0 bp", output), output
    assert re.search(r"75th:\s+325\.0 bp", output), output


def test_methylation_coverage_quartiles_interpolate_between_neighbouring_cpgs(tmp_path):
    # Arrange: four CpGs covered 10x, 20x, 30x and 40x
    path = tmp_path / "coverage.bedMethyl"
    write_lines(
        path,
        [
            encode_methyl_row(start=1000 + index * 10, end=1001 + index * 10, coverage=coverage)
            for index, coverage in enumerate([10, 20, 30, 40])
        ],
    )

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert
    assert code == 0, output
    assert re.search(r"Median:\s+25\.0\b", output), output
    assert re.search(r"75th:\s+32\.5\b", output), output


def test_loops_distance_quartiles_interpolate_between_neighbouring_loops(tmp_path):
    # Arrange: four cis loops 100kb, 200kb, 300kb and 400kb apart
    path = tmp_path / "even.bedpe"
    write_lines(
        path,
        [
            bedpe_row(
                start1=10_000_000 * index,
                end1=10_000_000 * index + 10_000,
                start2=10_000_000 * index + distance,
                end2=10_000_000 * index + distance + 10_000,
            )
            for index, distance in enumerate([100_000, 200_000, 300_000, 400_000])
        ],
    )

    # Act
    code, output = run_script(LOOPS, path)

    # Assert
    assert code == 0, output
    assert re.search(r"Median:\s+250,000\.0 bp", output), output
    assert re.search(r"75th:\s+325,000\.0 bp", output), output


# --- L7: gzipped inputs and blacklists -----------------------------------------------------------


@pytest.mark.parametrize(
    "script, filename, row",
    [
        (ACCESSIBILITY, "peaks.narrowPeak.gz", narrow_peak_row()),
        (HISTONE, "peaks.narrowPeak.gz", narrow_peak_row()),
        (LOOPS, "loops.bedpe.gz", bedpe_row()),
        (METHYLATION, "cpgs.bedMethyl.gz", encode_methyl_row()),
    ],
    ids=["accessibility", "histone", "loops", "methylation"],
)
def test_gzipped_input_is_read(tmp_path, script, filename, row):
    # Arrange
    path = write_gzipped(tmp_path / filename, [row])

    # Act
    code, output = run_script(script, path)

    # Assert
    assert code == 0, output
    assert "RESULT: PASS" in output, output


@pytest.mark.parametrize(
    "script, filename, row",
    [
        (ACCESSIBILITY, "peaks.narrowPeak", narrow_peak_row()),
        (HISTONE, "peaks.narrowPeak", narrow_peak_row()),
        (METHYLATION, "cpgs.bedMethyl", encode_methyl_row()),
    ],
    ids=["accessibility", "histone", "methylation"],
)
def test_gzipped_blacklist_is_read(tmp_path, script, filename, row):
    # Arrange
    path = write_lines(tmp_path / filename, [row])
    blacklist = write_gzipped(tmp_path / "blacklist.bed.gz", [["chr1", 500, 600]])

    # Act
    code, output = run_script(script, path, "--blacklist", blacklist)

    # Assert
    assert code == 0, output
    assert "RESULT: PASS" in output, output


@pytest.mark.parametrize(
    ("script", "filename", "good_rows", "negative_row", "valid_label"),
    [
        (
            ACCESSIBILITY,
            "neg.narrowPeak",
            [narrow_peak_row(), narrow_peak_row(start=2000, end=2200)],
            narrow_peak_row(start=-10, end=20),
            "Valid peaks",
        ),
        (
            HISTONE,
            "neg.narrowPeak",
            [narrow_peak_row(), narrow_peak_row(start=2000, end=2200)],
            narrow_peak_row(start=-10, end=20),
            "Valid peaks",
        ),
        (
            LOOPS,
            "neg.bedpe",
            [bedpe_row(), bedpe_row(start1=2_000_000, end1=2_010_000)],
            bedpe_row(start1=-10_000, end1=0),
            "Valid loops",
        ),
        (
            METHYLATION,
            "neg.bedMethyl",
            [encode_methyl_row(), encode_methyl_row(start=2000, end=2001)],
            encode_methyl_row(start=-1, end=0),
            "Valid CpGs",
        ),
    ],
)
def test_a_row_with_a_negative_coordinate_is_malformed_and_left_out_of_the_statistics(
    tmp_path, script, filename, good_rows, negative_row, valid_label
):
    # Arrange: start < end holds for the bad row, so only the sign gives it away
    path = tmp_path / filename
    write_lines(path, [*good_rows, negative_row])

    # Act
    code, output = run_script(script, path)

    # Assert
    assert code == 1, output
    assert "negative" in output, output
    assert re.search(rf"{valid_label}:\s+2\b", output), output
    assert re.search(r"Malformed lines:\s+1\b", output), output


@pytest.mark.parametrize("script", [ACCESSIBILITY, HISTONE])
@pytest.mark.parametrize("bad_signal", ["abc", "-3.0"])
def test_a_peak_with_an_invalid_signal_value_is_left_out_of_the_statistics(tmp_path, script, bad_signal):
    # Arrange: two good peaks and one 5 kb peak whose signalValue cannot be used
    bad_row = narrow_peak_row(start=10_000, end=15_000, signal=bad_signal)
    path = tmp_path / "signal.narrowPeak"
    write_lines(path, [narrow_peak_row(), narrow_peak_row(start=2000, end=2200), bad_row])

    # Act
    code, output = run_script(script, path)

    # Assert: the bad row is malformed, and its 5,000 bp size never reaches the size statistics
    assert code == 1, output
    assert re.search(r"Valid peaks:\s+2\b", output), output
    assert re.search(r"Malformed lines:\s+1\b", output), output
    assert "5,000" not in output, output


def test_histone_rejects_a_narrowpeak_file_read_as_broadpeak(tmp_path):
    # Arrange: narrowPeak has 10 columns, broadPeak 9; a longer row is not a broadPeak row
    path = tmp_path / "narrow.narrowPeak"
    write_lines(path, [narrow_peak_row(), narrow_peak_row(start=2000, end=2200)])

    # Act
    code, output = run_script(HISTONE, path, "--format", "broad")

    # Assert
    assert code == 1, output
    assert "expected 9 columns" in output, output


def test_accessibility_rejects_a_row_with_too_many_columns(tmp_path):
    path = tmp_path / "wide.narrowPeak"
    write_lines(path, [narrow_peak_row(), [*narrow_peak_row(start=2000, end=2200), "extra"]])

    code, output = run_script(ACCESSIBILITY, path)

    assert code == 1, output
    assert "expected 10 columns" in output, output
    assert re.search(r"Valid peaks:\s+1\b", output), output


def test_methylation_value_above_one_hundred_is_left_out_of_the_statistics(tmp_path):
    # Arrange
    path = tmp_path / "over.bedMethyl"
    write_lines(
        path,
        [
            encode_methyl_row(methylation=10),
            encode_methyl_row(start=2000, end=2001, methylation=20),
            encode_methyl_row(start=3000, end=3001, methylation=150),
        ],
    )

    # Act
    code, output = run_script(METHYLATION, path)

    # Assert: 150 is an error and must not become the maximum of the distribution
    assert code == 1, output
    assert "150" in output, output
    assert re.search(r"Max:\s+20\.0%", output), output
    assert re.search(r"Valid CpGs:\s+2\b", output), output
