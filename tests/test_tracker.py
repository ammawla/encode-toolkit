"""Tests for the experiment tracker (SQLite storage, provenance, compatibility)."""

import json

import pytest

from encode_connector.client.tracker import (
    ExperimentTracker,
    parse_encode_pipelines,
    parse_encode_publications,
)


@pytest.fixture
def tracker(tmp_path):
    """Create a tracker with a temp database."""
    db = tmp_path / "test_tracker.db"
    t = ExperimentTracker(db_path=db)
    yield t
    t.close()


@pytest.fixture
def sample_experiment():
    return {
        "accession": "ENCSR133RZO",
        "assay_title": "Histone ChIP-seq",
        "target": "H3K27me3",
        "biosample_summary": "human pancreas tissue",
        "organism": "Homo sapiens",
        "organ": "pancreas",
        "biosample_type": "tissue",
        "status": "released",
        "date_released": "2024-01-15",
        "description": "Test experiment",
        "lab": "Bernstein",
        "award": "ENCODE4",
        "assembly": "GRCh38",
        "replication_type": "isogenic",
        "life_stage": "adult",
        "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/",
    }


@pytest.fixture
def sample_experiment2():
    return {
        "accession": "ENCSR000AKS",
        "assay_title": "Histone ChIP-seq",
        "target": "H3K27me3",
        "biosample_summary": "human liver tissue",
        "organism": "Homo sapiens",
        "organ": "liver",
        "biosample_type": "tissue",
        "status": "released",
        "date_released": "2024-02-20",
        "description": "Another test experiment",
        "lab": "Bernstein",
        "award": "ENCODE4",
        "assembly": "GRCh38",
        "replication_type": "isogenic",
        "life_stage": "adult",
        "url": "https://www.encodeproject.org/experiments/ENCSR000AKS/",
    }


@pytest.fixture
def sample_experiment3():
    """A third experiment with different assay type for multi-experiment tests."""
    return {
        "accession": "ENCSR555XYZ",
        "assay_title": "ATAC-seq",
        "target": "",
        "biosample_summary": "human pancreas tissue",
        "organism": "Homo sapiens",
        "organ": "pancreas",
        "biosample_type": "tissue",
        "status": "released",
        "date_released": "2024-03-10",
        "description": "ATAC-seq experiment",
        "lab": "Snyder",
        "award": "ENCODE4",
        "assembly": "GRCh38",
        "replication_type": "anisogenic",
        "life_stage": "adult",
        "url": "https://www.encodeproject.org/experiments/ENCSR555XYZ/",
    }


