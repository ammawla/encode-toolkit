---
name: compare-experiments
description: Check if two ENCODE experiments are compatible for combined analysis
---

Compare two ENCODE experiments to determine if they can be analyzed together.

Both experiments must be tracked first with `encode_track_experiment`. Then use `encode_compare_experiments` to check organism, assembly, assay type, biosample, organ, target, replication type, and lab compatibility. It returns a verdict with issues, warnings, and recommendations.

Refer to the compare-biosamples skill for cross-biosample comparisons.
