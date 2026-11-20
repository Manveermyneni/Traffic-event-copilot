"""
Police Copilot Chatbot Engine.
Provides grounded, accurate tactical explanations of generated event traffic plans.
Answers police queries regarding bottlenecks, diversions, emergency corridors, and deployment.
"""
from __future__ import annotations

import os
import re
from typing import Any
import pandas as pd


def generate_police_response(query: str, res: dict[str, Any] | None) -> str:
    """
    Generate a factual, grounded response to a police officer's question based on the active traffic scenario.
    Labels all planning parameters and deployment heuristics as ASSUMED.
    """
    if not res:
        return (
            "No active scenario found. Please run a traffic scenario first by selecting an event or "
            "entering event parameters in the sidebar and clicking '▶ Run Co-Pilot'."
        )

    q = str(query).strip().lower()
    params = res.get("params", {})
    demand = res.get("demand", {})
    hotspots = res.get("hotspots", pd.DataFrame())
    diversions = res.get("diversions", [])
    corridor = res.get("corridor")
    approaches = res.get("approaches", {})
    so = res.get("sum_opt", {})
    sn = res.get("sum_naive", {})

    event_name = params.get("event_name", "Event")
    attendance = params.get("attendance", 0)
    phase = params.get("phase", "ingress")
    start_time = params.get("start_time", "19:30")

    # 1. Bottlenecks / Hotspots / Congestion
    if any(w in q for w in ["hotspot", "bottleneck", "congest", "traffic jam", "red road", "v/c", "over capacity", "worst", "h-"]):
        lines = [f"### 🚨 Congestion Hotspots for {event_name}"]
        lines.append(
            f"Under the spread-out assignment model, **{so.get('congested', 0)} road segment(s)** operate over capacity (V/C > 1.0), "
            f"and **{so.get('near', 0)} segment(s)** are near capacity (V/C 0.8–1.0). Peak V/C reaches **{so.get('max_vc', 0):.2f}**."
        )
        if not hotspots.empty:
            lines.append("\n**Top Critical Bottlenecks:**")
            for idx, r in hotspots.head(5).iterrows():
                tag = f"[H-{idx+1}]"
                st_name = r.get("street", "Unnamed road")
                vc = r.get("vc", 0.0)
                load = r.get("load_pcu_hr", 0.0)
                cap = r.get("capacity_pcu_hr", 0.0)
                fed = r.get("fed_by", "all approaches")
                lines.append(f"- **{tag} {st_name}**: V/C **{vc:.2f}** ({load:,.0f} PCU/h vs {cap:,.0f} capacity). Fed by traffic from: *{fed}*.")
            lines.append(
                "\n*Tactical Recommendation:* Deploy traffic marshals at these bottleneck intersections 90 minutes before "
                "event start (*ASSUMED peak ingress window*). Prevent curb parking and lane-blocking drop-offs."
            )
        return "\n".join(lines)

    # 2. Emergency / Ambulance / Green Corridor (Prioritized before general diversions)
    if any(w in q for w in ["emergency", "ambulance", "corridor", "hospital", "green channel", "green corridor", "e-", "trauma"]):
        if not corridor:
            return "No emergency corridor path could be computed between the venue and destination hospital on this network."
        hosp_note = (
            "Hospital location is currently a placeholder (ASSUMED)"
            if res.get("hospital_is_placeholder", True)
            else "Hospital location verified from manual/catalog records"
        )
        lines = [
            f"### 🚑 Protected Emergency Green Corridor (`[E-1]`)",
            f"- **Designated Route Length:** {corridor.get('length_m', 0):,} metres.",
            f"- **Free-flow ETA (Protected):** **{corridor.get('free_min', 0)} minutes** when kept strictly clear of event traffic.",
            f"- **Unprotected ETA (Event Congestion):** **{corridor.get('unprotected_min', 0)} minutes** if general spectator traffic mixes in.",
            f"- **Time Saved by Green Corridor Enforcement:** **{max(0, corridor.get('unprotected_min', 0) - corridor.get('free_min', 0)):.1f} minutes**.",
            f"- **Status:** {hosp_note}.",
            "\n*SOP for Police:* Station one stationary interceptor bike at each intersection along this corridor. "
            "Under no circumstances should spectator parking or spectator queuing encroach onto this designated lane."
        ]
        return "\n".join(lines)

    # 3. Diversions / Closures / Turn-backs / Barricades
    if any(w in q for w in ["diversion", "divert", "turnback", "turn-back", "barricade", "closure", "detour", "alternate route", "d-"]):
        lines = [f"### 🔀 Tactical Diversion Scheme for {event_name}"]
        if diversions:
            lines.append("Here are the recommended route diversions calculated to relieve key bottlenecks:\n")
            for idx, d in enumerate(diversions[:6]):
                tag = f"[D-{idx+1}]"
                name = d.get("name", "Hotspot")
                vc = d.get("vc", 0.0)
                if d.get("feasible"):
                    extra_m = d.get("extra_m", 0)
                    extra_s = d.get("extra_s", 0)
                    lines.append(
                        f"- **{tag} {name} (V/C {vc:.2f})**: Alternate detour feasible. "
                        f"Adds **+{extra_m:,} m** and **+{extra_s} seconds** detour penalty. Divert general private traffic here."
                    )
                else:
                    note = d.get("note", "No alternate bypass")
                    lines.append(
                        f"- **{tag} {name} (V/C {vc:.2f})**: **No safe alternate diversion available** ({note}). "
                        f"Implement strict turn-back enforcement or hold-and-release staging."
                    )
        adv = res.get("advisory")
        if adv is not None and not adv.empty:
            lines.append("\n**Published Police Advisory Diversions:**")
            for _, a in adv.drop_duplicates(["Movement", "Diversion_Point"]).head(4).iterrows():
                lines.append(f"- *{a.get('Movement')}*: Divert at **{a.get('Diversion_Point')}** via **{a.get('Diverted_Route')}**.")
        lines.append("\n*Barricade Guidance:* Place physical barricades with LED directional arrow boards at each diversion point.")
        return "\n".join(lines)

    # 4. Deployment / Police Personnel / Manpower
    if any(w in q for w in ["personnel", "officer", "manpower", "deployment", "duty", "staff", "police"]):
        tot_veh = demand.get("total_vehicles", 0)
        num_hotspots = len(hotspots)
        # ASSUMED planning ratio for traffic police staffing
        traffic_si = max(2, round(num_hotspots * 0.8))                # ASSUMED SI per major sector
        traffic_constables = max(10, round(tot_veh / 800) + num_hotspots * 4)  # ASSUMED constable ratio
        marshals = max(6, round(demand.get("pedestrians", 0) / 2500)) # ASSUMED crowd control ratio

        lines = [
            f"### 👮 Tactical Police Deployment Estimate (ASSUMED Heuristic)",
            f"For an expected attendance of **{attendance:,}** ({tot_veh:,} vehicles, peak {demand.get('peak_hourly_pcu', 0):,.0f} PCU/h):",
            f"- **Sector Officers (Sub-Inspectors/Inspectors):** ~{traffic_si} officers (assigned to major corridor sectors).",
            f"- **Traffic Constables & Home Guards:** ~{traffic_constables} personnel for intersection duty, diversion barricades, and U-turn closures.",
            f"- **Crowd & Pedestrian Marshals:** ~{marshals} personnel stationed at metro exits, bus drop-offs, and venue approach gates.",
            "\n*Key Duty Posts:*",
            "- Checkpoint [J-1] to [J-4] entry approaches: 2 constables each.",
            "- Diversion points [D-1] to [D-3]: 2 constables + 1 patrol bike each.",
            "- Emergency corridor [E-1]: Dedicated roving motorcycle escort."
        ]
        return "\n".join(lines)

    # 5. Parking / Transit / Metro / Buses
    if any(w in q for w in ["park", "bus", "metro", "transit", "walk", "crowd", "p-", "drop"]):
        p_note = (
            "Parking locations are algorithmically generated near the venue (ASSUMED)"
            if res.get("parking_is_generated", True)
            else "Parking zones verified from records"
        )
        lines = [
            f"### 🅿️ Parking & Transit Management for {event_name}",
            f"- **Mode Share (ASSUMED):** Private vehicles {demand.get('mode_share', {}).get('car', 0.25)*100:.0f}% cars, "
            f"{demand.get('mode_share', {}).get('two_wheeler', 0.25)*100:.0f}% 2-wheelers.",
            f"- **Vehicle Volume:** {demand.get('vehicles', {}).get('car', 0):,} cars, {demand.get('vehicles', {}).get('two_wheeler', 0):,} two-wheelers, "
            f"{demand.get('vehicles', {}).get('bus', 0):,} buses.",
            f"- **Off-road transit:** **{demand.get('metro_riders', 0):,.0f}** metro riders, **{demand.get('pedestrians', 0):,.0f}** pedestrians.",
            f"- **Parking Status:** {p_note}.",
            "\n*Police Directive:* Direct private vehicles to designated peripheral parking clusters `[P-1]` through `[P-4]` early. "
            "Coordinate with HMRL for high-frequency metro feeder trains (5-minute headway) during the peak arrival window."
        ]
        return "\n".join(lines)

    # 6. Default / General Plan Summary
    lines = [
        f"### 📋 Traffic Copilot Plan Overview: {event_name}",
        f"- **Event Window & Crowd:** Start time {start_time}, {attendance:,} attendance ({phase.title()} phase).",
        f"- **Peak Flow:** **{demand.get('total_vehicles', 0):,} vehicles** generating **{demand.get('peak_hourly_pcu', 0):,.0f} PCU/h** at peak.",
        f"- **Network Impact:** Peak V/C is **{so.get('max_vc', 0):.2f}** with **{so.get('congested', 0)} road(s) over capacity**.",
        f"- **Action Summary:**",
        f"  1. Monitor top bottlenecks `[H-1]` to `[H-4]`.",
        f"  2. Enforce diversions `[D-1]` and `[D-2]` to prevent gridlock.",
        f"  3. Keep the green corridor `[E-1]` clear for emergency vehicles.",
        f"  4. Guide spectators to peripheral parking `[P-1]` and promote metro usage.",
        "\n*You can ask me specific questions like: 'What are the hotspots?', 'What are the diversions?', 'What is the ambulance ETA?', or 'How many officers are needed?'*"
    ]
    return "\n".join(lines)

