# Fixture-driven test driver. Walks every directory under
# tests/testthat/fixtures/, parses EXPECTED headers from bad files,
# and asserts:
#
#   - Each bad file produces every expected finding (rule + line).
#   - Each good file produces no findings of the directory's rule.
#
# Cross-file rules use subdirectory fixtures (bad_*/ and good_*/ each
# containing multiple .R files); per-file rules use flat fixtures
# (bad_*.R and good_*.R directly inside the rule directory).
#
# Until a rule is implemented in R/per_file_linters.R or
# R/cross_file_rules.R, lint_file() / lint_project() return no
# findings. Good cases pass trivially; bad cases fail. That's the
# TDD starting state.

dirs <- fixture_dirs()

for (rule_dir in dirs) {
  rule <- fixture_rule(rule_dir)
  slug <- basename(rule_dir)

  if (rule %in% CROSS_FILE_RULES) {
    # Subdirectory shape.
    for (bad_dir in bad_fixture_dirs(rule_dir)) {
      test_that(sprintf("[%s] %s fires expected findings", slug, basename(bad_dir)), {
        findings <- fixture_findings(bad_dir, rule)
        relevant <- findings_for_rule(findings, rule)
        relevant_lines <- vapply(relevant, function(f) f$line, integer(1),
                                 USE.NAMES = FALSE)

        # Collect expectations across every .R file in the bad_*/ dir.
        bad_files <- list.files(bad_dir, pattern = "\\.R$", full.names = TRUE)
        expected <- do.call(rbind, lapply(bad_files, parse_expected))

        for (i in seq_len(nrow(expected))) {
          expect_true(
            expected$line[i] %in% relevant_lines,
            info = sprintf("expected %s at line %d in %s; got lines %s",
                           expected$rule[i], expected$line[i],
                           basename(bad_dir),
                           paste(relevant_lines, collapse = ","))
          )
        }
      })
    }

    for (good_dir in good_fixture_dirs(rule_dir)) {
      test_that(sprintf("[%s] %s does not fire %s", slug, basename(good_dir), rule), {
        findings <- fixture_findings(good_dir, rule)
        relevant <- findings_for_rule(findings, rule)
        expect_length(relevant, 0)
      })
    }
  } else {
    # Flat shape.
    for (bad in bad_fixtures_flat(rule_dir)) {
      expected <- parse_expected(bad)
      if (nrow(expected) == 0L) next

      test_that(sprintf("[%s] %s fires expected findings", slug, basename(bad)), {
        findings <- fixture_findings(bad, rule)
        relevant <- findings_for_rule(findings, rule)
        relevant_lines <- vapply(relevant, function(f) f$line, integer(1),
                                 USE.NAMES = FALSE)

        for (i in seq_len(nrow(expected))) {
          expect_true(
            expected$line[i] %in% relevant_lines,
            info = sprintf("expected %s at line %d in %s; got lines %s",
                           expected$rule[i], expected$line[i],
                           basename(bad),
                           paste(relevant_lines, collapse = ","))
          )
        }
      })
    }

    for (good in good_fixtures_flat(rule_dir)) {
      test_that(sprintf("[%s] %s does not fire %s", slug, basename(good), rule), {
        findings <- fixture_findings(good, rule)
        relevant <- findings_for_rule(findings, rule)
        expect_length(relevant, 0)
      })
    }
  }
}