class TestTrackExperiment:
    def test_track_new_experiment(self, tracker, sample_experiment):
        result = tracker.track_experiment(sample_experiment)
        assert result["action"] == "tracked"
        assert result["accession"] == "ENCSR133RZO"

    def test_track_updates_existing(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        sample_experiment["description"] = "Updated"
        result = tracker.track_experiment(sample_experiment)
        assert result["action"] == "updated"

    def test_get_tracked_experiment(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        exp = tracker.get_tracked_experiment("ENCSR133RZO")
        assert exp is not None
        assert exp["accession"] == "ENCSR133RZO"
        assert exp["assay_title"] == "Histone ChIP-seq"

    def test_get_nonexistent(self, tracker):
        assert tracker.get_tracked_experiment("ENCSR999ZZZ") is None

    def test_list_tracked_experiments(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        exps = tracker.list_tracked_experiments()
        assert len(exps) == 2

    def test_list_filtered_by_assay(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        exps = tracker.list_tracked_experiments(assay_title="ChIP-seq")
        assert len(exps) == 1
        exps = tracker.list_tracked_experiments(assay_title="RNA-seq")
        assert len(exps) == 0

    def test_list_filtered_by_organ(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        exps = tracker.list_tracked_experiments(organ="pancreas")
        assert len(exps) == 1
        assert exps[0]["accession"] == "ENCSR133RZO"

    def test_list_filtered_by_organism(self, tracker, sample_experiment, sample_experiment2):
        """Cover lines 280-281: organism LIKE filter path."""
        sample_experiment2["organism"] = "Mus musculus"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        exps = tracker.list_tracked_experiments(organism="Homo sapiens")
        assert len(exps) == 1
        assert exps[0]["accession"] == "ENCSR133RZO"

        exps = tracker.list_tracked_experiments(organism="Mus musculus")
        assert len(exps) == 1
        assert exps[0]["accession"] == "ENCSR000AKS"

    def test_remove_tracked(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        assert tracker.remove_tracked_experiment("ENCSR133RZO") is True
        assert tracker.get_tracked_experiment("ENCSR133RZO") is None

    def test_remove_nonexistent(self, tracker):
        assert tracker.remove_tracked_experiment("ENCSR999ZZZ") is False

    def test_remove_with_all_related_data(self, tracker, sample_experiment):
        """Cover lines 300-314: remove cascades to all child tables."""
        tracker.track_experiment(sample_experiment)
        acc = "ENCSR133RZO"

        # Populate every child table
        tracker.store_publications(acc, [{"pmid": "111", "title": "Pub1"}])
        tracker.store_pipeline_info(
            acc,
            [{"title": "ChIP-seq pipeline", "version": "2.0", "software": [], "status": "released"}],
        )
        tracker.store_quality_metrics(
            acc,
            [{"file_accession": "ENCFF001AAA", "metric_type": "frip", "data": {"frip": 0.05}}],
        )
        tracker.link_reference(acc, "pmid", "12345")
        tracker.log_derived_file("/data/peaks.bed", [acc], "Peaks")

        # Verify data exists before removal
        assert len(tracker.get_publications(acc)) == 1
        assert len(tracker.get_pipeline_info(acc)) == 1
        assert len(tracker.get_quality_metrics(acc)) == 1
        assert len(tracker.get_references(accession=acc)) == 1
        assert len(tracker.get_derived_files(acc)) == 1

        # Remove experiment
        assert tracker.remove_tracked_experiment(acc) is True

        # All related data should be gone
        assert tracker.get_tracked_experiment(acc) is None
        assert len(tracker.get_publications(acc)) == 0
        assert len(tracker.get_pipeline_info(acc)) == 0
        assert len(tracker.get_quality_metrics(acc)) == 0
        assert len(tracker.get_references(accession=acc)) == 0
        assert len(tracker.get_derived_files(acc)) == 0

    def test_add_note(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        assert tracker.add_note("ENCSR133RZO", "Important experiment") is True
        exp = tracker.get_tracked_experiment("ENCSR133RZO")
        assert exp["notes"] == "Important experiment"

    def test_raw_metadata_size_limit(self, tracker, sample_experiment):
        # Create oversized raw metadata
        big_metadata = {"data": "x" * (600 * 1024)}
        tracker.track_experiment(sample_experiment, raw_metadata=big_metadata)
        exp = tracker.get_tracked_experiment("ENCSR133RZO")
        # Should store empty JSON since over 512KB
        assert exp["raw_metadata"] == "{}"


class TestPublications:
    def test_store_and_retrieve(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        pubs = [
            {
                "pmid": "12345",
                "doi": "10.1234/test",
                "title": "Test Paper",
                "authors": "Smith, Jones",
                "journal": "Nature",
                "year": "2024",
                "abstract": "Test",
            },
        ]
        count = tracker.store_publications("ENCSR133RZO", pubs)
        assert count == 1

        retrieved = tracker.get_publications("ENCSR133RZO")
        assert len(retrieved) == 1
        assert retrieved[0]["title"] == "Test Paper"

    def test_store_multiple(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        pubs = [
            {"pmid": "111", "title": "Paper 1"},
            {"pmid": "222", "title": "Paper 2"},
        ]
        count = tracker.store_publications("ENCSR133RZO", pubs)
        assert count == 2

    def test_store_duplicate_pmid_replaces(self, tracker, sample_experiment):
        """Cover line 354-355: IntegrityError on INSERT OR REPLACE handles duplicates."""
        tracker.track_experiment(sample_experiment)
        tracker.store_publications("ENCSR133RZO", [{"pmid": "111", "title": "Original"}])
        count = tracker.store_publications("ENCSR133RZO", [{"pmid": "111", "title": "Updated"}])
        assert count == 1
        pubs = tracker.get_publications("ENCSR133RZO")
        assert len(pubs) == 1
        assert pubs[0]["title"] == "Updated"


class TestPipelineInfo:
    def test_store_and_retrieve(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        pipelines = [
            {
                "title": "ENCODE ChIP-seq pipeline",
                "version": "2.0",
                "software": [{"name": "bowtie2", "version": "2.4"}],
                "status": "released",
            },
        ]
        count = tracker.store_pipeline_info("ENCSR133RZO", pipelines)
        assert count == 1

        retrieved = tracker.get_pipeline_info("ENCSR133RZO")
        assert len(retrieved) == 1
        assert retrieved[0]["pipeline_title"] == "ENCODE ChIP-seq pipeline"

    def test_store_pipeline_replaces_existing(self, tracker, sample_experiment):
        """Cover lines 383-406: store_pipeline_info DELETE + INSERT replaces existing data."""
        tracker.track_experiment(sample_experiment)
        acc = "ENCSR133RZO"

        # Store initial pipeline
        tracker.store_pipeline_info(
            acc,
            [
                {"title": "Pipeline v1", "version": "1.0", "software": [], "status": "released"},
                {"title": "Pipeline v1b", "version": "1.0b", "software": [], "status": "released"},
            ],
        )
        assert len(tracker.get_pipeline_info(acc)) == 2

        # Replace with new pipeline (should delete old ones first)
        count = tracker.store_pipeline_info(
            acc,
            [
                {
                    "title": "Pipeline v2",
                    "version": "2.0",
                    "software": [{"name": "bwa", "version": "0.7"}],
                    "status": "released",
                }
            ],
        )
        assert count == 1
        pipelines = tracker.get_pipeline_info(acc)
        assert len(pipelines) == 1
        assert pipelines[0]["pipeline_title"] == "Pipeline v2"
        assert pipelines[0]["software_list"] == [{"name": "bwa", "version": "0.7"}]


class TestQualityMetrics:
    def test_store_and_retrieve(self, tracker, sample_experiment):
        """Cover lines 434-459: store_quality_metrics full path."""
        tracker.track_experiment(sample_experiment)
        acc = "ENCSR133RZO"
        metrics = [
            {
                "file_accession": "ENCFF001AAA",
                "metric_type": "frip",
                "data": {"frip": 0.05, "nsc": 1.1, "rsc": 0.9},
            },
            {
                "file_accession": "ENCFF002BBB",
                "metric_type": "mapping_quality",
                "data": {"mapping_rate": 0.95, "unique_mapped": 50000000},
            },
        ]
        count = tracker.store_quality_metrics(acc, metrics)
        assert count == 2

        retrieved = tracker.get_quality_metrics(acc)
        assert len(retrieved) == 2
        # Verify JSON deserialization
        frip_metric = next(m for m in retrieved if m["metric_type"] == "frip")
        assert frip_metric["metric_data"]["frip"] == 0.05
        assert frip_metric["file_accession"] == "ENCFF001AAA"

    def test_store_quality_metrics_replaces_existing(self, tracker, sample_experiment):
        """Cover lines 437-459: quality metrics DELETE + INSERT replaces existing data."""
        tracker.track_experiment(sample_experiment)
        acc = "ENCSR133RZO"

        # Store initial metrics
        tracker.store_quality_metrics(
            acc,
            [{"file_accession": "ENCFF001AAA", "metric_type": "frip", "data": {"frip": 0.03}}],
        )
        assert len(tracker.get_quality_metrics(acc)) == 1

        # Replace with new metrics
        count = tracker.store_quality_metrics(
            acc,
            [
                {"file_accession": "ENCFF001AAA", "metric_type": "frip", "data": {"frip": 0.07}},
                {"file_accession": "ENCFF002BBB", "metric_type": "nsc", "data": {"nsc": 1.2}},
            ],
        )
        assert count == 2
        metrics = tracker.get_quality_metrics(acc)
        assert len(metrics) == 2

    def test_get_quality_metrics_empty(self, tracker, sample_experiment):
        """Cover lines 463-473: get_quality_metrics with no data."""
        tracker.track_experiment(sample_experiment)
        metrics = tracker.get_quality_metrics("ENCSR133RZO")
        assert metrics == []

    def test_get_quality_metrics_nonexistent_experiment(self, tracker):
        """get_quality_metrics for an untracked experiment returns empty list."""
        metrics = tracker.get_quality_metrics("ENCSR999ZZZ")
        assert metrics == []


class TestProvenance:
    def test_log_and_retrieve(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        row_id = tracker.log_derived_file(
            file_path="/data/filtered_peaks.bed",
            source_accessions=["ENCSR133RZO"],
            description="Filtered peaks",
            tool_used="bedtools intersect",
            parameters="-a peaks.bed -b regions.bed",
        )
        assert row_id > 0

        derived = tracker.get_derived_files("ENCSR133RZO")
        assert len(derived) == 1
        assert derived[0]["file_path"] == "/data/filtered_peaks.bed"
        assert "ENCSR133RZO" in derived[0]["source_accessions"]

    def test_provenance_chain(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.log_derived_file(
            file_path="/data/output.bed",
            source_accessions=["ENCSR133RZO"],
            description="Output",
            tool_used="custom script",
        )

        chain = tracker.get_provenance_chain("/data/output.bed")
        assert "source_experiments" in chain
        assert chain["source_experiments"][0]["accession"] == "ENCSR133RZO"

    def test_provenance_chain_multiple_sources(self, tracker, sample_experiment, sample_experiment2):
        """Cover line 554: provenance chain with multiple source experiments."""
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        tracker.log_derived_file(
            file_path="/data/merged_peaks.bed",
            source_accessions=["ENCSR133RZO", "ENCSR000AKS"],
            description="Merged peaks from two experiments",
            tool_used="bedtools merge",
        )

        chain = tracker.get_provenance_chain("/data/merged_peaks.bed")
        assert "source_experiments" in chain
        assert len(chain["source_experiments"]) == 2
        accessions = [s["accession"] for s in chain["source_experiments"]]
        assert "ENCSR133RZO" in accessions
        assert "ENCSR000AKS" in accessions
        # Both should be fully tracked with metadata
        for source in chain["source_experiments"]:
            assert "assay_title" in source
            assert "organism" in source

    def test_provenance_chain_with_untracked_source(self, tracker, sample_experiment):
        """Cover line 554: provenance chain where one source is not tracked."""
        tracker.track_experiment(sample_experiment)
        tracker.log_derived_file(
            file_path="/data/combined.bed",
            source_accessions=["ENCSR133RZO", "ENCSR999ZZZ"],
            description="Combined from tracked and untracked",
            tool_used="custom",
        )

        chain = tracker.get_provenance_chain("/data/combined.bed")
        assert len(chain["source_experiments"]) == 2
        tracked_source = next(s for s in chain["source_experiments"] if s["accession"] == "ENCSR133RZO")
        untracked_source = next(s for s in chain["source_experiments"] if s["accession"] == "ENCSR999ZZZ")
        assert "assay_title" in tracked_source
        assert untracked_source["tracked"] is False

    def test_provenance_not_found(self, tracker):
        chain = tracker.get_provenance_chain("/nonexistent/file.bed")
        assert "error" in chain

    def test_get_all_derived_files(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.log_derived_file("/data/a.bed", ["ENCSR133RZO"], "File A")
        tracker.log_derived_file("/data/b.bed", ["ENCSR133RZO"], "File B")

        derived = tracker.get_derived_files()
        assert len(derived) == 2

    def test_log_derived_file_with_untracked_source(self, tracker):
        """Log a derived file referencing a source that is not tracked.

        The derived_files table does not have a foreign key on source_accessions,
        so this should succeed. The provenance chain will show tracked=False.
        """
        row_id = tracker.log_derived_file(
            file_path="/data/untracked_source.bed",
            source_accessions=["ENCSR999ZZZ"],
            description="From untracked source",
            tool_used="custom",
        )
        assert row_id > 0

        chain = tracker.get_provenance_chain("/data/untracked_source.bed")
        assert len(chain["source_experiments"]) == 1
        assert chain["source_experiments"][0]["tracked"] is False


class TestCompatibility:
    def test_fully_compatible(self, tracker, sample_experiment, sample_experiment2):
        # Make them identical except organ
        sample_experiment2["organ"] = "pancreas"
        sample_experiment2["lab"] = "Bernstein"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert result["verdict"] in ("FULLY_COMPATIBLE", "COMPATIBLE_WITH_CAVEATS")

    def test_incompatible_organism(self, tracker, sample_experiment, sample_experiment2):
        sample_experiment2["organism"] = "Mus musculus"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert result["verdict"] == "NOT_COMPATIBLE"
        assert any("organism" in i.lower() for i in result["issues"])

    def test_incompatible_assembly(self, tracker, sample_experiment, sample_experiment2):
        sample_experiment2["assembly"] = "mm10"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        # Assembly mismatch creates a NOT_COMPATIBLE verdict
        assert result["verdict"] == "NOT_COMPATIBLE"
        assert any("assembl" in i.lower() for i in result["issues"]), f"Expected assembly issue, got: {result}"

    def test_caveats_different_organ(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert result["verdict"] == "COMPATIBLE_WITH_CAVEATS"
        assert any("organ" in w.lower() for w in result["warnings"])

    def test_not_tracked(self, tracker):
        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert "error" in result

    def test_second_not_tracked(self, tracker, sample_experiment):
        """Cover line 571: only first experiment tracked, second missing."""
        tracker.track_experiment(sample_experiment)
        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert "error" in result
        assert "ENCSR000AKS" in result["error"]

    def test_different_assay_types_warning(self, tracker, sample_experiment, sample_experiment3):
        """Cover lines 600, 610: different assay_title and biosample_type produce warnings."""
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment3)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR555XYZ")
        assert result["verdict"] == "COMPATIBLE_WITH_CAVEATS"
        assert any("assay" in w.lower() for w in result["warnings"])

    def test_different_biosample_type_warning(self, tracker, sample_experiment, sample_experiment2):
        """Cover line 610: different biosample_type produces a warning."""
        sample_experiment2["biosample_type"] = "cell line"
        sample_experiment2["organ"] = "pancreas"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert any("biosample type" in w.lower() for w in result["warnings"])

    def test_different_target_warning(self, tracker, sample_experiment, sample_experiment2):
        """Cover lines 627-628: different ChIP-seq targets produce a warning."""
        sample_experiment2["target"] = "H3K4me3"
        sample_experiment2["organ"] = "pancreas"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert any("target" in w.lower() for w in result["warnings"])

    def test_different_replication_type_warning(self, tracker, sample_experiment, sample_experiment2):
        """Cover line 635: different replication types produce a warning."""
        sample_experiment2["replication_type"] = "anisogenic"
        sample_experiment2["organ"] = "pancreas"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert any("replication" in w.lower() for w in result["warnings"])

    def test_different_lab_warning(self, tracker, sample_experiment, sample_experiment2):
        """Cover line 640: different labs produce a batch-effects warning."""
        sample_experiment2["lab"] = "Snyder"
        sample_experiment2["organ"] = "pancreas"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        result = tracker.analyze_compatibility("ENCSR133RZO", "ENCSR000AKS")
        assert any("lab" in w.lower() for w in result["warnings"])
        assert any("batch" in w.lower() for w in result["warnings"])


class TestCitationExport:
    def test_bibtex_export(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.store_publications(
            "ENCSR133RZO",
            [
                {
                    "pmid": "12345",
                    "title": "Test Paper",
                    "authors": "Smith J",
                    "journal": "Nature",
                    "year": "2024",
                    "doi": "10.1234/test",
                },
            ],
        )

        bibtex = tracker.export_citations_bibtex(["ENCSR133RZO"])
        assert "@article" in bibtex
        assert "Test Paper" in bibtex
        assert "Smith J" in bibtex

    def test_ris_export(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.store_publications(
            "ENCSR133RZO",
            [
                {
                    "pmid": "12345",
                    "title": "Test Paper",
                    "authors": "Smith J, Doe A",
                    "journal": "Nature",
                    "year": "2024",
                },
            ],
        )

        ris = tracker.export_citations_ris(["ENCSR133RZO"])
        assert "TY  - JOUR" in ris
        assert "TI  - Test Paper" in ris
        assert "AU  - Smith J" in ris
        assert "ER  - " in ris

    def test_ris_export_with_doi_and_abstract(self, tracker, sample_experiment):
        """Cover lines 742, 747: RIS export with doi and abstract fields."""
        tracker.track_experiment(sample_experiment)
        tracker.store_publications(
            "ENCSR133RZO",
            [
                {
                    "pmid": "12345",
                    "title": "Test Paper",
                    "authors": "Smith J",
                    "journal": "Nature",
                    "year": "2024",
                    "doi": "10.1234/test",
                    "abstract": "This is the abstract of the test paper.",
                },
            ],
        )

        ris = tracker.export_citations_ris(["ENCSR133RZO"])
        assert "DO  - 10.1234/test" in ris
        assert "AB  - This is the abstract of the test paper." in ris
        assert "AN  - PMID:12345" in ris

    def test_export_all(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.store_publications(
            "ENCSR133RZO",
            [
                {"pmid": "111", "title": "Paper 1"},
            ],
        )

        bibtex = tracker.export_citations_bibtex()
        assert "Paper 1" in bibtex

    def test_export_all_ris(self, tracker, sample_experiment):
        """Cover line 726: RIS export with accessions=None (export all)."""
        tracker.track_experiment(sample_experiment)
        tracker.store_publications(
            "ENCSR133RZO",
            [{"pmid": "111", "title": "Paper 1"}],
        )

        ris = tracker.export_citations_ris()
        assert "Paper 1" in ris

    def test_bibtex_no_pmid_no_doi_uses_encode_key(self, tracker, sample_experiment):
        """Cover bibtex key fallback when pmid and doi are empty."""
        tracker.track_experiment(sample_experiment)
        tracker.store_publications(
            "ENCSR133RZO",
            [{"title": "Paper With No IDs"}],
        )

        bibtex = tracker.export_citations_bibtex(["ENCSR133RZO"])
        assert "@article{encode_ENCSR133RZO" in bibtex


class TestMetadataTable:
    def test_get_metadata_table(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        table = tracker.get_metadata_table()
        assert len(table) == 1
        assert "publication_count" in table[0]
        assert "derived_file_count" in table[0]
        assert "raw_metadata" not in table[0]

    def test_table_with_accession_filter(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)

        table = tracker.get_metadata_table(["ENCSR133RZO"])
        assert len(table) == 1

    def test_table_with_publications_and_derived_files(self, tracker, sample_experiment):
        """Cover metadata table with actual publication and derived file counts."""
        tracker.track_experiment(sample_experiment)
        acc = "ENCSR133RZO"
        tracker.store_publications(acc, [{"pmid": "111", "title": "P1"}, {"pmid": "222", "title": "P2"}])
        tracker.log_derived_file("/data/a.bed", [acc], "File A")
        tracker.log_derived_file("/data/b.bed", [acc], "File B")
        tracker.log_derived_file("/data/c.bed", [acc], "File C")

        table = tracker.get_metadata_table()
        assert len(table) == 1
        assert table[0]["publication_count"] == 2
        assert table[0]["derived_file_count"] == 3


class TestStats:
    def test_stats(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        stats = tracker.stats
        assert stats["tracked_experiments"] == 1
        assert stats["publications"] == 0
        assert "db_path" in stats

    def test_stats_includes_all_counts(self, tracker, sample_experiment):
        """Verify stats counts for all table types."""
        tracker.track_experiment(sample_experiment)
        acc = "ENCSR133RZO"
        tracker.store_publications(acc, [{"pmid": "111", "title": "P1"}])
        tracker.store_pipeline_info(
            acc, [{"title": "Pipeline", "version": "1.0", "software": [], "status": "released"}]
        )
        tracker.store_quality_metrics(
            acc, [{"file_accession": "ENCFF001AAA", "metric_type": "frip", "data": {"frip": 0.05}}]
        )
        tracker.log_derived_file("/data/a.bed", [acc], "File A")
        tracker.link_reference(acc, "pmid", "12345")

        stats = tracker.stats
        assert stats["tracked_experiments"] == 1
        assert stats["publications"] == 1
        assert stats["pipeline_records"] == 1
        assert stats["quality_metrics"] == 1
        assert stats["derived_files"] == 1
        assert stats["external_references"] == 1


class TestDbPath:
    def test_db_path_property(self, tracker, tmp_path):
        """Cover line 1043: db_path property returns string path."""
        path = tracker.db_path
        assert isinstance(path, str)
        assert "test_tracker.db" in path


class TestParseEncodePublications:
    def test_parse_basic(self):
        refs = [
            {
                "title": "Test Paper",
                "authors": "Smith J, Doe A",
                "journal": "Nature",
                "date_published": "2024-06-15",
                "identifiers": ["PMID:12345", "doi:10.1234/test"],
            }
        ]
        pubs = parse_encode_publications(refs)
        assert len(pubs) == 1
        assert pubs[0]["pmid"] == "12345"
        assert pubs[0]["doi"] == "10.1234/test"
        assert pubs[0]["year"] == "2024"

    def test_parse_skips_strings(self):
        refs = ["/publications/123/", {"title": "Real Paper"}]
        pubs = parse_encode_publications(refs)
        assert len(pubs) == 1

    def test_parse_skips_non_dicts(self):
        """Cover line 1067: non-dict, non-string items are skipped."""
        refs = [42, None, True, {"title": "Real Paper"}]
        pubs = parse_encode_publications(refs)
        assert len(pubs) == 1
        assert pubs[0]["title"] == "Real Paper"

    def test_parse_authors_as_list(self):
        """Cover lines 1083: authors provided as a list instead of string."""
        refs = [
            {
                "title": "Paper",
                "authors": ["Smith J", "Doe A", "Jones B"],
                "date_published": "2023-01-01",
            }
        ]
        pubs = parse_encode_publications(refs)
        assert pubs[0]["authors"] == "Smith J, Doe A, Jones B"

    def test_parse_authors_as_other_type(self):
        """Cover line 1087: authors as a non-string, non-list type."""
        refs = [{"title": "Paper", "authors": 12345}]
        pubs = parse_encode_publications(refs)
        assert pubs[0]["authors"] == "12345"

    def test_parse_authors_list_limited_to_10(self):
        """Cover line 1083: authors list is truncated to first 10."""
        many_authors = [f"Author{i}" for i in range(20)]
        refs = [{"title": "Paper", "authors": many_authors}]
        pubs = parse_encode_publications(refs)
        author_count = len(pubs[0]["authors"].split(", "))
        assert author_count == 10

    def test_parse_authors_string_limited_to_10(self):
        """Cover line 1083: authors string is truncated to first 10."""
        many_authors = ", ".join(f"Author{i}" for i in range(20))
        refs = [{"title": "Paper", "authors": many_authors}]
        pubs = parse_encode_publications(refs)
        author_count = len(pubs[0]["authors"].split(", "))
        assert author_count == 10

    def test_parse_no_date_published(self):
        """Verify year is empty when date_published is missing."""
        refs = [{"title": "Paper", "authors": "Smith J"}]
        pubs = parse_encode_publications(refs)
        assert pubs[0]["year"] == ""


class TestExternalReferences:
    def test_link_reference(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        result = tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        assert result["action"] == "linked"
        assert result["reference_type"] == "pmid"

    def test_link_reference_duplicate(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        result = tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        assert result["action"] == "already_linked"

    def test_link_reference_not_tracked(self, tracker):
        result = tracker.link_reference("ENCSR999ZZZ", "pmid", "12345")
        assert "error" in result

    def test_link_reference_invalid_type(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        with pytest.raises(ValueError, match="reference_type"):
            tracker.link_reference("ENCSR133RZO", "invalid_type", "12345")

    def test_get_references_by_experiment(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        tracker.link_reference("ENCSR133RZO", "doi", "10.1234/test")
        refs = tracker.get_references(accession="ENCSR133RZO")
        assert len(refs) == 2

    def test_get_references_by_type(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        tracker.link_reference("ENCSR000AKS", "pmid", "67890")
        tracker.link_reference("ENCSR133RZO", "doi", "10.1234/test")

        refs = tracker.get_references(reference_type="pmid")
        assert len(refs) == 2

    def test_get_references_all(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        tracker.link_reference("ENCSR133RZO", "geo_accession", "GSE123456")
        refs = tracker.get_references()
        assert len(refs) == 2

    def test_unlink_reference(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        assert tracker.unlink_reference("ENCSR133RZO", "pmid", "12345") is True
        refs = tracker.get_references(accession="ENCSR133RZO")
        assert len(refs) == 0

    def test_unlink_nonexistent(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        assert tracker.unlink_reference("ENCSR133RZO", "pmid", "99999") is False

    def test_remove_experiment_cleans_references(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        tracker.remove_tracked_experiment("ENCSR133RZO")
        refs = tracker.get_references(accession="ENCSR133RZO")
        assert len(refs) == 0

    def test_multiple_types_per_experiment(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        tracker.link_reference("ENCSR133RZO", "doi", "10.1234/test")
        tracker.link_reference("ENCSR133RZO", "geo_accession", "GSE123456")
        tracker.link_reference("ENCSR133RZO", "nct_id", "NCT04567890")
        refs = tracker.get_references(accession="ENCSR133RZO")
        assert len(refs) == 4


class TestExportTrackedData:
    def test_export_csv(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        csv_data = tracker.export_tracked_data(format="csv")
        lines = csv_data.split("\n")
        assert len(lines) == 2  # header + 1 row
        assert "accession" in lines[0]
        assert "ENCSR133RZO" in lines[1]

    def test_export_tsv(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tsv_data = tracker.export_tracked_data(format="tsv")
        lines = tsv_data.split("\n")
        assert "\t" in lines[0]

    def test_export_json(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        json_data = tracker.export_tracked_data(format="json")
        parsed = json.loads(json_data)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["accession"] == "ENCSR133RZO"

    def test_export_empty(self, tracker):
        csv_data = tracker.export_tracked_data(format="csv")
        assert csv_data == ""
        json_data = tracker.export_tracked_data(format="json")
        assert json_data == "[]"

    def test_export_includes_pmids(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.store_publications("ENCSR133RZO", [{"pmid": "12345", "title": "Test"}])
        csv_data = tracker.export_tracked_data(format="csv")
        assert "12345" in csv_data

    def test_export_filtered(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        csv_data = tracker.export_tracked_data(format="csv", organ="pancreas")
        lines = csv_data.strip().split("\n")
        assert len(lines) == 2  # header + 1 matching row

    def test_export_filtered_by_assay_title(self, tracker, sample_experiment, sample_experiment3):
        """Cover line 949: export with assay_title filter."""
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment3)
        csv_data = tracker.export_tracked_data(format="csv", assay_title="ATAC-seq")
        lines = csv_data.strip().split("\n")
        assert len(lines) == 2  # header + 1 ATAC-seq row
        assert "ENCSR555XYZ" in lines[1]
        assert "ENCSR133RZO" not in lines[1]

    def test_export_filtered_by_organism(self, tracker, sample_experiment, sample_experiment2):
        """Cover line 949: export with organism filter."""
        sample_experiment2["organism"] = "Mus musculus"
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        json_data = tracker.export_tracked_data(format="json", organism="Mus musculus")
        parsed = json.loads(json_data)
        assert len(parsed) == 1
        assert parsed[0]["accession"] == "ENCSR000AKS"

    def test_export_includes_external_reference_count(self, tracker, sample_experiment):
        """Verify export includes external_reference_count column."""
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        tracker.link_reference("ENCSR133RZO", "doi", "10.1234/test")

        csv_data = tracker.export_tracked_data(format="csv")
        assert "external_reference_count" in csv_data
        # The row should contain count of 2
        json_data = tracker.export_tracked_data(format="json")
        parsed = json.loads(json_data)
        assert parsed[0]["external_reference_count"] == 2


class TestSummarizeCollection:
    def test_summarize_basic(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        summary = tracker.summarize_collection()
        assert summary["total_experiments"] == 2
        assert "Histone ChIP-seq" in summary["by_assay"]
        assert "Homo sapiens" in summary["by_organism"]

    def test_summarize_empty(self, tracker):
        summary = tracker.summarize_collection()
        assert summary["total_experiments"] == 0

    def test_summarize_filtered(self, tracker, sample_experiment, sample_experiment2):
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        summary = tracker.summarize_collection(organ="pancreas")
        assert summary["total_experiments"] == 1

    def test_summarize_includes_totals(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        tracker.store_publications("ENCSR133RZO", [{"pmid": "11111", "title": "Test"}])
        summary = tracker.summarize_collection()
        assert summary["total_publications"] == 1
        assert summary["total_external_references"] == 1

    def test_summarize_with_derived_files(self, tracker, sample_experiment):
        """Cover line 1026: summarize includes total_derived_files count."""
        tracker.track_experiment(sample_experiment)
        tracker.log_derived_file("/data/a.bed", ["ENCSR133RZO"], "File A")
        tracker.log_derived_file("/data/b.bed", ["ENCSR133RZO"], "File B")

        summary = tracker.summarize_collection()
        assert summary["total_derived_files"] == 2

    def test_summarize_with_quality_metrics_and_pipelines(self, tracker, sample_experiment):
        """Verify summarize counts are correct with multiple data types populated."""
        tracker.track_experiment(sample_experiment)
        acc = "ENCSR133RZO"
        tracker.store_quality_metrics(
            acc,
            [{"file_accession": "ENCFF001AAA", "metric_type": "frip", "data": {"frip": 0.05}}],
        )
        tracker.store_pipeline_info(
            acc,
            [{"title": "ChIP-seq pipeline", "version": "2.0", "software": [], "status": "released"}],
        )
        tracker.store_publications(acc, [{"pmid": "111", "title": "Pub1"}])

        summary = tracker.summarize_collection()
        assert summary["total_experiments"] == 1
        assert summary["total_publications"] == 1

    def test_summarize_groupings(self, tracker, sample_experiment, sample_experiment2, sample_experiment3):
        """Verify all by_* grouping dicts are populated correctly."""
        tracker.track_experiment(sample_experiment)
        tracker.track_experiment(sample_experiment2)
        tracker.track_experiment(sample_experiment3)

        summary = tracker.summarize_collection()
        assert summary["total_experiments"] == 3
        assert summary["by_assay"]["Histone ChIP-seq"] == 2
        assert summary["by_assay"]["ATAC-seq"] == 1
        assert summary["by_organism"]["Homo sapiens"] == 3
        assert summary["by_organ"]["pancreas"] == 2
        assert summary["by_organ"]["liver"] == 1
        assert summary["by_biosample_type"]["tissue"] == 3
        assert "Bernstein" in summary["by_lab"]
        assert "Snyder" in summary["by_lab"]


class TestStatsIncludesReferences:
    def test_stats_has_external_references(self, tracker, sample_experiment):
        tracker.track_experiment(sample_experiment)
        tracker.link_reference("ENCSR133RZO", "pmid", "12345")
        stats = tracker.stats
        assert "external_references" in stats
        assert stats["external_references"] == 1


class TestCsvValueEscaping:
    def test_csv_escapes_values_with_commas(self, tracker):
        """Cover line 949: CSV values containing commas are quoted."""
        exp = {
            "accession": "ENCSR111AAA",
            "assay_title": "Histone ChIP-seq",
            "target": "H3K27me3",
            "biosample_summary": "human pancreas, male, adult tissue",
            "organism": "Homo sapiens",
            "organ": "pancreas",
            "biosample_type": "tissue",
            "status": "released",
            "date_released": "2024-01-15",
            "description": "Has a comma, in the summary",
            "lab": "Bernstein",
            "award": "ENCODE4",
            "assembly": "GRCh38",
            "replication_type": "isogenic",
            "life_stage": "adult",
            "url": "https://www.encodeproject.org/experiments/ENCSR111AAA/",
        }
        tracker.track_experiment(exp)
        csv_data = tracker.export_tracked_data(format="csv")
        # The biosample_summary contains a comma, so it should be quoted
        assert '"human pancreas, male, adult tissue"' in csv_data

    def test_csv_escapes_values_with_quotes(self, tracker):
        """Cover line 949: CSV values containing double-quotes are escaped."""
        exp = {
            "accession": "ENCSR222BBB",
            "assay_title": "Histone ChIP-seq",
            "target": "H3K27me3",
            "biosample_summary": 'tissue with "special" name',
            "organism": "Homo sapiens",
            "organ": "pancreas",
            "biosample_type": "tissue",
            "status": "released",
            "date_released": "2024-01-15",
            "description": "Quoted value",
            "lab": "Bernstein",
            "award": "ENCODE4",
            "assembly": "GRCh38",
            "replication_type": "isogenic",
            "life_stage": "adult",
            "url": "https://www.encodeproject.org/experiments/ENCSR222BBB/",
        }
        tracker.track_experiment(exp)
        csv_data = tracker.export_tracked_data(format="csv")
        # Double-quotes in values should be doubled and the field quoted
        assert '""special""' in csv_data


class TestPublicationIntegrityError:
    def test_store_publications_for_untracked_experiment(self, tracker):
        """Cover lines 354-355: IntegrityError from FK violation is caught.

        When storing publications for an experiment accession that does not exist
        in tracked_experiments, the foreign key constraint should cause an
        IntegrityError that is caught and skipped.
        """
        count = tracker.store_publications("ENCSR999ZZZ", [{"pmid": "111", "title": "Paper"}])
        # The publication should be silently skipped due to FK violation
        assert count == 0


class TestParseEncodePipelines:
    def test_parse_basic(self):
        analyses = [
            {
                "title": "ChIP-seq pipeline",
                "pipeline_version": "2.0",
                "status": "released",
                "pipeline_run_software": [
                    {"name": "bowtie2", "version": "2.4"},
                ],
            }
        ]
        pipelines = parse_encode_pipelines(analyses)
        assert len(pipelines) == 1
        assert pipelines[0]["title"] == "ChIP-seq pipeline"

    def test_parse_skips_non_dicts(self):
        analyses = ["/analyses/123/", {"title": "Real Analysis"}]
        pipelines = parse_encode_pipelines(analyses)
        assert len(pipelines) == 1

    def test_parse_uses_pipeline_title_fallback(self):
        """Cover fallback to pipeline_title when title is missing."""
        analyses = [{"pipeline_title": "Fallback Title", "pipeline_version": "1.0", "status": "released"}]
        pipelines = parse_encode_pipelines(analyses)
        assert pipelines[0]["title"] == "Fallback Title"

    def test_parse_software_skips_non_dicts(self):
        """Cover software parsing skipping non-dict entries."""
        analyses = [
            {
                "title": "Pipeline",
                "pipeline_run_software": ["/software/123/", {"name": "bwa", "version": "0.7"}],
            }
        ]
        pipelines = parse_encode_pipelines(analyses)
        assert len(pipelines[0]["software"]) == 1
        assert pipelines[0]["software"][0]["name"] == "bwa"
