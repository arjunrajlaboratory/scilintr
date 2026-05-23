# 0L is a length/presence sentinel, not a scientific threshold.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) > 0L) {
  message("got args")
}
