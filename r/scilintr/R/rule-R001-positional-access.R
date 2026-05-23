#' Flag raw positional dataframe access by integer literal.
#'
#' Detects patterns like `metadata[, 4]`, `df[[3]]`, and `df[, 2:5]`
#' where a bare integer literal sits in the column index slot of a
#' single-bracket access (after the *first* comma) or as the sole
#' index of a double-bracket access. Named-constant indices
#' (e.g. `metadata[, TREATMENT_COL_INDEX]`) use SYMBOL, not
#' NUM_CONST, and are not flagged.
#'
#' Trivial literals (`TRUE`, `FALSE`, `NA`, `0`, `1`, `Inf`, etc.) are
#' filtered out — they parse as `NUM_CONST` in xmlparsedata but are
#' never positional indices. The `drop = FALSE` argument of
#' `df[, j, drop = FALSE]` is the canonical false-positive this guards
#' against.
#'
#' V1.1 is still trigger-happy on real integer indices. Legitimate
#' uses are handled by the orchestrator's
#' `ANALYSIS_OK[positional-access]` waiver layer.
#'
#' @keywords internal
positional_access_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # ---- single-bracket `<expr>[X, Y]` ---------------------------------
    # Only inspect the FIRST OP-COMMA's following expr (the column
    # index slot). Filter NUM_CONSTs against TRIVIAL_LITERALS so that
    # `drop = FALSE` etc. doesn't trigger the rule.
    single_candidates <- xml2::xml_find_all(
      xml,
      "//expr[OP-LEFT-BRACKET and OP-COMMA]"
    )
    single_hits <- list()
    for (cand in as.list(single_candidates)) {
      first_comma <- xml2::xml_find_first(cand, "OP-COMMA")
      if (length(first_comma) == 0L) next
      col_expr <- xml2::xml_find_first(
        first_comma,
        "following-sibling::expr[1]"
      )
      if (length(col_expr) == 0L) next
      nums <- xml2::xml_find_all(col_expr, ".//NUM_CONST")
      if (length(nums) == 0L) next
      vals <- vapply(as.list(nums), xml2::xml_text, character(1))
      if (any(!vals %in% TRIVIAL_LITERALS)) {
        single_hits[[length(single_hits) + 1L]] <- cand
      }
    }

    # ---- double-bracket `<expr>[[N]]` ----------------------------------
    double_candidates <- xml2::xml_find_all(xml, "//expr[LBB]")
    double_hits <- list()
    for (cand in as.list(double_candidates)) {
      lbb <- xml2::xml_find_first(cand, "LBB")
      if (length(lbb) == 0L) next
      idx_expr <- xml2::xml_find_first(
        lbb,
        "following-sibling::expr[1]"
      )
      if (length(idx_expr) == 0L) next
      nums <- xml2::xml_find_all(idx_expr, ".//NUM_CONST")
      if (length(nums) == 0L) next
      vals <- vapply(as.list(nums), xml2::xml_text, character(1))
      if (any(!vals %in% TRIVIAL_LITERALS)) {
        double_hits[[length(double_hits) + 1L]] <- cand
      }
    }

    lapply(c(single_hits, double_hits), function(n) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(n, "line1")),
        type        = "warning",
        message     = paste(
          "R001: positional dataframe access by integer literal —",
          "use a named column (e.g. df$treatment, df[[\"treatment\"]])",
          "or extract the index to a named constant."
        )
      )
    })
  })
}
