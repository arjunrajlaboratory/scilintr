# EXPECTED: R030 at line 11

# DESeq2 size-factor estimation occasionally fails on all-zero rows.
# The warning makes the failure *look* handled, but the block still
# returns a bare NA that downstream code treats as a real estimate --
# a multi-statement handler swallowing the error all the same.
sf <- tryCatch(
  estimateSizeFactors(dds),
  error = function(e) {
    warning("size-factor estimation failed: ", conditionMessage(e))
    NA_real_
  }
)
