#' Main CLI entry point.
#'
#' Invoked from `inst/bin/scilintr` or
#' `Rscript -e 'scilintr::main()'`.
#'
#' @param args Character vector of command-line arguments.
#' @export
main <- function(args = commandArgs(trailingOnly = TRUE)) {
  root <- if (length(args) >= 1L) args[1] else "."
  findings <- lint_project(root)
  if (length(findings) == 0L) {
    message("scilintr: no findings")
    return(invisible(0L))
  }
  for (f in findings) cat(format(f), "\n", sep = "")
  message(sprintf("scilintr: %d finding(s)", length(findings)))
  invisible(1L)
}
