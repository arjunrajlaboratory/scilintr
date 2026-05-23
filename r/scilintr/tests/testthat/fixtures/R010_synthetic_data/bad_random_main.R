# EXPECTED: R010 at line 4

# silently substitute random data — this is main analysis code, not a test
counts <- matrix(rpois(20000 * 48, 10), nrow = 20000)
metadata <- data.frame(sample_id = paste0("S", 1:48),
                       condition = sample(c("ctrl", "trt"), 48, TRUE))
