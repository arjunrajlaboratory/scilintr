# R013 -- hardcoded design formulas ---------------------------------------

#' Flag inline `design = ~ ...` formula literals.
#'
#' v1 heuristic: find any named-argument `design = <expr>` where the
#' RHS expression is a tilde formula literal (`<OP-TILDE>` in the XML
#' parse tree). Variables resolving to formulas (e.g.,
#' `design = design_formula`) are not flagged — only inline tildes.
#' Waiver suppression (`ANALYSIS_OK[contrast-definition]`) is handled
#' by the dispatcher; this rule always fires on inline tildes.
#'
#' @keywords internal
hardcoded_design_formula_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Named arg `design = <expr>` whose value expression contains a
    # top-level OP-TILDE (formula literal).
    rhs_nodes <- xml2::xml_find_all(
      xml,
      paste0(
        "//SYMBOL_SUB[text()='design']",
        "/following-sibling::expr[1][OP-TILDE]"
      )
    )

    bad <- lapply(as.list(rhs_nodes), function(rhs) {
      tilde <- xml2::xml_find_first(rhs, "./OP-TILDE")
      line <- xml2::xml_attr(tilde, "line1")
      if (is.na(line)) line <- xml2::xml_attr(rhs, "line1")
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(line),
        type        = "warning",
        message     = paste(
          "R013: hardcoded design formula (`design = ~ ...`) —",
          "move the formula to a config file and load it,",
          "or document with ANALYSIS_OK[contrast-definition]."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}
