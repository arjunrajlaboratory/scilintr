p <- tryCatch(
  wilcox.test(a, b)$p.value,
  error = function(e) {
    warning("wilcox.test failed for ", id, ": ", conditionMessage(e))
    structure(NA_real_, error = conditionMessage(e), id = id)
  }
)
