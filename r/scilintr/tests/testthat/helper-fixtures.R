# Helpers for fixture-driven tests.

# Rules that operate over a whole directory (multiple .R files in the
# fixture). For these, the test driver runs lint_project(subdir).
CROSS_FILE_RULES <- c("R020", "R025", "R026")

#' Parse expected findings from a fixture file header.
#'
#' Looks for lines like:
#'   # EXPECTED: R030 at line 12
#'   # EXPECTED: R030 at line 12, R024 at line 7
#'
#' Returns a data.frame with columns `rule` and `line` (empty if none).
parse_expected <- function(path) {
  lines <- readLines(path, warn = FALSE)
  header <- grep("^# EXPECTED:", lines, value = TRUE)
  if (length(header) == 0L)
    return(data.frame(rule = character(), line = integer(),
                      stringsAsFactors = FALSE))

  payload <- sub("^# EXPECTED:\\s*", "", header)
  parts <- unlist(strsplit(payload, ",\\s*"))
  m <- regmatches(parts, regexec("(R[0-9]{3})\\s+at\\s+line\\s+([0-9]+)",
                                  parts))
  rule <- vapply(m, function(x) {
    if (length(x) >= 3L) x[2] else NA_character_
  }, character(1))
  line <- vapply(m, function(x) {
    if (length(x) >= 3L) as.integer(x[3]) else NA_integer_
  }, integer(1))
  data.frame(rule = rule, line = line, stringsAsFactors = FALSE)
}

#' List all top-level fixture directories.
fixture_dirs <- function() {
  root <- test_path("fixtures")
  if (!dir.exists(root)) return(character())
  list.dirs(root, recursive = FALSE, full.names = TRUE)
}

#' Return the rule ID a fixture directory belongs to (from its name).
fixture_rule <- function(dir) {
  sub("^(R[0-9]{3})_.*$", "\\1", basename(dir))
}

#' Bad fixture files in a directory (flat shape).
bad_fixtures_flat <- function(dir) {
  list.files(dir, pattern = "^bad_.*\\.R$", full.names = TRUE)
}

#' Good fixture files in a directory (flat shape).
good_fixtures_flat <- function(dir) {
  list.files(dir, pattern = "^good_.*\\.R$", full.names = TRUE)
}

#' Subdirectories named bad_* (for cross-file fixtures).
bad_fixture_dirs <- function(dir) {
  subs <- list.dirs(dir, recursive = FALSE, full.names = TRUE)
  subs[startsWith(basename(subs), "bad_")]
}

#' Subdirectories named good_*.
good_fixture_dirs <- function(dir) {
  subs <- list.dirs(dir, recursive = FALSE, full.names = TRUE)
  subs[startsWith(basename(subs), "good_")]
}

#' Lint one file. Tolerates a stub lint_file returning NULL/list().
lint_one <- function(path) {
  findings <- tryCatch(lint_file(path), error = function(e) list())
  if (is.null(findings)) list() else findings
}

#' Lint a directory as a project.
lint_dir <- function(dir) {
  findings <- tryCatch(lint_project(dir), error = function(e) list())
  if (is.null(findings)) list() else findings
}

#' Filter findings to those of a particular rule.
findings_for_rule <- function(findings, rule) {
  Filter(function(f) identical(f$rule, rule), findings)
}

#' Findings produced by linting a single fixture file or directory.
fixture_findings <- function(path, rule) {
  if (rule %in% CROSS_FILE_RULES) {
    # path is a directory holding multiple .R files
    lint_dir(path)
  } else {
    lint_one(path)
  }
}
