# ANALYSIS_OK[constant-gates-at-depth]: gates intentionally inherited; per-node
# gate tuning would be label-leaky. Stopping rule (assigned fraction +
# post-selection enrichment vs label-shuffle null) applied independently per node.
recurse_module <- function(node, gates) {
  best <- select_module(node, gates)
  if (terminal(node)) return(best)
  for (child in children(node, best)) {
    recurse_module(child, gates)
  }
}
