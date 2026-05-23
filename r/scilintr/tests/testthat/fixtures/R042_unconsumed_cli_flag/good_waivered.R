opt_list <- list(
  optparse::make_option("--top-modules", default = 25L),
  # ANALYSIS_OK[deprecated-flag]: --band-lo kept for backwards compat with
  # old wrapper scripts; value is ignored and BAND comes from the config.
  optparse::make_option("--band-lo",     default = 0.22)
)
opt <- optparse::parse_args(optparse::OptionParser(option_list = opt_list))

cat("top:", opt$top_modules, "\n")
