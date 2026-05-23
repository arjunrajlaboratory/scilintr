#' Flag positional re-indexing of a dataframe by row/column count of another.
#'
#' Detects patterns like `metadata <- metadata[1:ncol(counts), ]` or
#' `metadata[seq_len(ncol(counts)), ]` where rows of one structure are
#' positionally trimmed/aligned to the column or row count of another.
#' Such alignment is fragile: it silently succeeds even when the two
#' structures are in different orders. ID-based alignment
#' (e.g. `counts[, metadata$sample_id]`) is preferred.
#'
#' V1 finds any single-bracket access whose row-index expression contains
#' a call to `ncol`, `nrow`, or `seq_len`. Legitimate uses are handled
#' by the orchestrator's `ANALYSIS_OK[id-alignment]` waiver layer.
#'
#' @keywords internal
positional_alignment_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Single-bracket access where the index expression after `[` (the row
    # slot) contains a call to ncol/nrow/seq_len. Captures `df[1:ncol(x), ]`,
    # `df[seq_len(ncol(x)), ]`, `df[seq_len(nrow(x)), ]`, etc.
    xpath <- paste0(
      "//expr[",
      "OP-LEFT-BRACKET",
      " and OP-LEFT-BRACKET/following-sibling::expr[1]",
      "//SYMBOL_FUNCTION_CALL[",
      "text()='ncol' or text()='nrow' or text()='seq_len'",
      "]",
      "]"
    )

    nodes <- xml2::xml_find_all(xml, xpath)

    lapply(nodes, function(n) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(n, "line1")),
        type        = "warning",
        message     = paste(
          "R004: positional row/column slice driven by another structure's",
          "dimension (ncol/nrow/seq_len) -- align by shared identifier",
          "(e.g. df[, other$sample_id]) and assert identical() instead."
        )
      )
    })
  })
}
