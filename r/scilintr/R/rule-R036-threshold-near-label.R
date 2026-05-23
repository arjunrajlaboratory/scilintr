# R036 -- thresholds and bands defined adjacent to label reads ----------

#' Flag uppercase-constant assignments that are defined within a few lines
#' of a label-tainted read or label-column reference, inside a file tagged
#' `# STAGE: selection`.
#'
#' Selection-stage code must not pick its thresholds/bands by maximizing
#' a label-aware metric (e.g. ground-truth recall). When a constant like
#' `BAND <- sweep[which.max(sweep$gt_recall), ...]` sits next to a
#' `read.csv("..._gt_...")` call or a label column reference, the
#' threshold is effectively label-tuned. The fix is to either (a) move
#' the constant to `analysis_constants.yml` with a documented value, or
#' (b) move the threshold-selection code into a `# STAGE: evaluation`
#' script and pass the resulting number in by hand.
#'
#' Stage detection: scan the first 10 lines for `# STAGE: <name>`. Fires
#' only when `<name>` is exactly `selection`. Other stages (including
#' untagged files) are not flagged here.
#'
#' Detection: regex on the raw file text.
#'   * Constant lines: `^[A-Z][A-Z_0-9]+\\s*<-`
#'   * Label-tainted reads: paths/names containing `gt`, `oracle`,
#'     `truth`, `evaluated`, `recall` as a token.
#'   * Label column refs: a small hardcoded vocabulary (kept in sync
#'     with R033 for consistency).
#'   * A constant is flagged when at least one label-tainted line falls
#'     within +/- 6 lines of it.
#'
#' @keywords internal
threshold_near_label_linter <- function() {
  TAINT_RE  <- "(^|_|/|\")(gt|oracle|truth|evaluated|recall)(_|\\d|\\.|\")"
  LABEL_REF <- "(legacy_branch2_clone|legacy_clone|cell_type|treatment|diagnosis|condition|is_gt|truth_c1|truth|gt_label|gt_recall)"
  CONST_RE  <- "^[A-Z][A-Z_0-9]+\\s*<-"
  WINDOW    <- 6L

  lintr::Linter(function(source_expression) {
    filename <- source_expression$filename
    if (is.null(filename) || !nzchar(filename) || !file.exists(filename)) {
      return(list())
    }

    stage <- detect_file_stage(filename)
    if (is.na(stage) || !identical(stage, "selection")) return(list())

    lines <- readLines(filename, warn = FALSE)
    if (length(lines) == 0L) return(list())

    const_lines <- grep(CONST_RE, lines)
    if (length(const_lines) == 0L) return(list())

    label_lines <- grep(paste0(TAINT_RE, "|", LABEL_REF), lines, perl = TRUE)
    if (length(label_lines) == 0L) return(list())

    # Only emit one Lint per file from the first source_expression that
    # covers any of the constant lines, to avoid duplicate findings.
    expr_lines <- as.integer(source_expression$line)
    if (length(expr_lines) == 0L) return(list())

    findings <- list()
    for (cline in const_lines) {
      if (!(cline %in% expr_lines)) next
      if (!any(abs(label_lines - cline) <= WINDOW)) next
      const_name <- sub("\\s*<-.*$", "", lines[cline])
      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = filename,
        line_number = cline,
        type        = "warning",
        message     = paste0(
          "R036: constant `", const_name, "` is defined within ", WINDOW,
          " lines of a label-tainted read/column in a selection-stage file --",
          " move the value to `analysis_constants.yml`, or move the",
          " threshold-selection sweep into a `# STAGE: evaluation` script."
        )
      )
    }

    findings
  })
}
