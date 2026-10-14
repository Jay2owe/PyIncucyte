# Browsing and export performance

Export planning bounds outstanding scan responses and releases unused response data as scans are processed. Image exports continue to stream timepoints. Catalogue and preview response parsing avoid repeated conversion work.

Exact image outputs, ordering, calibration, cancellation and resume are covered by regression tests. Performance depends on dataset size, instrument network speed and host load; some cold-preview measurements did not improve.
