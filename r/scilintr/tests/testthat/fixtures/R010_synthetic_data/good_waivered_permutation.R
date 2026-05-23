# ANALYSIS_OK[permutation-test]: shuffles existing labels for a null
# distribution; sample(truth) is the intended diagnostic, not synthetic
# data generation.
null <- replicate(1000L, adjusted_rand_index(pred, sample(truth)))
