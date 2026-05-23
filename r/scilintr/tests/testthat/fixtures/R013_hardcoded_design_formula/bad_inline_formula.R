# EXPECTED: R013 at line 4

library(DESeq2)
dds <- DESeqDataSet(se, design = ~ treatment + batch)
results(dds, contrast = c("treatment", "treated", "control"))
