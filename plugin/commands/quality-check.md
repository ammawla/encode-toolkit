---
name: quality-check
description: Assess ENCODE experiment quality using audit counts and replicate counts
---

Evaluate data quality for ENCODE experiments.

Use `encode_get_experiment` to retrieve per-level audit counts (`audit_error_count`, `audit_not_compliant_count`, `audit_warning_count`, `audit_internal_action_count`) and `bio_replicate_count`. Check for non-zero ERROR and NOT_COMPLIANT counts, and expect 2+ biological replicates.

The tool returns audit counts, not the individual audit messages, and it returns no QC metric values. Read the standard metrics — FRiP, NSC, RSC for ChIP-seq; TSS enrichment for ATAC-seq; mapping rate for RNA-seq — from the experiment page on encodeproject.org, and use them as thresholds rather than expecting the server to report them.

Refer to the quality-assessment skill for detailed guidance.
