#' Shared trivial-literal allowlist.
#'
#' These values are too generic to count as scientifically meaningful:
#' loop sentinels, length/presence checks, polarity flags, common Inf
#' fences, NA fillers, and booleans. Multiple rules consult this set to
#' avoid over-flagging idiomatic R.
#'
#' Used by R001 (positional access -- drop = FALSE etc.) and R002 (magic
#' threshold -- `length(x) > 0L` etc.). Rule R024 (smuggled default)
#' uses an equivalent inline allowlist; consolidate if/when extending.
#'
#' @keywords internal
TRIVIAL_LITERALS <- c(
  "0", "1", "-1",
  "0L", "1L", "-1L",
  "NA", "NA_real_", "NA_integer_",
  "NA_character_", "NA_complex_",
  "TRUE", "FALSE",
  "Inf", "-Inf"
)
