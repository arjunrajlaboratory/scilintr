# ANALYSIS_OK[contrast-definition]: design formula and contrast match the
# pre-declared model in METHODS.md §4.2; reviewed by collaborator on
# 2026-05-01.
library(DESeq2)
dds <- DESeqDataSet(se, design = ~ treatment + batch)
results(dds, contrast = c("treatment", "treated", "control"))
