"""Experiment tracker with SQLite storage.

Tracks experiments, publications, methods, pipeline info, quality metrics,
provenance of derived files, and supports compatibility analysis between
experiments.

All data stored locally in SQLite. No external connections except ENCODE API.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from encode_connector.client.validation import escape_like, validate_reference_type

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".encode_connector" / "tracker.db"


class ExperimentTracker:
    """SQLite-backed experiment tracker for ENCODE data."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()  # Protects connection creation AND write operations
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                self._conn = sqlite3.connect(
                    str(self._db_path),
                    check_same_thread=False,
                )
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA foreign_keys=ON")
            return self._conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        # Note: executescript() implicitly commits any pending transaction.
        # We re-issue PRAGMA foreign_keys=ON afterward because executescript
        # can interfere with connection-level pragma state in some SQLite builds.
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tracked_experiments (
                accession TEXT PRIMARY KEY,
                assay_title TEXT,
                target TEXT,
                biosample_summary TEXT,
                organism TEXT,
                organ TEXT,
                biosample_type TEXT,
                status TEXT,
                date_released TEXT,
                description TEXT,
                lab TEXT,
                award TEXT,
                assembly TEXT,
                replication_type TEXT,
                life_stage TEXT,
                url TEXT,
                raw_metadata TEXT,
                tracked_at REAL,
                updated_at REAL,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_accession TEXT NOT NULL,
                pmid TEXT,
                doi TEXT,
                title TEXT,
                authors TEXT,
                journal TEXT,
                year TEXT,
                abstract TEXT,
                FOREIGN KEY (experiment_accession) REFERENCES tracked_experiments(accession),
                UNIQUE(experiment_accession, pmid)
            );

            CREATE TABLE IF NOT EXISTS pipeline_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_accession TEXT NOT NULL,
                pipeline_title TEXT,
                pipeline_version TEXT,
                software_list TEXT,
                analysis_status TEXT,
                FOREIGN KEY (experiment_accession) REFERENCES tracked_experiments(accession)
            );

            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_accession TEXT NOT NULL,
                file_accession TEXT,
                metric_type TEXT,
                metric_data TEXT,
                FOREIGN KEY (experiment_accession) REFERENCES tracked_experiments(accession)
            );

            CREATE TABLE IF NOT EXISTS derived_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                source_accessions TEXT NOT NULL,
                description TEXT,
                created_at REAL,
                file_type TEXT,
                tool_used TEXT,
                parameters TEXT,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS external_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_accession TEXT NOT NULL,
                reference_type TEXT NOT NULL,
                reference_id TEXT NOT NULL,
                description TEXT DEFAULT '',
                linked_at REAL,
                FOREIGN KEY (experiment_accession) REFERENCES tracked_experiments(accession),
                UNIQUE(experiment_accession, reference_type, reference_id)
            );

            CREATE INDEX IF NOT EXISTS idx_pub_experiment
                ON publications(experiment_accession);
            CREATE INDEX IF NOT EXISTS idx_pipeline_experiment
                ON pipeline_info(experiment_accession);
            CREATE INDEX IF NOT EXISTS idx_qm_experiment
                ON quality_metrics(experiment_accession);
            CREATE INDEX IF NOT EXISTS idx_derived_sources
                ON derived_files(source_accessions);
            CREATE INDEX IF NOT EXISTS idx_extref_experiment
                ON external_references(experiment_accession);
            CREATE INDEX IF NOT EXISTS idx_extref_type
                ON external_references(reference_type);
            CREATE INDEX IF NOT EXISTS idx_exp_assay
                ON tracked_experiments(assay_title);
            CREATE INDEX IF NOT EXISTS idx_exp_organism
                ON tracked_experiments(organism);
            CREATE INDEX IF NOT EXISTS idx_exp_organ
                ON tracked_experiments(organ);
        """)
        # Re-issue foreign_keys pragma after executescript to ensure it's active
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Track experiments
    # ------------------------------------------------------------------

    def track_experiment(self, experiment_data: dict, raw_metadata: dict | None = None) -> dict:
        """Add or update an experiment in the tracker."""
        conn = self._get_conn()
        now = time.time()
        accession = experiment_data.get("accession", "")

        # Check if already tracked
        existing = conn.execute(
            "SELECT accession, tracked_at FROM tracked_experiments WHERE accession = ?",
            (accession,),
        ).fetchone()

        raw_json = json.dumps(raw_metadata) if raw_metadata else "{}"
        # Limit raw metadata size to 512KB to prevent storage bloat
        max_raw_size = 512 * 1024
        if len(raw_json) > max_raw_size:
            raw_json = "{}"

        if existing:
            conn.execute(
                """
                UPDATE tracked_experiments SET
                    assay_title=?, target=?, biosample_summary=?, organism=?,
                    organ=?, biosample_type=?, status=?, date_released=?,
                    description=?, lab=?, award=?, assembly=?,
                    replication_type=?, life_stage=?, url=?,
                    raw_metadata=?, updated_at=?
                WHERE accession=?
            """,
                (
                    experiment_data.get("assay_title", ""),
                    experiment_data.get("target", ""),
                    experiment_data.get("biosample_summary", ""),
                    experiment_data.get("organism", ""),
                    experiment_data.get("organ", ""),
                    experiment_data.get("biosample_type", ""),
                    experiment_data.get("status", ""),
                    experiment_data.get("date_released", ""),
                    experiment_data.get("description", ""),
                    experiment_data.get("lab", ""),
                    experiment_data.get("award", ""),
                    experiment_data.get("assembly", ""),
                    experiment_data.get("replication_type", ""),
                    experiment_data.get("life_stage", ""),
                    experiment_data.get("url", ""),
                    raw_json,
                    now,
                    accession,
                ),
            )
            action = "updated"
        else:
            conn.execute(
                """
                INSERT INTO tracked_experiments (
                    accession, assay_title, target, biosample_summary, organism,
                    organ, biosample_type, status, date_released, description,
                    lab, award, assembly, replication_type, life_stage, url,
                    raw_metadata, tracked_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    accession,
                    experiment_data.get("assay_title", ""),
                    experiment_data.get("target", ""),
                    experiment_data.get("biosample_summary", ""),
                    experiment_data.get("organism", ""),
                    experiment_data.get("organ", ""),
                    experiment_data.get("biosample_type", ""),
                    experiment_data.get("status", ""),
                    experiment_data.get("date_released", ""),
                    experiment_data.get("description", ""),
                    experiment_data.get("lab", ""),
                    experiment_data.get("award", ""),
                    experiment_data.get("assembly", ""),
                    experiment_data.get("replication_type", ""),
                    experiment_data.get("life_stage", ""),
                    experiment_data.get("url", ""),
                    raw_json,
                    now,
                    now,
                ),
            )
            action = "tracked"

        conn.commit()
        return {"accession": accession, "action": action}

    def get_tracked_experiment(self, accession: str) -> dict | None:
        """Get a tracked experiment by accession."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM tracked_experiments WHERE accession = ?",
            (accession,),
        ).fetchone()
        if row:
            return dict(row)
        return None

    def list_tracked_experiments(
        self,
        assay_title: str | None = None,
        organism: str | None = None,
        organ: str | None = None,
    ) -> list[dict]:
        """List tracked experiments with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM tracked_experiments WHERE 1=1"
        params: list[Any] = []

        if assay_title:
            query += " AND assay_title LIKE ? ESCAPE '\\'"
            params.append(f"%{escape_like(assay_title)}%")
        if organism:
            query += " AND organism LIKE ? ESCAPE '\\'"
            params.append(f"%{escape_like(organism)}%")
        if organ:
            query += " AND organ LIKE ? ESCAPE '\\'"
            params.append(f"%{escape_like(organ)}%")

        query += " ORDER BY tracked_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def remove_tracked_experiment(self, accession: str) -> bool:
        """Remove an experiment and all related data from tracking.

        Uses an explicit transaction to ensure all child table deletes
        and the parent delete are atomic — no partial state on failure.
        """
        conn = self._get_conn()
        with self._lock:
            try:
                conn.execute("BEGIN")
                conn.execute("DELETE FROM publications WHERE experiment_accession = ?", (accession,))
                conn.execute("DELETE FROM pipeline_info WHERE experiment_accession = ?", (accession,))
                conn.execute("DELETE FROM quality_metrics WHERE experiment_accession = ?", (accession,))
                conn.execute("DELETE FROM external_references WHERE experiment_accession = ?", (accession,))
                # Also remove derived_files referencing this experiment (stored as JSON array)
                conn.execute(
                    "DELETE FROM derived_files WHERE source_accessions LIKE ? ESCAPE '\\'",
                    (f"%{escape_like(accession)}%",),
                )
                result = conn.execute("DELETE FROM tracked_experiments WHERE accession = ?", (accession,))
                conn.commit()
                return result.rowcount > 0
            except Exception:
                conn.rollback()
                raise

    def add_note(self, accession: str, note: str) -> bool:
        """Add or update a note on a tracked experiment."""
        conn = self._get_conn()
        result = conn.execute(
            "UPDATE tracked_experiments SET notes = ?, updated_at = ? WHERE accession = ?",
            (note, time.time(), accession),
        )
        conn.commit()
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Publications
    # ------------------------------------------------------------------

    def store_publications(self, accession: str, publications: list[dict]) -> int:
        """Store publications for an experiment. Returns count stored."""
        conn = self._get_conn()
        count = 0
        for pub in publications:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO publications
                    (experiment_accession, pmid, doi, title, authors, journal, year, abstract)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        accession,
                        pub.get("pmid", ""),
                        pub.get("doi", ""),
                        pub.get("title", ""),
                        pub.get("authors", ""),
                        pub.get("journal", ""),
                        pub.get("year", ""),
                        pub.get("abstract", ""),
                    ),
                )
                count += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        return count

    def get_publications(self, accession: str) -> list[dict]:
        """Get publications for a tracked experiment."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM publications WHERE experiment_accession = ?",
            (accession,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Pipeline info
    # ------------------------------------------------------------------

    def store_pipeline_info(self, accession: str, pipelines: list[dict]) -> int:
        """Store pipeline/analysis info for an experiment.

        Uses an explicit transaction so the DELETE + INSERTs are atomic.
        If any INSERT fails, the existing data is preserved (not erased).
        Holds self._lock for the entire transaction to prevent concurrent
        BEGIN on the same connection (which raises OperationalError).
        """
        conn = self._get_conn()
        with self._lock:
            try:
                conn.execute("BEGIN")
                conn.execute("DELETE FROM pipeline_info WHERE experiment_accession = ?", (accession,))
                count = 0
                for p in pipelines:
                    conn.execute(
                        """
                        INSERT INTO pipeline_info
                        (experiment_accession, pipeline_title, pipeline_version, software_list, analysis_status)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            accession,
                            p.get("title", ""),
                            p.get("version", ""),
                            json.dumps(p.get("software", [])),
                            p.get("status", ""),
                        ),
                    )
                    count += 1
                conn.commit()
                return count
            except Exception:
                conn.rollback()
                raise

    def get_pipeline_info(self, accession: str) -> list[dict]:
        """Get pipeline info for a tracked experiment."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM pipeline_info WHERE experiment_accession = ?",
            (accession,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["software_list"] = json.loads(d.get("software_list", "[]"))
            result.append(d)
        return result

    # ------------------------------------------------------------------
    # Quality metrics
    # ------------------------------------------------------------------

    def store_quality_metrics(self, accession: str, metrics: list[dict]) -> int:
        """Store quality metrics for an experiment.

        Uses an explicit transaction so the DELETE + INSERTs are atomic.
        If any INSERT fails, the existing data is preserved (not erased).
        Holds self._lock for the entire transaction to prevent concurrent
        BEGIN on the same connection (which raises OperationalError).
        """
        conn = self._get_conn()
        with self._lock:
            try:
                conn.execute("BEGIN")
                conn.execute("DELETE FROM quality_metrics WHERE experiment_accession = ?", (accession,))
                count = 0
                for m in metrics:
                    conn.execute(
                        """
                        INSERT INTO quality_metrics
                        (experiment_accession, file_accession, metric_type, metric_data)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            accession,
                            m.get("file_accession", ""),
                            m.get("metric_type", ""),
                            json.dumps(m.get("data", {})),
                        ),
                    )
                    count += 1
                conn.commit()
                return count
            except Exception:
                conn.rollback()
                raise

    def get_quality_metrics(self, accession: str) -> list[dict]:
        """Get quality metrics for a tracked experiment."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM quality_metrics WHERE experiment_accession = ?",
            (accession,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["metric_data"] = json.loads(d.get("metric_data", "{}"))
            result.append(d)
        return result

    # ------------------------------------------------------------------
    # Provenance / derived files
    # ------------------------------------------------------------------

    def log_derived_file(
        self,
        file_path: str,
        source_accessions: list[str],
        description: str = "",
        file_type: str = "",
        tool_used: str = "",
        parameters: str = "",
    ) -> int:
        """Log a file derived from ENCODE data. Returns the row ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO derived_files
            (file_path, source_accessions, description, created_at, file_type, tool_used, parameters)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                file_path,
                json.dumps(source_accessions),
                description,
                time.time(),
                file_type,
                tool_used,
                parameters,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore

    def get_derived_files(self, source_accession: str | None = None) -> list[dict]:
        """Get derived files, optionally filtered by source accession."""
        conn = self._get_conn()
        if source_accession:
            rows = conn.execute(
                "SELECT * FROM derived_files WHERE source_accessions LIKE ? ESCAPE '\\' ORDER BY created_at DESC",
                (f"%{escape_like(source_accession)}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM derived_files ORDER BY created_at DESC",
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["source_accessions"] = json.loads(d.get("source_accessions", "[]"))
            result.append(d)
        return result

    def get_provenance_chain(self, file_path: str) -> dict:
        """Get full provenance chain for a derived file."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM derived_files WHERE file_path = ?",
            (file_path,),
        ).fetchone()
        if not row:
            return {"error": f"No provenance record for {file_path}"}
        d = dict(row)
        d["source_accessions"] = json.loads(d.get("source_accessions", "[]"))

        # Get info about source experiments
        sources = []
        for acc in d["source_accessions"]:
            exp = self.get_tracked_experiment(acc)
            if exp:
                sources.append(
                    {
                        "accession": acc,
                        "assay_title": exp.get("assay_title", ""),
                        "biosample_summary": exp.get("biosample_summary", ""),
                        "organism": exp.get("organism", ""),
                    }
                )
            else:
                sources.append({"accession": acc, "tracked": False})

        d["source_experiments"] = sources
        return d

    # ------------------------------------------------------------------
    # Compatibility analysis
    # ------------------------------------------------------------------

    def analyze_compatibility(self, accession1: str, accession2: str) -> dict:
        """Analyze whether two experiments are compatible for combined analysis."""
        exp1 = self.get_tracked_experiment(accession1)
        exp2 = self.get_tracked_experiment(accession2)

        if not exp1:
            return {"error": f"Experiment {accession1} not tracked. Track it first."}
        if not exp2:
            return {"error": f"Experiment {accession2} not tracked. Track it first."}

        issues: list[str] = []
        warnings: list[str] = []
        compatible_aspects: list[str] = []

        # Check organism
        if exp1.get("organism") and exp2.get("organism"):
            if exp1["organism"] != exp2["organism"]:
                issues.append(
                    f"Different organisms: {exp1['organism']} vs {exp2['organism']}. "
                    "Cross-species comparison requires ortholog mapping."
                )
            else:
                compatible_aspects.append(f"Same organism: {exp1['organism']}")

        # Check assembly
        if exp1.get("assembly") and exp2.get("assembly"):
            if exp1["assembly"] != exp2["assembly"]:
                issues.append(
                    f"Different genome assemblies: {exp1['assembly']} vs {exp2['assembly']}. "
                    "Coordinate liftover needed before comparison."
                )
            else:
                compatible_aspects.append(f"Same assembly: {exp1['assembly']}")

        # Check assay type
        if exp1.get("assay_title") and exp2.get("assay_title"):
            if exp1["assay_title"] != exp2["assay_title"]:
                warnings.append(
                    f"Different assay types: {exp1['assay_title']} vs {exp2['assay_title']}. "
                    "Multi-omic integration may be needed."
                )
            else:
                compatible_aspects.append(f"Same assay: {exp1['assay_title']}")

        # Check biosample type
        if exp1.get("biosample_type") and exp2.get("biosample_type"):
            if exp1["biosample_type"] != exp2["biosample_type"]:
                warnings.append(
                    f"Different biosample types: {exp1['biosample_type']} vs {exp2['biosample_type']}. "
                    "Results may reflect sample type differences."
                )
            else:
                compatible_aspects.append(f"Same biosample type: {exp1['biosample_type']}")

        # Check organ
        if exp1.get("organ") and exp2.get("organ"):
            if exp1["organ"] != exp2["organ"]:
                warnings.append(f"Different organs/tissues: {exp1['organ']} vs {exp2['organ']}.")
            else:
                compatible_aspects.append(f"Same organ: {exp1['organ']}")

        # Check target (for ChIP-seq)
        if exp1.get("target") or exp2.get("target"):
            if exp1.get("target") != exp2.get("target"):
                if exp1.get("target") and exp2.get("target"):
                    warnings.append(f"Different targets: {exp1['target']} vs {exp2['target']}.")
            else:
                compatible_aspects.append(f"Same target: {exp1['target']}")

        # Check replication type
        if exp1.get("replication_type") and exp2.get("replication_type"):
            if exp1["replication_type"] != exp2["replication_type"]:
                warnings.append(f"Different replication: {exp1['replication_type']} vs {exp2['replication_type']}.")

        # Check lab
        if exp1.get("lab") and exp2.get("lab"):
            if exp1["lab"] != exp2["lab"]:
                warnings.append(f"Different labs: {exp1['lab']} vs {exp2['lab']}. Batch effects possible.")
            else:
                compatible_aspects.append(f"Same lab: {exp1['lab']}")

        # Determine overall compatibility
        if issues:
            verdict = "NOT_COMPATIBLE"
            recommendation = (
                "These experiments have fundamental incompatibilities that must be resolved before combined analysis."
            )
        elif warnings:
            verdict = "COMPATIBLE_WITH_CAVEATS"
            recommendation = "These experiments can be compared, but the warnings should be addressed in your analysis."
        else:
            verdict = "FULLY_COMPATIBLE"
            recommendation = "These experiments appear fully compatible for combined analysis."

        return {
            "experiment_1": {
                "accession": accession1,
                "assay": exp1.get("assay_title", ""),
                "biosample": exp1.get("biosample_summary", ""),
            },
            "experiment_2": {
                "accession": accession2,
                "assay": exp2.get("assay_title", ""),
                "biosample": exp2.get("biosample_summary", ""),
            },
            "verdict": verdict,
            "recommendation": recommendation,
            "compatible_aspects": compatible_aspects,
            "issues": issues,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Citation export
    # ------------------------------------------------------------------

    def export_citations_bibtex(self, accessions: list[str] | None = None) -> str:
        """Export publications as BibTeX format."""
        conn = self._get_conn()
        if accessions:
            placeholders = ",".join("?" for _ in accessions)
            rows = conn.execute(
                f"SELECT * FROM publications WHERE experiment_accession IN ({placeholders})",
                accessions,
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM publications").fetchall()

        entries = []
        for r in rows:
            pub = dict(r)
            key = pub.get("pmid", "") or pub.get("doi", "") or f"encode_{pub.get('experiment_accession', '')}"
            key = key.replace("/", "_").replace(".", "_")

            entry = f"@article{{{key},\n"
            if pub.get("title"):
                entry += f"  title = {{{pub['title']}}},\n"
            if pub.get("authors"):
                entry += f"  author = {{{pub['authors']}}},\n"
            if pub.get("journal"):
                entry += f"  journal = {{{pub['journal']}}},\n"
            if pub.get("year"):
                entry += f"  year = {{{pub['year']}}},\n"
            if pub.get("doi"):
                entry += f"  doi = {{{pub['doi']}}},\n"
            if pub.get("pmid"):
                entry += f"  pmid = {{{pub['pmid']}}},\n"
            entry += f"  note = {{ENCODE experiment: {pub.get('experiment_accession', '')}}},\n"
            entry += "}"
            entries.append(entry)

        return "\n\n".join(entries)

    def export_citations_ris(self, accessions: list[str] | None = None) -> str:
        """Export publications as RIS format (compatible with Endnote, Zotero, Mendeley)."""
        conn = self._get_conn()
        if accessions:
            placeholders = ",".join("?" for _ in accessions)
            rows = conn.execute(
                f"SELECT * FROM publications WHERE experiment_accession IN ({placeholders})",
                accessions,
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM publications").fetchall()

        entries = []
        for r in rows:
            pub = dict(r)
            lines = ["TY  - JOUR"]
            if pub.get("title"):
                lines.append(f"TI  - {pub['title']}")
            if pub.get("authors"):
                for author in pub["authors"].split(", "):
                    lines.append(f"AU  - {author}")
            if pub.get("journal"):
                lines.append(f"JO  - {pub['journal']}")
            if pub.get("year"):
                lines.append(f"PY  - {pub['year']}")
            if pub.get("doi"):
                lines.append(f"DO  - {pub['doi']}")
            if pub.get("pmid"):
                lines.append(f"AN  - PMID:{pub['pmid']}")
            lines.append(f"N1  - ENCODE experiment: {pub.get('experiment_accession', '')}")
            if pub.get("abstract"):
                lines.append(f"AB  - {pub['abstract']}")
            lines.append("ER  - ")
            entries.append("\n".join(lines))

        return "\n\n".join(entries)

    # ------------------------------------------------------------------
    # Metadata table export
    # ------------------------------------------------------------------

    def get_metadata_table(self, accessions: list[str] | None = None) -> list[dict]:
        """Get a metadata table of tracked experiments for analysis."""
        conn = self._get_conn()
        if accessions:
            placeholders = ",".join("?" for _ in accessions)
            rows = conn.execute(
                f"SELECT * FROM tracked_experiments WHERE accession IN ({placeholders}) ORDER BY tracked_at DESC",
                accessions,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tracked_experiments ORDER BY tracked_at DESC",
            ).fetchall()

        table = []
        for r in rows:
            d = dict(r)
            # Remove raw_metadata from table view (too large)
            d.pop("raw_metadata", None)
            # Add publication count
            pub_count = conn.execute(
                "SELECT COUNT(*) FROM publications WHERE experiment_accession = ?",
                (d["accession"],),
            ).fetchone()[0]
            d["publication_count"] = pub_count
            # Add derived file count
            derived_count = conn.execute(
                "SELECT COUNT(*) FROM derived_files WHERE source_accessions LIKE ? ESCAPE '\\'",
                (f"%{escape_like(d['accession'])}%",),
            ).fetchone()[0]
            d["derived_file_count"] = derived_count
            table.append(d)

        return table

    # ------------------------------------------------------------------
    # External references (cross-server linking)
    # ------------------------------------------------------------------

    def link_reference(
        self,
        accession: str,
        reference_type: str,
        reference_id: str,
        description: str = "",
    ) -> dict:
        """Link an external reference to a tracked experiment."""
        validate_reference_type(reference_type)
        conn = self._get_conn()

        # Check experiment is tracked
        exp = conn.execute(
            "SELECT accession FROM tracked_experiments WHERE accession = ?",
            (accession,),
        ).fetchone()
        if not exp:
            return {"error": f"Experiment {accession} not tracked. Track it first."}

        try:
            conn.execute(
                """
                INSERT INTO external_references
                (experiment_accession, reference_type, reference_id, description, linked_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (accession, reference_type, reference_id, description, time.time()),
            )
            conn.commit()
            return {
                "action": "linked",
                "experiment_accession": accession,
                "reference_type": reference_type,
                "reference_id": reference_id,
            }
        except sqlite3.IntegrityError:
            return {
                "action": "already_linked",
                "experiment_accession": accession,
                "reference_type": reference_type,
                "reference_id": reference_id,
            }

    def get_references(
        self,
        accession: str | None = None,
        reference_type: str | None = None,
    ) -> list[dict]:
        """Get external references, optionally filtered by experiment or type."""
        conn = self._get_conn()
        query = "SELECT * FROM external_references WHERE 1=1"
        params: list[Any] = []

        if accession:
            query += " AND experiment_accession = ?"
            params.append(accession)
        if reference_type:
            validate_reference_type(reference_type)
            query += " AND reference_type = ?"
            params.append(reference_type)

        query += " ORDER BY linked_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def unlink_reference(
        self,
        accession: str,
        reference_type: str,
        reference_id: str,
    ) -> bool:
        """Remove an external reference link."""
        conn = self._get_conn()
        result = conn.execute(
            "DELETE FROM external_references WHERE experiment_accession = ? AND reference_type = ? AND reference_id = ?",
            (accession, reference_type, reference_id),
        )
        conn.commit()
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Data export (CSV/TSV/JSON)
    # ------------------------------------------------------------------

    def export_tracked_data(
        self,
        format: str = "csv",
        assay_title: str | None = None,
        organism: str | None = None,
        organ: str | None = None,
    ) -> str:
        """Export tracked experiments as CSV, TSV, or JSON."""
        experiments = self.list_tracked_experiments(
            assay_title=assay_title,
            organism=organism,
            organ=organ,
        )

        table = self.get_metadata_table([e["accession"] for e in experiments] if experiments else None)

        # Enrich with external reference counts and PMIDs
        conn = self._get_conn()
        for row in table:
            row.pop("raw_metadata", None)
            # Get PMIDs from publications
            pmids = conn.execute(
                "SELECT pmid FROM publications WHERE experiment_accession = ? AND pmid != ''",
                (row["accession"],),
            ).fetchall()
            row["pmids"] = ";".join(r[0] for r in pmids) if pmids else ""
            # Get external reference count
            ref_count = conn.execute(
                "SELECT COUNT(*) FROM external_references WHERE experiment_accession = ?",
                (row["accession"],),
            ).fetchone()[0]
            row["external_reference_count"] = ref_count

        if not table:
            if format == "json":
                return "[]"
            return ""

        if format == "json":
            return json.dumps(table, indent=2, default=str)

        # CSV / TSV
        sep = "," if format == "csv" else "\t"
        headers = [
            "accession",
            "assay_title",
            "target",
            "organism",
            "organ",
            "biosample_type",
            "biosample_summary",
            "lab",
            "assembly",
            "status",
            "date_released",
            "replication_type",
            "life_stage",
            "publication_count",
            "pmids",
            "derived_file_count",
            "external_reference_count",
        ]
        lines = [sep.join(headers)]
        for row in table:
            values = []
            for h in headers:
                val = str(row.get(h, ""))
                # Escape separators in values for CSV
                if sep in val or '"' in val:
                    val = '"' + val.replace('"', '""') + '"'
                values.append(val)
            lines.append(sep.join(values))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Collection summary
    # ------------------------------------------------------------------

    def summarize_collection(
        self,
        assay_title: str | None = None,
        organism: str | None = None,
        organ: str | None = None,
    ) -> dict:
        """Summarize tracked experiments by various groupings."""
        experiments = self.list_tracked_experiments(
            assay_title=assay_title,
            organism=organism,
            organ=organ,
        )

        if not experiments:
            return {
                "total_experiments": 0,
                "message": "No tracked experiments found matching filters.",
            }

        conn = self._get_conn()

        # Group by various fields
        by_assay: dict[str, int] = {}
        by_target: dict[str, int] = {}
        by_organism: dict[str, int] = {}
        by_organ: dict[str, int] = {}
        by_biosample_type: dict[str, int] = {}
        by_lab: dict[str, int] = {}

        for exp in experiments:
            assay = exp.get("assay_title", "") or "unknown"
            by_assay[assay] = by_assay.get(assay, 0) + 1

            target_val = exp.get("target", "") or "none"
            by_target[target_val] = by_target.get(target_val, 0) + 1

            org = exp.get("organism", "") or "unknown"
            by_organism[org] = by_organism.get(org, 0) + 1

            organ_val = exp.get("organ", "") or "unknown"
            by_organ[organ_val] = by_organ.get(organ_val, 0) + 1

            btype = exp.get("biosample_type", "") or "unknown"
            by_biosample_type[btype] = by_biosample_type.get(btype, 0) + 1

            lab_val = exp.get("lab", "") or "unknown"
            by_lab[lab_val] = by_lab.get(lab_val, 0) + 1

        # Totals scoped to the filtered experiments
        if experiments:
            accessions = [exp.get("accession", "") for exp in experiments]
            placeholders = ",".join("?" * len(accessions))
            total_pubs = conn.execute(
                f"SELECT COUNT(*) FROM publications WHERE experiment_accession IN ({placeholders})",
                accessions,
            ).fetchone()[0]
            # derived_files stores source_accessions as a JSON array, so use LIKE matching
            like_clauses = " OR ".join("source_accessions LIKE ? ESCAPE '\\'" for _ in accessions)
            like_params = [f"%{escape_like(acc)}%" for acc in accessions]
            total_derived = conn.execute(
                f"SELECT COUNT(*) FROM derived_files WHERE {like_clauses}",
                like_params,
            ).fetchone()[0]
            total_refs = conn.execute(
                f"SELECT COUNT(*) FROM external_references WHERE experiment_accession IN ({placeholders})",
                accessions,
            ).fetchone()[0]
        else:
            total_pubs = total_derived = total_refs = 0

        return {
            "total_experiments": len(experiments),
            "total_publications": total_pubs,
            "total_derived_files": total_derived,
            "total_external_references": total_refs,
            "by_assay": dict(sorted(by_assay.items(), key=lambda x: -x[1])),
            "by_target": dict(sorted(by_target.items(), key=lambda x: -x[1])[:20]),
            "by_organism": dict(sorted(by_organism.items(), key=lambda x: -x[1])),
            "by_organ": dict(sorted(by_organ.items(), key=lambda x: -x[1])[:20]),
            "by_biosample_type": dict(sorted(by_biosample_type.items(), key=lambda x: -x[1])),
            "by_lab": dict(sorted(by_lab.items(), key=lambda x: -x[1])[:20]),
        }

    @property
    def db_path(self) -> str:
        return str(self._db_path)

    @property
    def stats(self) -> dict:
        """Get tracker statistics."""
        conn = self._get_conn()
        return {
            "tracked_experiments": conn.execute("SELECT COUNT(*) FROM tracked_experiments").fetchone()[0],
            "publications": conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0],
            "pipeline_records": conn.execute("SELECT COUNT(*) FROM pipeline_info").fetchone()[0],
            "quality_metrics": conn.execute("SELECT COUNT(*) FROM quality_metrics").fetchone()[0],
            "derived_files": conn.execute("SELECT COUNT(*) FROM derived_files").fetchone()[0],
            "external_references": conn.execute("SELECT COUNT(*) FROM external_references").fetchone()[0],
            "db_path": str(self._db_path),
        }


