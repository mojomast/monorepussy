"""Copula Risk Model — Correlated Vulnerability Aggregation with TVaR."""

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CopulaResult:
    """Result of copula-based aggregate risk analysis."""
    model_id: str
    copula_type: str  # "gaussian", "clayton", "gumbel", "independent"
    n_assets: int
    n_simulations: int
    var_level: float
    var_value: float
    tvar_value: float
    mean_loss: float
    params: dict = field(default_factory=dict)


def _inv_cdf_uniform(u: float, mean_rate: float) -> int:
    """Simple Poisson inverse CDF for claim counts."""
    # Use Knuth's algorithm for Poisson generation
    L = math.exp(-mean_rate)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def _lognormal_sample(mu: float, sigma: float) -> float:
    """Generate a lognormal random variate."""
    return math.exp(mu + sigma * _normal_sample())


def _normal_sample() -> float:
    """Generate a standard normal random variate (Box-Muller)."""
    u1 = random.random()
    u2 = random.random()
    while u1 == 0:
        u1 = random.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def gaussian_copula_sample(n: int, correlation: float = 0.3) -> list[float]:
    """Generate correlated uniform samples using Gaussian copula.

    Uses a single-factor model: X_i = rho * Z + sqrt(1-rho^2) * epsilon_i
    where Z is a common factor and epsilon_i are idiosyncratic.
    """
    from math import erf, sqrt

    z = _normal_sample()  # Common factor
    samples = []
    for _ in range(n):
        eps = _normal_sample()  # Idiosyncratic
        x = correlation * z + math.sqrt(1 - correlation ** 2) * eps
        # Transform to uniform via normal CDF
        u = 0.5 * (1 + erf(x / sqrt(2)))
        samples.append(u)

    return samples


def clayton_copula_sample(alpha: float, n: int) -> list[float]:
    """Generate correlated uniform samples using Clayton copula.

    Clayton captures lower-tail dependence (joint extreme low values).
    Uses conditional sampling method.
    """
    if alpha <= 0:
        return [random.random() for _ in range(n)]

    # Generate from Clayton copula using the conditional method
    # V ~ Gamma(1/alpha, 1), then U_i = (1 - log(E_i)/V)^(-1/alpha)
    # where E_i ~ Exp(1)
    v = _gamma_sample(1.0 / alpha)
    samples = []
    for _ in range(n):
        e = random.expovariate(1.0)
        base = 1.0 - math.log(e) / v
        # If base is negative, the power produces complex — cap to small positive
        if base <= 0:
            u = random.random() * 0.01  # Near-zero sample
        else:
            try:
                u = base ** (-1.0 / alpha)
            except (ValueError, OverflowError):
                u = 1.0
            u = max(0.0, min(1.0, u))
        samples.append(u)

    return samples


def gumbel_copula_sample(beta: float, n: int) -> list[float]:
    """Generate correlated uniform samples using Gumbel copula.

    Gumbel captures upper-tail dependence (joint extreme high values).
    Uses Marshall-Olkin method with stable distribution.
    """
    if beta <= 1.0:
        return [random.random() for _ in range(n)]

    # Marshall-Olkin method: generate stable(alpha, 1) variable
    alpha = 1.0 / beta
    v = _stable_sample(alpha)
    samples = []
    for _ in range(n):
        e = random.expovariate(1.0)
        u = max(0.0, min(1.0, math.exp(-((-math.log(e)) ** beta / v))))
        samples.append(u)

    return samples


def _gamma_sample(shape: float) -> float:
    """Generate a Gamma(shape, 1) random variate (Marsaglia-Tsang)."""
    if shape < 1.0:
        # Use Ahrens-Dieter: if X ~ Gamma(shape+1, 1), then X * U^(1/shape) ~ Gamma(shape, 1)
        return _gamma_sample(shape + 1.0) * (random.random() ** (1.0 / shape))

    d = shape - 1.0 / 3.0
    c = 1.0 / math.sqrt(9.0 * d)
    while True:
        while True:
            x = _normal_sample()
            v = 1.0 + c * x
            if v > 0:
                break
        v = v ** 3
        u = random.random()
        if u < 1.0 - 0.0331 * (x ** 2) ** 2:
            return d * v
        if math.log(u) < 0.5 * x * x + d * (1.0 - v + math.log(v)):
            return d * v


def _stable_sample(alpha: float) -> float:
    """Generate a positive stable(alpha, 1) random variate.

    Uses Chambers-Mallows-Stuck method.
    """
    if alpha >= 1.0:
        return 1.0

    # Uniform on (-pi/2, pi/2)
    u = math.pi * (random.random() - 0.5)
    # Exponential with rate 1
    w = random.expovariate(1.0)

    # CMS formula for alpha-stable with beta=1
    factor = math.sin(alpha * (u + math.pi / 2)) / (math.cos(u) ** (1.0 / alpha))
    inner = math.cos(u - alpha * (u + math.pi / 2)) / w
    result = factor * (inner ** ((1.0 - alpha) / alpha))

    return max(result, 0.001)  # Ensure positive


