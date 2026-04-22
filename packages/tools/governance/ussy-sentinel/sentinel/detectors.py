"""Detector generation using negative selection algorithm.

Generates random pattern vectors (candidate detectors), then filters out
any that match the 'self' corpus (autoreactive detectors). Only detectors
that do NOT match self survive — they detect 'non-self' (anomalous patterns).
"""

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .distance import euclidean_distance, min_distance_to_corpus
from .extractor import FeatureVector


@dataclass
class Detector:
    """A mature detector that recognizes non-self patterns."""
    id: str
    vector: List[float]
    threshold: float = 1.0
    generation: int = 0
    activation_count: int = 0
    false_positive_count: int = 0
    true_positive_count: int = 0
    created_at: str = ""
    description: str = ""

    def matches(self, pattern: List[float], metric: str = "euclidean") -> bool:
        """Check if this detector matches a pattern (within threshold)."""
        if metric == "euclidean":
            dist = euclidean_distance(self.vector, pattern)
        else:
            from .distance import _get_distance_fn
            dist = _get_distance_fn(metric)(self.vector, pattern)
        return dist <= self.threshold

    def distance_to(self, pattern: List[float], metric: str = "euclidean") -> float:
        """Compute distance from this detector to a pattern."""
        if metric == "euclidean":
            return euclidean_distance(self.vector, pattern)
        from .distance import _get_distance_fn
        return _get_distance_fn(metric)(self.vector, pattern)

    @property
    def false_positive_rate(self) -> float:
        """Compute false positive rate."""
        if self.activation_count == 0:
            return 0.0
        return self.false_positive_count / self.activation_count

    @property
    def true_positive_rate(self) -> float:
        """Compute true positive rate."""
        if self.activation_count == 0:
            return 0.0
        return self.true_positive_count / self.activation_count

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "vector": self.vector,
            "threshold": self.threshold,
            "generation": self.generation,
            "activation_count": self.activation_count,
            "false_positive_count": self.false_positive_count,
            "true_positive_count": self.true_positive_count,
            "created_at": self.created_at,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Detector":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            vector=data["vector"],
            threshold=data.get("threshold", 0.3),
            generation=data.get("generation", 0),
            activation_count=data.get("activation_count", 0),
            false_positive_count=data.get("false_positive_count", 0),
            true_positive_count=data.get("true_positive_count", 0),
            created_at=data.get("created_at", ""),
            description=data.get("description", ""),
        )


@dataclass
class DetectorPopulation:
    """A population of mature detectors."""
    detectors: List[Detector] = field(default_factory=list)
    metric: str = "euclidean"
    matching_threshold: float = 0.3
    generation: int = 0
    created_at: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "metric": self.metric,
            "matching_threshold": self.matching_threshold,
            "generation": self.generation,
            "created_at": self.created_at,
            "detectors": [d.to_dict() for d in self.detectors],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DetectorPopulation":
        """Deserialize from dictionary."""
        pop = cls(
            metric=data.get("metric", "euclidean"),
            matching_threshold=data.get("matching_threshold", 0.3),
            generation=data.get("generation", 0),
            created_at=data.get("created_at", ""),
        )
        for ddata in data.get("detectors", []):
            pop.detectors.append(Detector.from_dict(ddata))
        return pop


def generate_random_vector(num_dims: int, rng: random.Random) -> List[float]:
    """Generate a random feature vector with values in [0, 1]."""
    return [rng.random() for _ in range(num_dims)]


