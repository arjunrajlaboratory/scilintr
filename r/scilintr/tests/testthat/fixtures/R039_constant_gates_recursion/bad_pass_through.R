# EXPECTED: R039 at line 8

# recursive call inherits parent-tuned gates at every depth
recurse_module <- function(node, gates) {
  best <- select_module(node, gates)
  if (terminal(node)) return(best)
  for (child in children(node, best)) {
    recurse_module(child, gates)
  }
}
