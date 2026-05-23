#' R024 -- Smuggled function-signature defaults
#'
#' Flag `function(arg = <literal>)` where the literal is "interesting":
#' a NUM_CONST whose value is not in `{0, 1, -1, NA*, Inf, -Inf, TRUE,
#' FALSE}` (with optional `L` suffix), or a STR_CONST whose unwrapped
#' value is not the empty string.
#'
#' Boring defaults (`0`, `1`, `NA`, `NULL`, `TRUE`, `""`) are sentinels,
#' not scientific choices. Calls (e.g. `c("a","b")`) and absent defaults
#' are not literals and are skipped by construction.
#'
#' @keywords internal
smuggled_default_linter <- function() {
  trivial_num <- c(
    "0", "1", "-1", "0L", "1L", "-1L",
    "NA", "NA_real_", "NA_integer_", "NA_character_", "NA_complex_",
    "Inf", "-Inf", "TRUE", "FALSE", "NULL"
  )

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Defaults: an EQ_FORMALS followed by an expr whose sole child is a literal.
    nodes <- xml2::xml_find_all(
      xml,
      "//EQ_FORMALS/following-sibling::expr[1][NUM_CONST or STR_CONST]"
    )

    bad <- lapply(as.list(nodes), function(n) {
      children <- xml2::xml_children(n)
      if (length(children) != 1L) return(NULL)
      tag <- xml2::xml_name(children[[1]])
      txt <- xml2::xml_text(children[[1]])
      interesting <- if (tag == "NUM_CONST") {
        !(txt %in% trivial_num)
      } else if (tag == "STR_CONST") {
        nchar(txt) > 2L  # everything quoted; "" and '' have nchar 2
      } else {
        FALSE
      }
      if (!interesting) return(NULL)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(n, "line1")),
        type        = "warning",
        message     = paste0(
          "R024: function-signature default `", txt,
          "` encodes a scientific choice -- move to config or document with ",
          "ANALYSIS_OK[smuggled-default] waiver."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}
