from apps.arf_sentinel.evidence import compute_blast_radius

def test_blast_radius_range():
    score = compute_blast_radius(147, 58, 23)
    assert 0.0 <= score <= 1.0

def test_blast_radius_monotonic():
    score_small = compute_blast_radius(50, 20, 10)
    score_large = compute_blast_radius(200, 100, 50)
    assert score_large >= score_small
