# R035 -- label-tainted file reads in selection-stage scripts --------------

#' Flag `read.csv` / `read_csv` / `read.table` / `read.delim` / `fread` calls
#' in a `# STAGE: selection` file whose path argument's basename matches a
#' label-tainted pattern (e.g. `gt_*`, `*_oracle_*`, `*_recall_*`, etc.).
#'
#' Even when a selection-stage script only reads one "harmless" column from
#' such a file, the rows / panel that ended up in the CSV were chosen using
#' labels -- so the downstream selection is laundered through the file name.
#' See analysis_lint_strategy.md #35.
#'
#' Stage gate: the linter scans the first 10 lines for a `# STAGE: <name>`
#' marker and fires only when `<name>` is exactly `selection`. Untagged or
#' otherwise-tagged files are left to other rules.
#'
#' Hardcoded label-tainted regex (v1, applied to `basename(path)`):
#'   `(^|_)(gt|oracle|truth|evaluated|recall|label)(_|\d|\.)`
#' This anchors on `_`/start and accepts a trailing digit (so `gt17_*.csv`
#' fires), underscore (so `*_oracle_*.csv` fires), or `.` (so `gt.csv` would
#' fire too). Project-config extension is left for a future iteration.
#'
#' Waivers (e.g. `ANALYSIS_OK[oracle-file-read]`) are honoured by the waiver
#' layer; this linter just emits the raw finding.
#'
#' @keywords internal
label_tainted_input_linter <- function() {
  TAINT_RE <- "(^|_)(gt|oracle|truth|evaluated|recall|label)(_|\\d|\\.)"
  READS <- c("read.csv", "read.table", "read_csv", "read.delim", "fread")

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    filename <- source_expression$filename
    if (is.null(filename) || !nzchar(filename) || !file.exists(filename)) {
      return(list())
    }

    stage <- detect_file_stage(filename)
    if (is.na(stage) || !identical(stage, "selection")) return(list())

    name_pred <- paste0("text()='", READS, "'", collapse = " or ")
    read_calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[", name_pred, "]]"
      )
    )

    findings <- list()
    for (call in as.list(read_calls)) {
      str_arg <- xml2::xml_find_first(call, ".//STR_CONST[1]")
      if (inherits(str_arg, "xml_missing")) next
      if (length(str_arg) == 0L) next
      raw <- xml2::xml_text(str_arg)
      val <- gsub('^["\']|["\']$', "", raw)
      if (!nzchar(val)) next
      bn <- basename(val)
      if (grepl(TAINT_RE, bn, perl = TRUE)) {
        findings[[length(findings) + 1L]] <- lintr::Lint(
          filename    = filename,
          line_number = as.integer(xml2::xml_attr(call, "line1")),
          type        = "warning",
          message     = paste0(
            "R035: selection-stage read of label-tainted file '", bn,
            "' -- the rows in this CSV were chosen using labels, so any",
            " column read here inherits that selection (see",
            " analysis_lint_strategy.md #35). Move the read into a",
            " `# STAGE: evaluation` script, or add an ANALYSIS_OK waiver",
            " demonstrating the column is genuinely label-independent."
          )
        )
      }
    }

    findings
  })
}
