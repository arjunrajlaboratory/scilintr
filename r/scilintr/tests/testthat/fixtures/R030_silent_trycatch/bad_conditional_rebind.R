# EXPECTED: R030 at line 9

# The rebind is guarded by a flag but still runs on the error path:
# downstream stages silently run on a NULL cohort. A `<<-` nested in
# control flow escapes the handler just the same as a top-level one.
tryCatch(
  cohort <- load_cohort(path),
  error = function(e) {
    if (allow_empty) cohort <<- NULL
  }
)
