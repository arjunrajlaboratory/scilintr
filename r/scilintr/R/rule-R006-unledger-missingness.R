#' Flag unledger missingness coercion/imputation calls.
#'
#' v1 detects bare `na.omit(...)` calls. Stripping NAs silently
#' discards rows without an audit trail; analyses should either
#' scope the drop (`df[!is.na(df$col), ]`) or carry an
#' `ANALYSIS_OK[missingness]` ledger comment documenting the
#' exclusion. Future versions should extend to `na.exclude`,
#' `tidyr::replace_na`, `drop_na`, and top-level `as.numeric`
#' coercions; ledger-comment recognition is also deferred.
#'
#' @keywords internal
unledger_missingness_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml,
      "//SYMBOL_FUNCTION_CALL[text()='na.omit']"
    )

    lapply(as.list(calls), function(node) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste(
          "R006: na.omit() silently drops rows with NAs —",
          "scope the drop or add an ANALYSIS_OK[missingness] ledger comment."
        )
      )
    })
  })
}
