#' Lint a single R file.
#'
#' Runs every registered per-file linter against `path`, converts the
#' resulting `lintr::Lint` objects to `scilintr_finding` records, and
#' applies the `ANALYSIS_OK[...]` waiver filter.
#'
#' @param path Path to a `.R` file.
#' @param config Optional configuration list (loaded from `.scilintr.yml`).
#' @return A list of `scilintr_finding` records.
#' @export
lint_file <- function(path, config = NULL) {
  if (!file.exists(path)) return(list())

  linters <- per_file_linters()
  if (length(linters) == 0L) return(list())

  lints <- tryCatch(
    lintr::lint(path, linters = linters),
    error = function(e) list()
  )

  if (length(lints) == 0L) return(list())

  findings <- lapply(lints, lint_to_finding)

  file_text <- paste(readLines(path, warn = FALSE), collapse = "\n")
  apply_waivers(findings, file_text)
}

#' Lint an entire project directory.
#'
#' Walks every `.R` file, runs the per-file linters, then builds the
#' project index and runs the cross-file rules against it.
#'
#' @param root Project root directory.
#' @param config Optional configuration list.
#' @return A list of `scilintr_finding` records aggregated across files.
#' @export
lint_project <- function(root = ".", config = NULL) {
  files <- list.files(root, pattern = "\\.R$", recursive = TRUE,
                      full.names = TRUE)
  if (length(files) == 0L) return(list())

  per_file <- list()
  for (f in files) {
    per_file <- c(per_file, lint_file(f, config = config))
  }

  idx <- build_project_index(files, config = config)
  cross_findings <- run_cross_file_rules(idx)
  cross_findings <- filter_waivers_cross_file(cross_findings)

  c(per_file, cross_findings)
}

#' Run every registered cross-file rule against the project index.
#' @keywords internal
run_cross_file_rules <- function(idx) {
  rules <- cross_file_rules()
  if (length(rules) == 0L) return(list())
  out <- list()
  for (rid in names(rules)) {
    res <- tryCatch(rules[[rid]](idx), error = function(e) list())
    if (length(res) > 0L) out <- c(out, res)
  }
  out
}

#' Apply waivers to a list of cross-file Findings.
#'
#' Reads each finding's file from disk (cached across findings to the
#' same file) and removes findings covered by a nearby `ANALYSIS_OK[...]`.
#'
#' @keywords internal
filter_waivers_cross_file <- function(findings) {
  if (length(findings) == 0L) return(findings)
  cache <- new.env(parent = emptyenv())

  Filter(function(f) {
    if (!file.exists(f$file)) return(TRUE)
    key <- f$file
    text <- cache[[key]]
    if (is.null(text)) {
      text <- paste(readLines(f$file, warn = FALSE), collapse = "\n")
      cache[[key]] <- text
    }
    lines <- strsplit(text, "\n", fixed = TRUE)[[1]]
    is.na(nearby_waiver(lines, f$line))
  }, findings)
}

#' Convert a single `lintr::Lint` to a `scilintr_finding`.
#'
#' Pulls the rule ID from `lint$linter` (set by the registry key when
#' the linter is dispatched). Strips a trailing `_linter` suffix if
#' lintr added one.
#'
#' @keywords internal
lint_to_finding <- function(lint) {
  rule_id <- sub("_linter$", "", as.character(lint$linter))
  Finding(
    file = normalizePath(lint$filename, mustWork = FALSE),
    line = as.integer(lint$line_number),
    rule = rule_id,
    message = as.character(lint$message),
    severity = as.character(lint$type)
  )
}
