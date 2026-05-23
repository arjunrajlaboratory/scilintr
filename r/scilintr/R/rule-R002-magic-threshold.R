#' Flag magic numeric thresholds in comparison expressions.
#'
#' Detects patterns like `padj < 0.05`, `counts > 10`, `zscores > 3`
#' where a bare numeric literal sits on either side of a comparison
#' operator (`<`, `>`, `<=`, `>=`, `==`, `!=`). Named constants
#' (e.g. `padj < FDR_THRESHOLD`) are not flagged because no
#' `NUM_CONST` appears.
#'
#' Trivial literals (`0`, `1`, `-1`, `NA`, `TRUE`, `FALSE`, `Inf`,
#' etc.) are filtered out — loop sentinels (`length(x) > 0L`) and
#' presence checks (`nrow(df) > 0`) are not scientific thresholds.
#'
#' V1.1 still over-flags relative to the strict spec; legitimate
#' bare-number cases are handled by the orchestrator's
#' `ANALYSIS_OK[threshold]` waiver.
#'
#' @keywords internal
magic_threshold_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Comparison <expr> = parent <expr> that has a direct child
    # comparison operator AND a direct child <expr> wrapping a
    # NUM_CONST.
    cmp_ops <- "self::LT or self::GT or self::LE or self::GE or self::EQ or self::NE"
    candidates <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[(*[", cmp_ops, "]) and (expr[NUM_CONST])]"
      )
    )

    # Filter: only fire when at least one of the comparison's
    # NUM_CONST operands is a non-trivial value.
    hits <- list()
    for (cand in as.list(candidates)) {
      nums <- xml2::xml_find_all(cand, "expr/NUM_CONST")
      vals <- vapply(as.list(nums), xml2::xml_text, character(1))
      if (length(vals) == 0L) next
      if (all(vals %in% TRIVIAL_LITERALS)) next
      hits[[length(hits) + 1L]] <- cand
    }

    lapply(hits, function(n) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(n, "line1")),
        type        = "warning",
        message     = paste(
          "R002: magic numeric threshold in comparison —",
          "extract to a named constant (e.g. FDR_THRESHOLD)",
          "or move to config."
        )
      )
    })
  })
}
