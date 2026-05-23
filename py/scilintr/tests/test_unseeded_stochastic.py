"""Rule: unseeded-stochastic — stochastic method invoked without a seed kwarg."""

from __future__ import annotations

RULE = "unseeded-stochastic"

BAD_KMEANS = """
from sklearn.cluster import KMeans
labels = KMeans(n_clusters=5).fit_predict(expr)
"""

BAD_TRAIN_TEST_SPLIT = """
from sklearn.model_selection import train_test_split
xtr, xte, ytr, yte = train_test_split(x, y, test_size=0.2)
"""

BAD_UMAP = """
import umap
embedding = umap.UMAP(n_neighbors=15).fit_transform(expr)
"""

GOOD = """
from sklearn.cluster import KMeans
SEED = 20260523
labels = KMeans(n_clusters=5, random_state=SEED).fit_predict(expr)
"""

WAIVED = """
from sklearn.cluster import KMeans
# ANALYSIS_OK[random-seed-only]: random_state is fixed by a module-level np.random.seed earlier
labels = KMeans(n_clusters=5).fit_predict(expr)
"""


def test_unseeded_stochastic_flags_kmeans(has_finding):
    assert has_finding(BAD_KMEANS, RULE)


def test_unseeded_stochastic_flags_train_test_split(has_finding):
    assert has_finding(BAD_TRAIN_TEST_SPLIT, RULE)


def test_unseeded_stochastic_flags_umap(has_finding):
    assert has_finding(BAD_UMAP, RULE)


def test_unseeded_stochastic_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unseeded_stochastic_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
