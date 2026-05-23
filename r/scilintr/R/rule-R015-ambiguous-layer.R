# R015 -- ambiguous AnnData/Seurat layer ---------------------------------

#' Flag `GetAssayData(obj)` calls missing explicit `assay=` and `layer=`.
#'
#' `Seurat::GetAssayData()` silently falls back to the object's
#' "default assay" and "default layer", which depend on global state set
#' elsewhere in the pipeline. Pulling expression values without naming
#' the assay/layer is a common source of "I got counts when I wanted
#' data" bugs. Require at least one of `assay=` or `layer=` to be named
#' at the call site.
#'
#' @keywords internal
ambiguous_layer_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml,
      "//SYMBOL_FUNCTION_CALL[text()='GetAssayData']/parent::expr/parent::expr"
    )

    bad <- lapply(as.list(calls), function(call) {
      named <- xml2::xml_find_all(
        call,
        "SYMBOL_SUB[text()='assay' or text()='layer']"
      )
      if (length(named) > 0L) return(NULL)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(call, "line1")),
        type        = "warning",
        message     = paste(
          "R015: GetAssayData() called without explicit assay= and layer= --",
          "name the assay/layer to avoid relying on default-assay state."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}
