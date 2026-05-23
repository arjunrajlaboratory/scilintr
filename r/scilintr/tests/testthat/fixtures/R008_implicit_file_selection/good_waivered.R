# ANALYSIS_OK[file-selection]: latest_counts.tsv is a stable symlink maintained
# by the data registry; input fingerprint checked immediately below.
counts <- read.csv("data/latest_counts.tsv")
stopifnot(tools::md5sum("data/latest_counts.tsv") == EXPECTED_COUNTS_MD5)