def simulate_aggregate_loss(
    n_assets: int,
    exploit_prob: float,
    loss_severity_mu: float = 6.0,
    loss_severity_sigma: float = 2.0,
    copula_type: str = "independent",
    copula_params: Optional[dict] = None,
    n_simulations: int = 10000,
    seed: Optional[int] = None,
) -> CopulaResult:
    """Simulate aggregate loss using copula model.

    Args:
        n_assets: Number of vulnerable assets.
        exploit_prob: Base exploit probability per asset.
        loss_severity_mu: Lognormal mu for loss severity.
        loss_severity_sigma: Lognormal sigma for loss severity.
        copula_type: "independent", "gaussian", "clayton", or "gumbel".
        copula_params: Parameters for the copula (correlation, alpha, beta).
        n_simulations: Number of Monte Carlo simulations.
        seed: Random seed for reproducibility.

    Returns:
        CopulaResult with VaR and TVaR estimates.
    """
    if seed is not None:
        random.seed(seed)

    params = copula_params or {}
    losses = []

    for _ in range(n_simulations):
        # Generate correlated uniform samples
        if copula_type == "gaussian":
            correlation = params.get("correlation", 0.3)
            u_samples = gaussian_copula_sample(n_assets, correlation)
        elif copula_type == "clayton":
            alpha = params.get("alpha", 2.0)
            u_samples = clayton_copula_sample(alpha, n_assets)
        elif copula_type == "gumbel":
            beta = params.get("beta", 2.0)
            u_samples = gumbel_copula_sample(beta, n_assets)
        else:  # independent
            u_samples = [random.random() for _ in range(n_assets)]

        # Compute aggregate loss
        total_loss = 0.0
        for u in u_samples:
            # If the correlated uniform falls below exploit probability,
            # the asset is exploited
            if u < exploit_prob:
                severity = _lognormal_sample(loss_severity_mu, loss_severity_sigma)
                total_loss += severity

        losses.append(total_loss)

    # Sort for VaR and TVaR computation
    losses.sort()

    n = len(losses)
    mean_loss = sum(losses) / n

    # VaR at specified level
    var_level = params.get("var_level", 0.99)
    var_idx = int(var_level * n) - 1
    var_idx = max(0, min(n - 1, var_idx))
    var_value = losses[var_idx]

    # TVaR = E[S | S > VaR]
    tail_losses = losses[var_idx:]
    tvar_value = sum(tail_losses) / len(tail_losses) if tail_losses else var_value

    return CopulaResult(
        model_id=f"{copula_type}_{n_assets}assets",
        copula_type=copula_type,
        n_assets=n_assets,
        n_simulations=n_simulations,
        var_level=var_level,
        var_value=var_value,
        tvar_value=tvar_value,
        mean_loss=mean_loss,
        params=params,
    )


def compute_var_tvar(
    losses: list[float],
    var_level: float = 0.99,
) -> tuple[float, float]:
    """Compute VaR and TVaR from a list of loss values.

    Args:
        losses: List of simulated aggregate losses.
        var_level: Confidence level (e.g., 0.99 for 99th percentile).

    Returns:
        Tuple of (VaR, TVaR).
    """
    if not losses:
        return 0.0, 0.0

    sorted_losses = sorted(losses)
    n = len(sorted_losses)
    var_idx = int(var_level * n) - 1
    var_idx = max(0, min(n - 1, var_idx))
    var_value = sorted_losses[var_idx]

    tail = sorted_losses[var_idx:]
    tvar = sum(tail) / len(tail) if tail else var_value

    return var_value, tvar


def format_copula_result(result: CopulaResult) -> str:
    """Format copula simulation result as a readable string."""
    lines = [
        f"Correlated Risk Aggregation: {result.model_id}",
        f"  Copula type:    {result.copula_type}",
        f"  Assets:         {result.n_assets}",
        f"  Simulations:    {result.n_simulations}",
        f"  Mean loss:      {result.mean_loss:,.2f}",
        f"  VaR ({result.var_level:.0%}):     {result.var_value:,.2f}",
        f"  TVaR ({result.var_level:.0%}):    {result.tvar_value:,.2f}",
        f"  TVaR/VaR ratio: {result.tvar_value / result.var_value:.2f}" if result.var_value > 0 else "  TVaR/VaR ratio: N/A",
    ]

    if result.params:
        lines.append(f"  Parameters:     {result.params}")

    return "\n".join(lines)
