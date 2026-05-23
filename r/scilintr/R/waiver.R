#' Detect a structured ANALYSIS_OK waiver near a given line.
#'
#' Scans up to `window` lines around `line_no` for a
#' `# ANALYSIS_OK[category]:` comment. Returns the category name if
#' found, NA otherwise. Roxygen comments (`#' @...`) are ignored so
#' an unrelated tag cannot spoof a waiver.
#'
#' @keywords internal
nearby_waiver <- function(file_lines, line_no, window = 8L) {
  lo <- max(1L, line_no - window)
  hi <- min(length(file_lines), line_no + window)
  if (lo > hi) return(NA_character_)

  block <- file_lines[lo:hi]
  block <- block[!grepl("^\\s*#'", block)]   # strip roxygen
  block <- paste(block, collapse = "\n")

  m <- regmatches(block, regexpr("ANALYSIS_OK\\[([a-zA-Z0-9_-]+)\\]:", block))
  if (length(m) == 0L) return(NA_character_)
  sub("ANALYSIS_OK\\[([a-zA-Z0-9_-]+)\\]:.*", "\\1", m)
}

#' Filter findings by removing those covered by a nearby ANALYSIS_OK waiver.
#'
#' @keywords internal
apply_waivers <- function(findings, file_text) {
  if (length(findings) == 0L) return(findings)
  lines <- strsplit(file_text, "\n", fixed = TRUE)[[1]]
  keep <- vapply(findings, function(f) {
    is.na(nearby_waiver(lines, f$line))
  }, logical(1))
  findings[keep]
}
