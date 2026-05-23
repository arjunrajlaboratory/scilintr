unsupervised_select_module <- function(modules) {
  scored <- score_unsupervised(modules)
  modules[which.max(scored), ]
}
