# Superassigning a *real* recovered value on the failure path is a
# legitimate fallback (the analysis continues on a genuine object, not
# a placeholder), so the rebind costume must not fire here.
tryCatch(
  cohort <<- load_cohort(primary_path),
  error = function(e) {
    cohort <<- load_cohort(backup_path)
  }
)
