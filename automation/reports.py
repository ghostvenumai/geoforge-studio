"""Human-readable master-loop reports and terminal summaries."""

from __future__ import annotations

from pathlib import Path

from automation.state import LoopState, LoopStatus, Phase


def phase_status(state: LoopState, phase: Phase) -> str:
    if phase.value in state.completed_phases:
        return "PASS"
    if phase.value in state.blocked_phases:
        return "BLOCKED_EXTERNAL"
    if phase.value in state.failed_phases:
        return "FAIL"
    return "NOT_RUN"


def write_build_report(state: LoopState, path: Path) -> None:
    rows = "\n".join(
        f"| {phase.value} | {phase_status(state, phase)} |"
        for phase in Phase
        if phase != Phase.COMPLETE
    )
    blockers = "\n".join(f"- {blocker}" for blocker in state.blockers) or "- None"
    final_video = path.parent / "solcom_demo.mp4"
    preview_video = path.parent / "solcom_demo_preview.mp4"
    output = final_video if final_video.is_file() else preview_video
    output_text = str(output) if output.is_file() else "not generated"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# GeoForge Studio - Master Loop Build Report",
                "",
                f"Build ID: `{state.build_id}`",
                f"Status: **{state.status.value}**",
                f"Updated: {state.updated_at}",
                f"Global iterations: {state.global_iterations}/{state.max_global_iterations}",
                "",
                "| Phase | Status |",
                "|---|---|",
                rows,
                "",
                "## Output",
                "",
                f"`{output_text}`",
                "",
                "## External blockers",
                "",
                blockers,
                "",
                "## Resume",
                "",
                "Configure only the documented missing external requirement and run "
                "`./run_loop.sh --resume`.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def terminal_summary(state: LoopState) -> str:
    key_phases = (
        ("APPLICATION", Phase.APPLICATION_QA),
        ("UNIT TESTS", Phase.UNIT_TEST),
        ("INTEGRATION TESTS", Phase.INTEGRATION_TEST),
        ("SECURITY CHECK", Phase.SECURITY_CHECK),
        ("DEMO", Phase.DEMO_RUN),
        ("RECORDING", Phase.RECORD),
        ("NARRATION", Phase.GENERATE_NARRATION),
        ("VOICEOVER", Phase.GENERATE_VOICE),
        ("SUBTITLES", Phase.GENERATE_SUBTITLES),
        ("RENDER", Phase.RENDER),
        ("VIDEO QA", Phase.VIDEO_QA),
    )
    lines = ["=" * 56, "GEOFORGE STUDIO - AUTONOMOUS BUILD REPORT", "=" * 56, ""]
    lines.extend(f"{label + ':':<22} {phase_status(state, phase)}" for label, phase in key_phases)
    lines.extend(["", f"FINAL STATUS:          {state.status.value}"])
    if state.status == LoopStatus.COMPLETE:
        lines.extend(["", "VIDEO:", "dist/solcom_demo.mp4"])
    elif state.blockers:
        lines.extend(["", "BLOCKER:", *state.blockers])
    lines.extend(["", "REPORT:", "dist/build_report.md", "=" * 56])
    return "\n".join(lines)
