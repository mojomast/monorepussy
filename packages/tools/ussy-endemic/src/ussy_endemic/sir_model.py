"""SIR Model — discrete-time SIR simulation for code pattern spread."""

from __future__ import annotations

from typing import Optional

from ussy_endemic.models import SIRSimulation, SIRState


def compute_beta(r0: float, gamma: float, n: int) -> float:
    """Compute transmission rate β from R0 and γ.

    In the SIR model: R0 = β / γ, so β = R0 × γ.
    """
    return r0 * gamma


def compute_gamma(recovery_time_weeks: float = 4.0, time_step_weeks: float = 1.0) -> float:
    """Compute recovery rate γ.

    γ = time_step / recovery_time
    """
    if recovery_time_weeks <= 0:
        return 1.0
    return time_step_weeks / recovery_time_weeks


def simulate_sir(
    n: int,
    initial_infected: int,
    initial_recovered: int = 0,
    r0: float = 1.0,
    gamma: float = 0.1,
    horizon_steps: int = 26,
    time_step_label: str = "week",
) -> SIRSimulation:
    """Run a discrete-time SIR simulation.

    Args:
        n: Total population (modules).
        initial_infected: Number initially infected.
        initial_recovered: Number initially recovered (immune).
        r0: Basic reproduction number.
        gamma: Recovery rate per time step.
        horizon_steps: Number of time steps to simulate.
        time_step_label: Label for time steps (for display).

    Returns:
        SIRSimulation with full time series.
    """
    beta = compute_beta(r0, gamma, n)

    s = n - initial_infected - initial_recovered
    i = initial_infected
    r = initial_recovered

    states = [SIRState(time=0, s=s, i=i, r=r)]
    peak_infected = i
    peak_time = 0.0

    for step in range(1, horizon_steps + 1):
        # SIR update equations
        new_infections = beta * s * i / n if n > 0 else 0
        new_recoveries = gamma * i

        # Ensure we don't over-flow compartments
        new_infections = min(new_infections, s)
        new_recoveries = min(new_recoveries, i)

        s = s - new_infections
        i = i + new_infections - new_recoveries
        r = r + new_recoveries

        # Round to integers for discrete population
        s = max(0, round(s))
        i = max(0, round(i))
        r = max(0, round(r))

        # Ensure total is conserved
        total = s + i + r
        if total != n:
            diff = n - total
            s += diff  # Adjust susceptible

        state = SIRState(time=step, s=s, i=i, r=r)
        states.append(state)

        if i > peak_infected:
            peak_infected = i
            peak_time = step

    return SIRSimulation(
        pattern_name="",
        r0=r0,
        beta=beta,
        gamma=gamma,
        n=n,
        states=states,
        peak_infected=peak_infected,
        peak_time=peak_time,
        final_infected=states[-1].i if states else 0,
    )


def simulate_with_intervention(
    n: int,
    initial_infected: int,
    initial_recovered: int,
    r0: float,
    gamma: float,
    intervention_step: int,
    intervention_r0: float,
    horizon_steps: int = 26,
) -> tuple[SIRSimulation, SIRSimulation]:
    """Simulate SIR with and without intervention.

    Returns (without_intervention, with_intervention) simulations.
    """
    without = simulate_sir(
        n=n,
        initial_infected=initial_infected,
        initial_recovered=initial_recovered,
        r0=r0,
        gamma=gamma,
        horizon_steps=horizon_steps,
    )

    # Simulate with intervention: first run until intervention step
    pre_intervention = simulate_sir(
        n=n,
        initial_infected=initial_infected,
        initial_recovered=initial_recovered,
        r0=r0,
        gamma=gamma,
        horizon_steps=intervention_step,
    )

    # Then continue with reduced R0
    if pre_intervention.states:
        last_state = pre_intervention.states[-1]
        post_intervention = simulate_sir(
            n=n,
            initial_infected=last_state.i,
            initial_recovered=last_state.r,
            r0=intervention_r0,
            gamma=gamma,
            horizon_steps=horizon_steps - intervention_step,
        )

        # Combine states
        combined_states = list(pre_intervention.states)
        for state in post_intervention.states[1:]:  # Skip first (duplicate)
            combined_states.append(SIRState(
                time=state.time + intervention_step,
                s=state.s,
                i=state.i,
                r=state.r,
            ))

        with_intervention = SIRSimulation(
            pattern_name="",
            r0=intervention_r0,
            beta=compute_beta(intervention_r0, gamma, n),
            gamma=gamma,
            n=n,
            states=combined_states,
        )
    else:
        with_intervention = without

    return without, with_intervention


def format_sir_chart(sim: SIRSimulation, width: int = 60, height: int = 10,
                     time_labels: Optional[list[str]] = None) -> str:
    """Format an ASCII chart of SIR simulation results.

    Returns a string with the chart.
    """
    if not sim.states:
        return "No simulation data."

    lines = []
    n = sim.n
    if n == 0:
        return "Population is zero."

    for row_idx in range(height):
        y_val = n * (height - row_idx) / height
        row_str = f"{int(y_val):>4} ┤"

        for state in sim.states:
            # Determine dominant compartment at this height
            i_frac = state.i / n if n > 0 else 0
            s_frac = state.s / n if n > 0 else 0
            r_frac = state.r / n if n > 0 else 0

            threshold = y_val / n if n > 0 else 0

            if threshold <= r_frac:
                row_str += "R"
            elif threshold <= r_frac + i_frac:
                row_str += "I"
            else:
                row_str += "S"

        lines.append(row_str)

    # X-axis
    x_axis = "     └" + "─" * len(sim.states)
    lines.append(x_axis)

    # Time labels
    if time_labels:
        label_line = "      "
        step = max(1, len(sim.states) // len(time_labels))
        for i, label in enumerate(time_labels):
            pos = i * step
            if pos < len(sim.states):
                label_line += label.ljust(step)
        lines.append(label_line)

    # Legend
    lines.append(f"  S=Susceptible  I=Infected  R=Recovered  (N={n})")

    return "\n".join(lines)
