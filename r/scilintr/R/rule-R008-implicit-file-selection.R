# R008 -- implicit file selection ---------------------------------------

#' Flag implicit file selection patterns.
#'
#' Two patterns flagged:
#'   1. String literals containing suspicious filename tokens
#'      (latest, _old, old_, backup, previous, tmp_, _tmp, temp_,
#'      _temp, copy_, _copy, final_final, archive). Case-insensitive.
#'   2. mtime-based file picking: an expression containing both
#'      `file.info` and `mtime` symbols (e.g.
#'      `files[which.max(file.info(files)$mtime)]`).
#'
#' Waivers (`# ANALYSIS_OK[...]`) are handled by the harness layer;
#' this linter just emits Lints.
#'
#' @keywords internal
implicit_file_selection_linter <- function() {
  suspicious_re <- paste0(
    "(?i)(latest|_old|old_|backup|previous|",
    "tmp_|_tmp|temp_|_temp|copy_|_copy|final_final|archive)"
  )

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    lints <- list()

    # Pattern 1: suspicious string literals.
    strs <- xml2::xml_find_all(xml, "//STR_CONST")
    for (s in as.list(strs)) {
      txt <- xml2::xml_text(s)
      # Strip surrounding quotes for matching.
      val <- gsub('^["\']|["\']$', "", txt)
      if (grepl(suspicious_re, val, perl = TRUE)) {
        lints[[length(lints) + 1L]] <- lintr::Lint(
          filename    = source_expression$filename,
          line_number = as.integer(xml2::xml_attr(s, "line1")),
          type        = "warning",
          message     = paste0(
            "R008: suspicious filename literal (", val,
            ") -- pin to an explicit release identifier."
          )
        )
      }
    }

    # Pattern 2: mtime-based selection. Find any expression that
    # contains both a `file.info` call and a `$mtime` access.
    file_info_calls <- xml2::xml_find_all(
      xml, "//SYMBOL_FUNCTION_CALL[text()='file.info']"
    )
    for (fi in as.list(file_info_calls)) {
      # Walk up to the enclosing expr that also references mtime.
      enclosing <- xml2::xml_find_first(
        fi,
        "ancestor::expr[descendant::SYMBOL[text()='mtime'] or descendant::OP-DOLLAR/following-sibling::*[text()='mtime']][1]"
      )
      if (length(enclosing) > 0L && !is.na(xml2::xml_attr(enclosing, "line1"))) {
        lints[[length(lints) + 1L]] <- lintr::Lint(
          filename    = source_expression$filename,
          line_number = as.integer(xml2::xml_attr(enclosing, "line1")),
          type        = "warning",
          message     = paste(
            "R008: file picked by mtime (file.info(...)$mtime) --",
            "pin to an explicit release identifier instead."
          )
        )
      }
    }

    lints
  })
}
