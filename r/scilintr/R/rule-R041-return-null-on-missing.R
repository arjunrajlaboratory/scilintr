# R041 -- return-NULL / return-NA on missing input ---------------------

#' Flag `if (!file.exists(path)) return(NULL/NA)`.
#'
#' This is a silent fallback wearing a different costume -- the explicit
#' fallback rule (R007) catches `try(...)` swallowing, but it doesn't
#' catch the cleaner-looking `if (!file.exists(path)) return(NULL)`.
#' Same end state: the missing input is treated as an acceptable empty
#' signal and propagates downstream.
#'
#' Detection: an `if(!file.exists(...))` whose body is -- or contains --
#' a `return(NULL)`, `return(NA)`, `return(NA_real_)`, etc. Returns of
#' other values (`return(0)`, `return(x)`) are not flagged.
#'
#' Ported from the Python rule `return-none-on-missing-input`.
#'
#' @keywords internal
return_null_on_missing_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Every `if(!file.exists(...))` expression in the file.
    if_exprs <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[IF",
        " and expr[1][OP-EXCLAMATION",
        " and .//SYMBOL_FUNCTION_CALL[text()='file.exists']]]"
      )
    )

    findings <- list()
    for (ie in as.list(if_exprs)) {
      # First two direct-child <expr>: [1] condition, [2] body.
      direct_exprs <- xml2::xml_find_all(ie, "expr")
      if (length(direct_exprs) < 2L) next
      body <- direct_exprs[[2]]

      # Any return(NULL|NA|NA_real_|...) inside the body -- directly or
      # wrapped in `{ ... }`. The literal child must be NULL_CONST, or
      # NUM_CONST whose text is NA / NA_*. `descendant-or-self::` so the
      # one-liner shape `if (!file.exists(path)) return(NULL)` -- where
      # the body IS the return call, not a descendant -- still matches.
      bad_returns <- xml2::xml_find_all(
        body,
        paste0(
          "descendant-or-self::expr[",
          "expr/SYMBOL_FUNCTION_CALL[text()='return']",
          " and expr[NULL_CONST",
          " or NUM_CONST[starts-with(text(),'NA')]]]"
        )
      )

      if (length(bad_returns) == 0L) next

      first_return <- bad_returns[[1]]
      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(first_return, "line1")),
        type        = "warning",
        message     = paste(
          "R041: function returns NULL/NA when input file is missing --",
          "silently propagates absence downstream; raise an error or",
          "add ANALYSIS_OK[optional-input]."
        )
      )
    }
    findings
  })
}
