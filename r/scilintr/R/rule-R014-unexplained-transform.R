#' Flag scientifically consequential transforms without explanation.
#'
#' Batch correction, residualization, and similar transforms silently
#' reshape downstream analysis. Require an `ANALYSIS_OK[...]` waiver
#' (handled elsewhere) that documents what was — and was not —
#' included as a covariate.
#'
#' Flagged calls (matched by function symbol):
#'   ComBat, combat, residualize, regress_out,
#'   remove_batch_effect, removeBatchEffect, regressOut
#'
#' @keywords internal
unexplained_transform_linter <- function() {
  flagged <- c(
    "ComBat", "combat",
    "residualize", "regress_out",
    "remove_batch_effect", "removeBatchEffect",
    "regressOut"
  )
  predicate <- paste0(
    "text()='", flagged, "'",
    collapse = " or "
  )
  xpath <- paste0("//SYMBOL_FUNCTION_CALL[", predicate, "]")

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    hits <- xml2::xml_find_all(xml, xpath)
    lapply(as.list(hits), function(node) {
      name <- xml2::xml_text(node)
      line <- as.integer(xml2::xml_attr(node, "line1"))
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = line,
        type        = "warning",
        message     = paste0(
          "R014: scientifically consequential transform `", name,
          "()` — document covariates with an ANALYSIS_OK[...] waiver."
        )
      )
    })
  })
}
