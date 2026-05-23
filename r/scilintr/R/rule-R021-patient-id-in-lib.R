# R021 -- patient/sample IDs hardcoded in library-stage code ---------------

#' Flag hardcoded patient/sample identifiers (and A191-specific SNP literals)
#' in files declared `# STAGE: library`.
#'
#' Stage detection: the rule scans the first 10 lines of the file for a
#' `# STAGE: <name>` directive. If `<name>` is not `library`, the rule
#' returns no findings. This keeps the rule scoped to sample-agnostic
#' library helpers; analysis scripts can legitimately mention `"A191"`,
#' `191L`, etc.
#'
#' v1 forbidden literal set (hardcoded):
#'   - NUM_CONST: `191`, `191L`, `193`, `193L`
#'   - STR_CONST: `"A191"`, `"A193"`
#'   - STR_CONST matching SNP-name pattern `^X\d+\.\d+[A-Z]+\.[A-Z]+$`
#'     (e.g., `"X17.76565019G.A"` — R-mangled SNP-id, which is necessarily
#'     dataset-specific and should not live in library code).
#'
#' Waiver suppression (`ANALYSIS_OK[sample-specific-default]` and similar)
#' is applied by the orchestrator, not here — this rule fires on every
#' offending literal regardless of nearby waiver comments.
#'
#' @keywords internal
patient_id_in_lib_linter <- function() {
  snp_re <- "^X\\d+\\.\\d+[A-Z]+\\.[A-Z]+$"
  bad_strs <- c("A191", "A193")
  num_xpath <- paste0(
    "//NUM_CONST[",
    "text()='191' or text()='193' or ",
    "text()='191L' or text()='193L'",
    "]"
  )

  lintr::Linter(function(source_expression) {
    filename <- source_expression$filename
    if (is.null(filename) || !nzchar(filename) || !file.exists(filename)) {
      return(list())
    }

    # Stage gate: only fire in `# STAGE: library` files.
    lines10 <- readLines(filename, n = 10L, warn = FALSE)
    stage_hits <- grep("^\\s*#\\s*STAGE:\\s*(\\S+)", lines10, value = TRUE)
    if (length(stage_hits) == 0L) return(list())
    stage <- sub("^\\s*#\\s*STAGE:\\s*(\\S+).*", "\\1", stage_hits[1])
    if (!identical(stage, "library")) return(list())

    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    out <- list()

    # Numeric literals: 191 / 193 / 191L / 193L
    num_nodes <- xml2::xml_find_all(xml, num_xpath)
    for (n in as.list(num_nodes)) {
      out[[length(out) + 1L]] <- lintr::Lint(
        filename    = filename,
        line_number = as.integer(xml2::xml_attr(n, "line1")),
        type        = "warning",
        message     = paste0(
          "R021: hardcoded patient/sample ID `", xml2::xml_text(n),
          "` in library-stage code — pass as an argument or ",
          "move to a manifest."
        )
      )
    }

    # String literals: "A191"/"A193" or R-mangled SNP-id pattern.
    str_nodes <- xml2::xml_find_all(xml, "//STR_CONST")
    for (s in as.list(str_nodes)) {
      raw <- xml2::xml_text(s)
      val <- gsub('^"|"$', "", gsub("^'|'$", "", raw))
      if (val %in% bad_strs || grepl(snp_re, val)) {
        out[[length(out) + 1L]] <- lintr::Lint(
          filename    = filename,
          line_number = as.integer(xml2::xml_attr(s, "line1")),
          type        = "warning",
          message     = paste0(
            "R021: hardcoded patient/SNP literal `", val,
            "` in library-stage code — pass as an argument or ",
            "move to a manifest."
          )
        )
      }
    }

    out
  })
}
