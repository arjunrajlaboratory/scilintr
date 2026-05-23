# ANALYSIS_OK[api-retry]: retry same path after transient I/O error;
# no alternate-file fallback.
counts <- tryCatch(
  load_counts("/path"),
  error = function(e) {
    Sys.sleep(1)
    load_counts("/path")
  }
)
