---
name: browse-files
description: List, search, and inspect ENCODE files by format, type, and assembly
---

Browse and inspect ENCODE files across experiments.

Use `encode_list_files` to see files within a specific experiment. Use `encode_search_files` to find file types across all experiments. Use `encode_get_file_info` for detailed metadata on a single file.

Common filters: file_format (bed, bigWig, fastq, bam), output_type (IDR thresholded peaks, signal of unique reads), assembly (GRCh38, mm10), preferred_default=True for ENCODE-recommended files.

Refer to the search-encode skill for detailed guidance.