def parse_encode_publications(references: list[dict]) -> list[dict]:
    """Parse ENCODE API references array into publication records."""
    pubs = []
    for ref in references:
        if isinstance(ref, str):
            continue  # Just a path reference, skip
        if not isinstance(ref, dict):
            continue

        # Extract identifiers
        identifiers = ref.get("identifiers", [])
        pmid = ""
        doi = ""
        for ident in identifiers:
            if isinstance(ident, str):
                if ident.startswith("PMID:"):
                    pmid = ident.replace("PMID:", "")
                elif ident.startswith("doi:"):
                    doi = ident.replace("doi:", "")

        # Extract authors (limit to first 10; handle both string and list formats)
        authors_raw = ref.get("authors", "")
        if isinstance(authors_raw, list):
            authors = ", ".join(str(a) for a in authors_raw[:10])
        elif isinstance(authors_raw, str):
            authors = ", ".join(authors_raw.split(", ")[:10])
        else:
            authors = str(authors_raw)

        pubs.append(
            {
                "pmid": pmid,
                "doi": doi,
                "title": ref.get("title", ""),
                "authors": authors,
                "journal": ref.get("journal", ""),
                "year": ref.get("date_published", "")[:4] if ref.get("date_published") else "",
                "abstract": ref.get("abstract", ""),
            }
        )
    return pubs


def parse_encode_pipelines(analyses: list[dict]) -> list[dict]:
    """Parse ENCODE API analyses array into pipeline records."""
    pipelines = []
    for analysis in analyses:
        if not isinstance(analysis, dict):
            continue

        # Extract pipeline info
        software_list = []
        for sw in analysis.get("pipeline_run_software", []):
            if isinstance(sw, dict):
                software_list.append(
                    {
                        "name": sw.get("name", ""),
                        "version": sw.get("version", ""),
                    }
                )

        pipelines.append(
            {
                "title": analysis.get("title", analysis.get("pipeline_title", "")),
                "version": analysis.get("pipeline_version", ""),
                "software": software_list,
                "status": analysis.get("status", ""),
            }
        )
    return pipelines
