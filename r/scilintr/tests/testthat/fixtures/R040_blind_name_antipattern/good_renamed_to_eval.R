# ANALYSIS_OK[blind-name]: this function is named *_evaluate_against_labels
# because it intentionally joins labels for an audit (evaluation stage).
evaluate_blind_selection_against_labels <- function(selected_calls, labels) {
  merge(selected_calls, labels, by = "cell_id")
}
