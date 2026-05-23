# per-node gate selection — uses OOB stability inside the parent's blind output
recurse_module <- function(node, parent_gates) {
  best <- select_module(node, parent_gates)
  if (terminal(node)) return(best)
  child_gates <- choose_gates_from_oob(node, best)
  for (child in children(node, best)) {
    recurse_module(child, child_gates)
  }
}
