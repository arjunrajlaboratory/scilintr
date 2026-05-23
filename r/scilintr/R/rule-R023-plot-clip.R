# R023 -- plot transforms that suppress informative ranges -------------

#' Flag `pmax(<expr>, 0)` and `ylim(0, ...)`.
#'
#' Both patterns silently clip negative values, hiding informative
#' signed ranges (e.g. ARI dropping below 0). For v1 we look for the
#' literal `0` argument; later versions may also catch `pmin(x, 1)`,
#' `coord_cartesian(ylim = c(0, NA))`, etc.
#'
#' @keywords internal
plot_clip_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    mk_lint <- function(call_expr, msg) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(call_expr, "line1")),
        type        = "warning",
        message     = paste0("R023: ", msg)
      )
    }

    lints <- list()

    # Pattern 1: pmax(<expr>, 0) -- any arg is literal 0.
    pmax_calls <- xml2::xml_find_all(
      xml,
      "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='pmax']]"
    )
    for (call_expr in as.list(pmax_calls)) {
      zeros <- xml2::xml_find_all(
        call_expr,
        "./expr[position()>1][count(*)=1][NUM_CONST[text()='0']]"
      )
      if (length(zeros) > 0L) {
        lints[[length(lints) + 1L]] <- mk_lint(
          call_expr,
          "pmax(x, 0) clips negative values -- hides signed range."
        )
      }
    }

    # Pattern 2: ylim(0, ...) -- first arg is literal 0.
    ylim_calls <- xml2::xml_find_all(
      xml,
      "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='ylim']]"
    )
    for (call_expr in as.list(ylim_calls)) {
      first_arg <- xml2::xml_find_first(call_expr, "./expr[2]")
      if (length(first_arg) == 0L) next
      kids <- xml2::xml_children(first_arg)
      if (length(kids) == 1L &&
          xml2::xml_name(kids[[1]]) == "NUM_CONST" &&
          xml2::xml_text(kids[[1]]) == "0") {
        lints[[length(lints) + 1L]] <- mk_lint(
          call_expr,
          "ylim(0, ...) clips negative values -- hides signed range."
        )
      }
    }

    lints
  })
}
