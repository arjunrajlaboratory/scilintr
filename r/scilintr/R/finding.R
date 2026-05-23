#' Construct a Finding record.
#'
#' The unified finding schema is shared with the Python linter so
#' downstream tooling (CI reporters, agent prompts) is language-agnostic.
#'
#' @keywords internal
Finding <- function(file, line, rule, message,
                    severity = "warning",
                    suggested_fix = NA_character_,
                    waiver_status = "none") {
  structure(
    list(
      file = file,
      line = as.integer(line),
      rule = rule,
      message = message,
      severity = severity,
      suggested_fix = suggested_fix,
      waiver_status = waiver_status
    ),
    class = "scilintr_finding"
  )
}

#' @export
format.scilintr_finding <- function(x, ...) {
  sprintf("%s:%d [%s/%s] %s", x$file, x$line, x$rule, x$severity, x$message)
}

#' @export
print.scilintr_finding <- function(x, ...) {
  cat(format(x), "\n", sep = "")
  invisible(x)
}
