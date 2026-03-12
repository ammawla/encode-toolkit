---
name: quality-check
description: Assess ENCODE experiment quality using QC metrics and audit flags
---

Evaluate data quality for ENCODE experiments using standard metrics: FRiP, NSC, RSC for ChIP-seq; TSS enrichment for ATAC-seq; mapping rate for RNA-seq.

Use `encode_get_experiment` to retrieve audit information. Check for ERROR and NOT_COMPLIANT audit flags. Always require 2+ biological replicates.

Refer to the quality-assessment skill for detailed guidance.
