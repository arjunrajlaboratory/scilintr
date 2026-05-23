# R018 -- unchecked convergence ----------------------------------------

#' Flag iterative-fit calls that lack a nearby convergence check.
#'
#' Iterative optimisers (lme4's `glmer`/`lmer`/`nlmer`, base `nls` and
#' `optim`, and `optimx::optimx`) can silently return non-converged
#' fits. Downstream inference on a non-converged model is unreliable.
#' Analyses should inspect `fit@optinfo$conv$lme4$messages`, the
#' `convergence` slot of `optim()` output, or otherwise programmatically
#' confirm convergence before using the fit.
#'
#' v1 heuristic: if any flagged fit call appears in the file AND the file
#' body contains none of the tokens `converged`, `conv$lme4`, or
#' `convergence`, every fit call in the file is flagged. The waiver layer
#' silences this elsewhere when a justified `ANALYSIS_OK[model-fit]`
#' comment is present.
#'
#' @keywords internal
unchecked_convergence_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//SYMBOL_FUNCTION_CALL[",
        "text()='glmer' or text()='lmer' or text()='nlmer' or ",
        "text()='nls' or text()='optim' or text()='optimx']"
      )
    )
    if (length(calls) == 0L) return(list())

    file_lines <- readLines(source_expression$filename, warn = FALSE)
    # Strip comments so waiver / docstring prose doesn't satisfy the check.
    file_lines <- sub("#.*$", "", file_lines)
    file_text <- paste(file_lines, collapse = "\n")
    has_check <- grepl("converged|conv\\$lme4|convergence", file_text)
    if (has_check) return(list())

    lapply(as.list(calls), function(node) {
      fn_name <- xml2::xml_text(node)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R018: ", fn_name, "() is an iterative fit but the file contains ",
          "no convergence check (looked for 'converged', 'conv$lme4', or ",
          "'convergence'); inspect the optimiser status before using the ",
          "fit or add an ANALYSIS_OK[model-fit] waiver."
        )
      )
    })
  })
}
