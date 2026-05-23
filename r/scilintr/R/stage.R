#' Detect the `# STAGE: <name>` tag in a file's first 10 lines.
#'
#' @param path Path to an R file.
#' @return The stage name as a string, or `NA_character_` if no tag.
#' @keywords internal
detect_file_stage <- function(path) {
  if (is.null(path) || !file.exists(path)) return(NA_character_)
  lines <- tryCatch(
    readLines(path, n = 10L, warn = FALSE),
    error = function(e) character()
  )
  hits <- grep("^\\s*#\\s*STAGE:\\s*\\S+", lines, value = TRUE)
  if (length(hits) == 0L) return(NA_character_)
  sub("^\\s*#\\s*STAGE:\\s*(\\S+).*", "\\1", hits[1])
}