def generate_detectors(
    self_vectors: List[List[float]],
    num_detectors: int = 5000,
    matching_threshold: float = 0.3,
    metric: str = "euclidean",
    coverage: float = 0.95,
    seed: Optional[int] = None,
    max_candidates: int = 50000,
) -> DetectorPopulation:
    """Generate a detector population using negative selection.

    Args:
        self_vectors: The self corpus (list of feature vectors)
        num_detectors: Target number of mature detectors
        matching_threshold: Distance threshold for matching self
        metric: Distance metric to use
        coverage: Target coverage of non-self space
        seed: Random seed for reproducibility
        max_candidates: Maximum number of candidates to try

    Returns:
        DetectorPopulation with mature detectors
    """
    from datetime import datetime

    rng = random.Random(seed)

    if not self_vectors:
        # No self corpus — generate detectors freely
        num_dims = len(FeatureVector.feature_names())
        detectors = []
        for i in range(num_detectors):
            vec = generate_random_vector(num_dims, rng)
            det_id = f"D-{i:04d}"
            detector = Detector(
                id=det_id,
                vector=vec,
                threshold=1.5,  # Default detection threshold in 25D
                created_at=datetime.now().isoformat(),
            )
            detectors.append(detector)
        return DetectorPopulation(
            detectors=detectors,
            metric=metric,
            matching_threshold=matching_threshold,
            created_at=datetime.now().isoformat(),
        )

    num_dims = len(self_vectors[0])
    detectors = []
    candidates_tried = 0

    while len(detectors) < num_detectors and candidates_tried < max_candidates:
        # Generate candidate
        candidate = generate_random_vector(num_dims, rng)
        candidates_tried += 1

        # Check against self corpus (negative selection)
        min_dist = min_distance_to_corpus(candidate, self_vectors, metric)

        if min_dist > matching_threshold:
            # This detector does NOT match self → keep it (mature detector)
            # Detection threshold is wider than negative selection threshold
            # so the detector can "see" patterns in its neighborhood
            detection_threshold = min_dist * 0.7  # 70% of distance to nearest self
            det_id = f"D-{len(detectors):04d}"
            detector = Detector(
                id=det_id,
                vector=candidate,
                threshold=detection_threshold,
                created_at=datetime.now().isoformat(),
            )
            detectors.append(detector)

    population = DetectorPopulation(
        detectors=detectors,
        metric=metric,
        matching_threshold=matching_threshold,
        generation=0,
        created_at=datetime.now().isoformat(),
    )

    return population


def apply_feedback(detector_id: str, population: DetectorPopulation,
                   is_true_positive: bool) -> Optional[Detector]:
    """Apply feedback to a detector (affinity maturation).

    True positive: lower threshold (make more sensitive)
    False positive: raise threshold (make less sensitive)
    """
    for detector in population.detectors:
        if detector.id == detector_id:
            detector.activation_count += 1
            if is_true_positive:
                detector.true_positive_count += 1
                # Lower threshold slightly (more sensitive)
                detector.threshold = max(0.5, detector.threshold * 0.9)
            else:
                detector.false_positive_count += 1
                # Raise threshold slightly (less sensitive)
                detector.threshold = min(3.0, detector.threshold * 1.15)
            return detector
    return None


def generate_similar_detectors(
    detector: Detector,
    self_vectors: List[List[float]],
    count: int = 3,
    perturbation: float = 0.1,
    seed: Optional[int] = None,
) -> List[Detector]:
    """Generate detectors similar to an effective detector (clonal expansion).

    Used when a detector gets a true positive confirmation — generate
    similar detectors to improve coverage of that region of pattern space.
    """
    from datetime import datetime

    rng = random.Random(seed)
    new_detectors = []

    for i in range(count):
        # Perturb the original detector's vector
        new_vec = []
        for v in detector.vector:
            delta = (rng.random() * 2 - 1) * perturbation
            new_val = max(0.0, min(1.0, v + delta))
            new_vec.append(new_val)

        # Negative selection check
        min_dist = min_distance_to_corpus(new_vec, self_vectors, "euclidean")
        if min_dist > detector.threshold:
            det_id = f"D-{hashlib.md5(str(new_vec).encode()).hexdigest()[:8]}"
            new_det = Detector(
                id=det_id,
                vector=new_vec,
                threshold=detector.threshold,
                generation=detector.generation + 1,
                created_at=datetime.now().isoformat(),
                description=f"Clonal expansion of {detector.id}",
            )
            new_detectors.append(new_det)

    return new_detectors
