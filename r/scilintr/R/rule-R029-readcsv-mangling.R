# R029 -- read.csv() column-name mangling ------------------------------

#' Flag `read.csv()` then string-keyed column lookup with mangled chars.
#'
#' R's `read.csv()` / `read.table()` rewrite column names: `-`, `>`,
#' `:` become `.`, and names starting with a digit get an `X` prefix.
#' A subsequent `df[["17-38733306C>T"]]` or `` df$`17-38733306C>T` ``
#' then silently returns NULL with no error or warning. Passing
#' `check.names = FALSE` (or using `readr::read_csv`) avoids the
#' rewrite.
#'
#' Two-phase, single-pass detection:
#'  1. File-level: if the script contains no `read.csv` / `read.table`
#'     call, or every such call passes `check.names = FALSE`, bail.
#'  2. Per-expression: flag string-literal column lookups
#'     (`df[["..."]]`) and backtick-symbol lookups
#'     (`` df$`...` ``) whose name carries `-`, `>`, `:`, or a leading
#'     digit.
#'
#' Both `df[["..."]]` (STR_CONST) and `` df$`...` `` (OP-DOLLAR /
#' SYMBOL) forms are handled.
#'
#' @keywords internal
readcsv_mangling_linter <- function() {
  mangle_re <- "[-:>]|^[\"`]?\\d"
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    file_text <- paste(
      readLines(source_expression$filename, warn = FALSE),
      collapse = "\n"
    )
    has_unsafe_read <-
      grepl("read\\.(csv|table)\\s*\\(", file_text, perl = TRUE) &&
      !grepl("check\\.names\\s*=\\s*FALSE", file_text, perl = TRUE)
    if (!has_unsafe_read) return(list())

    # df[["..."]] : STR_CONST sandwiched between [[ and ]]
    str_nodes <- xml2::xml_find_all(
      xml,
      "//LBB/following-sibling::expr[1]/STR_CONST"
    )
    # df$`...` : OP-DOLLAR followed by SYMBOL with special chars
    sym_nodes <- xml2::xml_find_all(
      xml,
      "//OP-DOLLAR/following-sibling::SYMBOL"
    )

    flag <- function(node, raw) {
      bare <- gsub("^[\"'`]|[\"'`]$", "", raw)
      if (!grepl("[-:>]|^\\d", bare)) return(NULL)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R029: column lookup '", bare, "' contains characters that ",
          "read.csv() mangles; pass check.names = FALSE or use ",
          "readr::read_csv()."
        )
      )
    }

    out <- c(
      lapply(as.list(str_nodes), function(n) flag(n, xml2::xml_text(n))),
      lapply(as.list(sym_nodes), function(n) flag(n, xml2::xml_text(n)))
    )
    out[!vapply(out, is.null, logical(1))]
  })
}
