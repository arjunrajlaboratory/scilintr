# EXPECTED: R027 at line 3

env_integer <- function(name, default) {
  v <- Sys.getenv(name, NA_character_)
  if (is.na(v) || is.na(suppressWarnings(as.integer(v)))) return(default)
  as.integer(v)
}

env_methods <- function(name) {
  v <- Sys.getenv(name, NA_character_)
  if (is.na(v)) stop("env var ", name, " is required")
  strsplit(v, ",", fixed = TRUE)[[1]]
}
