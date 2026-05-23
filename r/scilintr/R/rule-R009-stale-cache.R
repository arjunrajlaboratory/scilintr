# R009 -- stale cache without input fingerprint ------------------------

#' Flag `if (file.exists(<X>)) return(read*(...))` single-statement bodies.
#'
#' A cache short-circuit that returns a previously serialized result
#' without comparing an input fingerprint is a stale-cache hazard: if
#' upstream inputs change, the cached value is silently returned and
#' the analysis quietly drifts from its inputs.
#'
#' Detection (v1): an `if` whose condition calls `file.exists(...)` and
#' whose body is a *single* statement calling `return(readRDS(...))`
#' (or `read_rds`, `read.csv`, `read_csv`). Multi-statement `{...}`
#' bodies are spared on the assumption that the extra statements
#' implement a fingerprint check -- the orchestrator's waiver layer
#' handles any remaining false positives.
#'
#' @keywords internal
stale_cache_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    readers <- c("readRDS", "read_rds", "read.csv", "read_csv")
    reader_pred <- paste0(
      "SYMBOL_FUNCTION_CALL[",
      paste0("text()='", readers, "'", collapse = " or "),
      "]"
    )

    # `<expr>` nodes that are if-statements whose condition is a
    # `file.exists(...)` call, whose body is NOT a `{...}` block, and
    # whose body contains a call to one of the readers above.
    if_exprs <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[IF",
        " and expr[1]/expr[1]/SYMBOL_FUNCTION_CALL[text()='file.exists']",
        " and expr[2][not(OP-LEFT-BRACE)]",
        " and expr[2]//", reader_pred,
        "]"
      )
    )

    lapply(as.list(if_exprs), function(node) {
      body <- xml2::xml_find_first(node, "expr[2]")
      line <- as.integer(xml2::xml_attr(body, "line1"))
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = line,
        type        = "warning",
        message     = paste(
          "R009: cache short-circuit returns readRDS/read.csv without an",
          "input fingerprint check -- stale-cache hazard."
        )
      )
    })
  })
}
