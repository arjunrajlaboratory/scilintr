# R016 -- hardcoded sample IDs --------------------------------------------

#' Flag `c("S17", "S23", ...)` style hardcoded sample-ID exclusion lists.
#'
#' Heuristic (v1): any `c(...)` call that contains two or more `STR_CONST`
#' children whose unquoted value matches `^[A-Z]+\\d+$` (e.g., "S17",
#' "A191", "P001") is flagged at the line of the `c()` call. This catches
#' the canonical `exclude <- c("S17", "S23")` pattern from the strategy
#' doc. The rule fires regardless of waivers; waiver suppression is
#' applied by the dispatcher reading `ANALYSIS_OK[sample-exclusion]`
#' ledger comments — so `good_ledgered.R` still emits a Lint here.
#'
#' @keywords internal
hardcoded_sample_id_linter <- function() {
  sample_id_re <- "^[A-Z]+[0-9]+$"
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Each <expr> that is a call to `c(...)`.
    c_calls <- xml2::xml_find_all(
      xml,
      "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='c']]"
    )

    bad <- lapply(as.list(c_calls), function(call_node) {
      str_nodes <- xml2::xml_find_all(call_node, "./expr/STR_CONST")
      if (length(str_nodes) < 2L) return(NULL)
      raw <- xml2::xml_text(str_nodes)
      unquoted <- gsub('^"|"$', "", gsub("^'|'$", "", raw))
      matches <- grepl(sample_id_re, unquoted)
      if (sum(matches) < 2L) return(NULL)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(call_node, "line1")),
        type        = "warning",
        message     = paste(
          "R016: hardcoded sample IDs in c(...) —",
          "move exclusion list to a ledger file or document with",
          "ANALYSIS_OK[sample-exclusion]."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}
