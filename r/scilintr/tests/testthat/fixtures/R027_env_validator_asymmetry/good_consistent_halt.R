env_integer <- function(name) {
  v <- Sys.getenv(name, NA_character_)
  if (is.na(v) || is.na(suppressWarnings(as.integer(v))))
    stop("env var ", name, " is required and must be an integer")
  as.integer(v)
}

env_methods <- function(name) {
  v <- Sys.getenv(name, NA_character_)
  if (is.na(v)) stop("env var ", name, " is required")
  strsplit(v, ",", fixed = TRUE)[[1]]
}
