# R010 -- synthetic / random data generation ---------------------------

#' Flag calls to random-data generators (`rnorm`, `runif`, `rpois`,
#' `rbinom`, `rexp`, `rgamma`, `rbeta`, `rmultinom`, `sample`,
#' `sample_n`, `sample_frac`).
#'
#' v1 heuristic: any `<SYMBOL_FUNCTION_CALL>` whose text matches one of
#' the known random-data generators is flagged at the line of the call.
#' We deliberately don't try to distinguish "data-like" assignments from
#' diagnostic randomness — false positives are cheap and the waiver
#' layer (`ANALYSIS_OK[...]`) handles legitimate uses.
#'
#' @keywords internal
synthetic_data_linter <- function() {
  random_fns <- c(
    "rnorm", "runif", "rpois", "rbinom", "rexp",
    "rgamma", "rbeta", "rmultinom",
    "sample", "sample_n", "sample_frac"
  )

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    predicate <- paste0(
      "text()=",
      paste0("'", random_fns, "'", collapse = " or text()="),
      ""
    )
    calls <- xml2::xml_find_all(
      xml,
      paste0("//SYMBOL_FUNCTION_CALL[", predicate, "]")
    )

    lapply(as.list(calls), function(node) {
      fn <- xml2::xml_text(node)
      line <- as.integer(xml2::xml_attr(node, "line1"))
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = line,
        type        = "warning",
        message     = paste0(
          "R010: call to random-data generator `", fn,
          "()` — synthetic data should be confined to tests/fixtures."
        )
      )
    })
  })
}
