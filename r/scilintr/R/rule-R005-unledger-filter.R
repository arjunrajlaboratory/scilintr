# R005 -- unledgered filtering / subsetting -----------------------------

#' Flag self-assignments that silently narrow a dataframe.
#'
#' Patterns like `df <- df[<cond>, ]`, `df <- subset(df, ...)`, and
#' `df <- df %>% filter(...)` drop rows without recording how many were
#' dropped or why. The matched rule (R005 in the strategy doc) is that
#' filtering is allowed when ledgered -- a sibling `ANALYSIS_OK[<tag>]`
#' waiver comment plus an observable drop record -- but unannotated
#' self-narrowing should be surfaced.
#'
#' Heuristic: LEFT_ASSIGN where the LHS SYMBOL name reappears as a SYMBOL
#' on the RHS, and the RHS contains either a `[` (OP-LEFT-BRACKET) or a
#' call to `filter` / `subset`. Waiver-comment suppression is the
#' responsibility of the cross-file aggregator.
#'
#' @keywords internal
unledger_filter_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    assigns <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[",
        "  LEFT_ASSIGN",
        "  and expr[1]/SYMBOL",
        "  and expr[2][",
        "    .//OP-LEFT-BRACKET",
        "    or .//SYMBOL_FUNCTION_CALL[text()='filter' or text()='subset']",
        "  ]",
        "]"
      )
    )

    bad <- lapply(as.list(assigns), function(node) {
      lhs_sym <- xml2::xml_find_first(node, "expr[1]/SYMBOL")
      if (length(lhs_sym) == 0L) return(NULL)
      name <- xml2::xml_text(lhs_sym)
      rhs_syms <- xml2::xml_find_all(node, "expr[2]//SYMBOL")
      if (!any(xml2::xml_text(rhs_syms) == name)) return(NULL)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste(
          "R005: self-assignment narrows", shQuote(name),
          "without a ledger -- record dropped rows or add an",
          "ANALYSIS_OK[<tag>] waiver."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}
