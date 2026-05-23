# Mixed-style access: $-access AND [[ ]]-access both count as "read".
opt_list <- list(
  optparse::make_option("--top-modules", default = 25L),
  optparse::make_option("--band-lo",     default = 0.22)
)
opt <- optparse::parse_args(optparse::OptionParser(option_list = opt_list))

n <- opt[["top_modules"]]
lo <- opt$band_lo
cat(n, lo, "\n")
