"""
Traffic Event Co-Pilot: SIPOC demo for Uppal Stadium, Hyderabad.
Run:  streamlit run app.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
import event_engine as E  # noqa: E402
from map_view import make_map  # noqa: E402
import venue_catalog as VC  # noqa: E402
import police_chatbot as PC  # noqa: E402
import traffic_profiles as TP  # noqa: E402

st.set_page_config(page_title="Traffic Event Co-Pilot", page_icon="🚦", layout="wide")


@st.cache_resource(show_spinner="Loading road network for area...")
def get_network(network_path_str: str | None = None):
    p = Path(network_path_str) if network_path_str else E.GRAPH_PATH
    return E.build_network(p)


@st.cache_data(show_spinner=False)
def get_pack():
    return E.load_pack()


@st.cache_data(show_spinner="Evaluating scenario presets...")
def get_preset_comparison(_D, pack=None):
    presets = [
        {
            "Preset": "IPL weeknight 19:30 ingress",
            "params": {"attendance": 39000, "start_time": "19:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weeknight"}
        },
        {
            "Preset": "IPL weekend 15:30 ingress",
            "params": {"attendance": 39000, "start_time": "15:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weekend"}
        },
        {
            "Preset": "Same weekend match egress",
            "params": {"attendance": 39000, "start_time": "15:30", "phase": "egress", "duration_h": 3.0, "shift_pct": 0.0, "event_name": "IPL Weekend Egress"}
        },
        {
            "Preset": "20% metro shift",
            "params": {"attendance": 39000, "start_time": "19:30", "phase": "ingress", "duration_h": 3.0, "shift_pct": 20.0, "event_name": "20% Metro Shift"}
        },
    ]

    rows = []
    for p in presets:
        res_p = E.run_scenario(_D, p["params"], pack)
        rows.append({
            "Scenario Preset": p["Preset"],
            "Vehicles": f"{res_p['demand']['total_vehicles']:,}",
            "Peak PCU/hour": f"{round(res_p['demand']['peak_hourly_pcu']):,}",
            "Max V/C": f"{res_p['sum_opt']['max_vc']:.2f}",
            "Roads over capacity": res_p["sum_opt"]["congested"],
        })
    return pd.DataFrame(rows)


PACK = get_pack()
EVENTS = E.event_options(PACK)

# ------------------------------------------------------------------ sidebar
st.sidebar.title("🚦 Event setup")

# Location Auto-Suggest (like Google suggestions)
hyderabad_suggestions = VC.get_hyderabad_location_suggestions()
suggestion_keys = list(hyderabad_suggestions.keys())
location_choices = suggestion_keys + ["+ Custom Address / Coordinates in Hyderabad"]

selected_loc = st.sidebar.selectbox(
    "Location / Venue in Hyderabad (type to search)",
    location_choices,
    index=0,
    help="Type to search locations across Greater Hyderabad (stadiums, junctions, IT corridors, and areas)"
)

venue_coords = None
venue_info = None
if selected_loc == "+ Custom Address / Coordinates in Hyderabad":
    custom_area = st.sidebar.text_input("Area or Landmark name", "Charminar, Hyderabad")
    c_lat = st.sidebar.number_input("Latitude", value=17.3616, format="%.6f")
    c_lon = st.sidebar.number_input("Longitude", value=78.4747, format="%.6f")
    venue_coords = (float(c_lat), float(c_lon))
    st.sidebar.caption("Custom Sector Checkpoint")
    default_capacity = 25000
    selected_loc_name = custom_area
    venue_key = f"custom_{abs(int(c_lat*100))}_{abs(int(c_lon*100))}"
else:
    venue_info = hyderabad_suggestions[selected_loc]
    venue_coords = (venue_info["lat"], venue_info["lon"])
    default_capacity = venue_info["capacity"]
    venue_key = venue_info.get("key", "uppal_stadium")
    st.sidebar.caption(f"Jurisdiction: **{venue_info['commissionerate']}** | Area: {venue_info['area']}")
    selected_loc_name = selected_loc

# Load the road network for the selected location (dynamic network support)
net_path = VC.get_road_network_path(venue_key, venue_coords[0], venue_coords[1])
try:
    D, NET = get_network(str(net_path))
except Exception:
    D, NET = get_network(str(E.GRAPH_PATH))

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Event Details")
event_name = st.sidebar.text_input("Event Name / Description", value="SRH IPL Match 2026")
event_type = st.sidebar.selectbox(
    "Event Category",
    ["Cricket / Sports Match", "Concert / Music Show", "Political Rally / Gathering",
     "Exhibition / Trade Fair", "Marathon / Festival", "VIP Movement / Conference"],
    index=0
)
event_date = st.sidebar.date_input("Event Date", value=pd.to_datetime("2026-04-15").date())
start_time = st.sidebar.text_input("Start time (HH:MM)", "19:30")
attendance = st.sidebar.number_input(f"Expected Attendance / Crowd (ASSUMED capacity ~{default_capacity:,})", 1000, 150000, default_capacity, 1000)
phase = st.sidebar.radio("Phase", ["ingress", "egress"], horizontal=True,
                         help="ingress = people arriving before the event, egress = leaving after it")
private = st.sidebar.slider("Share arriving by own/hired vehicle (%)", 20, 90, 60)
shift = st.sidebar.slider("What-if: move this % of 2-wheeler and car riders to metro", 0, 40, 0)
with st.sidebar.expander("Approach shares (ASSUMED)"):
    shares = {k: st.slider(k, 0, 50, int(v * 100)) for k, v in E.DEFAULT_APPROACH_SHARE.items()}
demo_mode = st.sidebar.checkbox("Demo mode", value=False, help="Show SIPOC letter and guidance caption under each tab")
run = st.sidebar.button("▶ Run Co-Pilot", type="primary")

# Turn-back points missing coordinates (sidebar note)
manual_df = E.load_manual_locations()
if not manual_df.empty and "Type" in manual_df.columns:
    tb_mask = manual_df["Type"].astype(str).str.strip().str.lower() == "turnback"
    tb_rows = manual_df[tb_mask]
    missing_tb = []
    for _, r in tb_rows.iterrows():
        lat = r.get("Latitude")
        lon = r.get("Longitude")
        if pd.isna(lat) or pd.isna(lon) or str(lat).strip() == "" or str(lon).strip() == "":
            missing_tb.append(str(r.get("Location", "")).strip())
    if missing_tb:
        st.sidebar.markdown("---")
        with st.sidebar.expander(f"⚠️ Turn-backs without coordinates ({len(missing_tb)})", expanded=True):
            st.caption("These turn-back points lack coordinates and are skipped on the map until filled:")
            for item in missing_tb:
                st.write(f"• {item}")

if run or "res" not in st.session_state:
    with st.spinner("Estimating demand, loading roads, finding hotspots..."):
        st.session_state["res"] = E.run_scenario(D, {
            "attendance": int(attendance), "start_time": start_time, "phase": phase,
            "mode_share": E.mode_share_with_private_total(private / 100),
            "approach_share": {k: v / 100 for k, v in shares.items()}, "shift_pct": float(shift),
            "event_date": event_date,
            "event_name": event_name,
            "venue_latlon": venue_coords,
            "venue_name": selected_loc_name,
            "event_type": event_type}, PACK)
res = st.session_state["res"]
dem, so, sn = res["demand"], res["sum_opt"], res["sum_naive"]

# Top Header with Top-Right AI Chat Popover (as per UI specification)
head_col, ai_col = st.columns([0.76, 0.24])
with head_col:
    st.title("Traffic Event Co-Pilot (Greater Hyderabad)")
    st.caption(f"Area: **{selected_loc_name}** | Event: **{event_name}** ({event_type}) | Plans traffic before the event happens.")
with ai_col:
    st.write("")
    chat_popover = st.popover("✨ AI Chat", use_container_width=True)
    with chat_popover:
        st.markdown("### ✨ AI Chat")
        st.caption("Ask questions regarding the generated traffic plan, bottlenecks, diversions, emergency corridors, and police deployment.")

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = [
                {"role": "assistant", "content": f"Hello, Officer. I have prepared the traffic operation plan for **{res['params']['event_name']}**. How can I help you understand the plan, manage bottlenecks, or position your personnel?"}
            ]

        # Quick prompt buttons
        q_btn_cols = st.columns(2)
        quick_query_top = None
        if q_btn_cols[0].button("🚨 Bottlenecks", key="q1_top"):
            quick_query_top = "What are the critical bottlenecks?"
        if q_btn_cols[1].button("🔀 Diversions", key="q2_top"):
            quick_query_top = "Explain the diversion scheme"
        if q_btn_cols[0].button("🚑 Ambulance ETA", key="q3_top"):
            quick_query_top = "What is the emergency corridor route and ETA?"
        if q_btn_cols[1].button("👮 Deployment", key="q4_top"):
            quick_query_top = "What is the recommended police personnel deployment?"

        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        with st.form("top_chat_form", clear_on_submit=True):
            f_cols = st.columns([0.80, 0.20])
            user_text_top = f_cols[0].text_input("Ask your copilot anything...", placeholder="Ask about bottlenecks, diversions, ETA...", label_visibility="collapsed")
            send_btn = f_cols[1].form_submit_button("➤")

        active_top_q = quick_query_top or (user_text_top if send_btn and user_text_top.strip() else None)
        if active_top_q:
            st.session_state["chat_history"].append({"role": "user", "content": active_top_q})
            ans_top = PC.generate_police_response(active_top_q, res)
            st.session_state["chat_history"].append({"role": "assistant", "content": ans_top})
            st.rerun()

# Data status strip
st.markdown("### Data status")
ds1, ds2, ds3 = st.columns(3)
ds1.success("**REAL** (OSM, advisories)")
ds2.warning("**ASSUMED** (parameters)")
ds3.error("**MISSING** (event-day counts)")

# Warning badges until real rows exist in data/manual_locations.csv
badges = []
if res.get("hospital_is_placeholder", True):
    badges.append("Hospital is a placeholder")
if res.get("parking_is_generated", True):
    badges.append("Parking zones are generated")

if badges:
    badge_cols = st.columns(len(badges))
    for col, badge_text in zip(badge_cols, badges):
        col.warning(f"⚠️ {badge_text}")

t1, t2, t3, t4, t5, t6 = st.tabs(["1 · SIPOC overview", "2 · Suppliers → Inputs", "3 · Process",
                                  "4 · Outputs", "5 · 📋 Operational Plan & Customers", "6 · 💬 Police Copilot Chatbot"])

# ------------------------------------------------------------------ 1. SIPOC
with t1:
    if demo_mode:
        st.caption("ℹ️ **SIPOC Overview (S, I, P, O, C):** Look at the complete system map and how real OSM network and police advisories balance with assumed parameters.")
    st.subheader("SIPOC of the Traffic Event Co-Pilot")
    sipoc = pd.DataFrame({
        "S: Suppliers": ["OpenStreetMap (road network)", "Traffic police advisories (Rachakonda / Malkajgiri)",
                         "HMRL metro and TGSRTC bus provisions", "News and event schedules (dates, start times)",
                         "Event organiser (attendance): not yet connected", "RTA vehicle data (fleet mix): planned"],
        "I: Inputs": ["Event name, date, start time, attendance", "3 km road graph around the stadium",
                      "Mode split and occupancy (assumed)", "Diversion points and time windows",
                      "Metro and bus support on match days", "Approach shares (where traffic comes from)"],
        "P: Process": ["1 Collect and clean data", "2 Build road graph, estimate capacity", "3 Snap locations to roads",
                       "4 Demand per mode in PCU, 15-min peak", "5 Load roads: naive vs optimised, V/C and delay",
                       "6 Hotspots, diversions, emergency corridor, plan text"],
        "O: Outputs": ["Congestion hotspots with V/C", "Colour-coded congestion map",
                       "Diversion routes with extra distance", "Protected emergency corridor and ETA",
                       "What-if comparison", "Event traffic plan (downloadable)"],
        "C: Customers": ["Traffic police planners", "Event organiser", "Emergency services (ambulance, fire)",
                         "Commuters and attendees", "Metro and bus operators", "Project mentor / evaluator"],
    })
    st.dataframe(sipoc, hide_index=True)
    c1, c2, c3 = st.columns(3)
    c1.success("**Real data used**\n\nOSM road network\n\nPolice advisories and diversions\n\nEvent dates, metro and bus provisions")
    c2.warning("**Assumed (labelled in the app)**\n\nMode split, occupancy, PCU factors\n\nRoad capacity and speeds\n\n"
               "Approach shares, background traffic, parking zones")
    c3.error("**Missing (needs police data)**\n\nClassified vehicle counts on event days\n\nSpeeds and queue lengths\n\n"
             "Real hospital and parking coordinates")

# ------------------------------------------------------------------ 2. Suppliers -> Inputs
with t2:
    if demo_mode:
        st.caption("ℹ️ **S & I (Suppliers & Inputs):** Look at the selected event details, OSM network data quality, and the travel mode split.")
    st.subheader("Suppliers → Inputs")
    a, b = st.columns(2)
    with a:
        st.markdown("**Event selected**")
        st.write({"Event": res["params"]["event_name"], "Date": str(res["params"]["event_date"] or "custom"),
                  "Start": res["params"]["start_time"], "Phase": res["params"]["phase"],
                  "Attendance": f"{res['params']['attendance']:,}"})
        st.caption(f"Category: {event_type} | Operational Phase: {phase.title()}")
        st.markdown("**Data pack (Excel)**")
        st.write({k: f"{len(v)} rows" for k, v in PACK.items()} if PACK else "Data pack not found")
    with b:
        st.markdown("**Road network quality**")
        st.write({"Routable junctions": NET["nodes"], "Road segments": NET["edges"],
                  "Lanes missing in OSM (defaulted)": f"{NET['pct_lanes_defaulted']}%",
                  "Speeds missing in OSM (defaulted)": f"{NET['pct_speed_defaulted']}%",
                  "Real event-day vehicle counts": "0 (not public)"})
        st.caption("Almost all roads have no lane or speed tag in OSM, so capacities are estimates. "
                   "This is why we show model estimates, not measurements.")
    st.markdown("**Police advisory diversions for this date**")
    adv = res["advisory"]
    if adv is not None and not adv.empty:
        st.dataframe(adv[["Movement", "Vehicle_Class", "Diversion_Point", "Diverted_Route", "Window_Start", "Window_End"]]
                     .drop_duplicates(), hide_index=True)
    else:
        st.info("No advisory rows for this date in the data pack.")
    st.markdown("**Mode split used (share of people)**")
    ms = pd.DataFrame({"mode": list(dem["mode_share"]), "share_%": [round(v * 100, 1) for v in dem["mode_share"].values()]})
    st.bar_chart(ms.set_index("mode"))

    st.markdown("---")
    st.markdown("### 📊 24-Hour & 7-Day Baseline Traffic Patterns (HMDA CTS & IRC:106 Data)")
    st.caption("Average hourly traffic volume and classified vehicle mix passing through this road category on each day of the week.")

    day_name = pd.to_datetime(event_date).day_name()
    ev_hour = int(start_time.split(":")[0]) if ":" in start_time else 19
    c_day1, c_day2 = st.columns(2)
    with c_day1:
        st.markdown(f"**24-Hour Diurnal Traffic Curve ({day_name})**")
        curve_df = TP.get_diurnal_24h_curve(day_of_week=day_name, road_category="Primary_Arterial")
        if not curve_df.empty:
            st.line_chart(curve_df.set_index("Time_Window")[["Total_Vehicles", "Total_PCU"]])
    with c_day2:
        st.markdown(f"**Classified Vehicle Mix during Event Hour ({start_time[:2]}:00)**")
        slice_data = TP.get_hourly_slice(day_of_week=day_name, hour=ev_hour, road_category="Primary_Arterial")
        if slice_data:
            mix_df = pd.DataFrame({
                "Vehicle Class": ["2-Wheelers", "Cars", "Autos", "Buses", "Trucks/LCVs"],
                "Count": [slice_data["Two_Wheeler_Count"], slice_data["Car_Count"], slice_data["Auto_Rickshaw_Count"], slice_data["Bus_Count"], slice_data["LCV_Truck_Count"]]
            })
            st.bar_chart(mix_df.set_index("Vehicle Class"))

    st.markdown(f"**7-Day Traffic Volume Comparison at {start_time[:2]}:00 (Vehicles passing through corridor)**")
    week_df = TP.get_weekly_comparison(hour=ev_hour, road_category="Primary_Arterial")
    if not week_df.empty:
        st.dataframe(week_df, hide_index=True)

# ------------------------------------------------------------------ 3. Process
with t3:
    if demo_mode:
        st.caption("ℹ️ **P (Process):** Look at the 15-minute arrival PCU profile and how successive averaging reallocates traffic across roads.")
    st.subheader("Process: what the Co-Pilot does, step by step")
    st.markdown("**Step 1-2. Data and road graph**")
    st.write(f"{NET['nodes']:,} junctions, {NET['edges']:,} road segments, road types: {NET['road_types']}")
    st.markdown("**Step 3. Locations snapped to road junctions (approach entry points)**")
    rows = [{"Approach": n, "Share of traffic": f"{a['share']*100:.0f}%", "Entry junctions": len(a["nodes"]),
             "Lat/Lon": f"{a['latlon'][0]:.4f}, {a['latlon'][1]:.4f}"} for n, a in res["approaches"].items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Uppal metro station uses verified coordinates because the geocoder result was about 1 km off.")
    st.markdown("**Step 4. Demand per mode (people → vehicles → PCU)**")
    dtab = pd.DataFrame({"mode": list(E.MODES),
                         "people": [round(dem["persons"][m]) for m in E.MODES],
                         "vehicles": [dem["vehicles"].get(m, 0) for m in E.MODES],
                         "PCU": [round(dem["pcu"].get(m, 0)) for m in E.MODES]})
    st.dataframe(dtab, hide_index=True)
    st.write(f"Total {dem['total_vehicles']:,} vehicles = {dem['total_pcu']:,.0f} PCU. Busiest 15 minutes start at "
             f"**{dem['peak_bucket']}**: {dem['peak_15min_pcu']:,.0f} PCU = {dem['peak_hourly_pcu']:,.0f} PCU/hour.")
    st.line_chart(dem["curve"].set_index("Time")["PCU"])
    st.markdown("**Step 5. Load the roads: naive vs optimised**")
    st.write("Naive = everyone takes the shortest empty-road path (what a plain route finder does). "
             "Optimised = repeated re-routing as roads fill up (method of successive averages).")
    st.line_chart(pd.DataFrame({"max V/C": res["history"]}, index=[f"iter {i}" for i in range(len(res["history"]))]))
    st.markdown("**Step 6-7. Hotspots, diversions, emergency corridor** are shown in the Outputs tab.")

# ------------------------------------------------------------------ 4. Outputs
with t4:
    if demo_mode:
        st.caption("ℹ️ **O (Outputs):** Look at critical congestion bottlenecks, diversion paths with detour penalties, and preset scenario comparisons.")
    st.subheader("Outputs")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vehicles", f"{dem['total_vehicles']:,}")
    m2.metric("Peak PCU / hour", f"{dem['peak_hourly_pcu']:,.0f}")
    m3.metric("Max V/C (Co-Pilot)", f"{so['max_vc']:.2f}", f"{so['max_vc'] - sn['max_vc']:+.2f} vs naive", delta_color="inverse")
    m4.metric("Roads over capacity", so["congested"], f"{so['congested'] - sn['congested']:+d} vs naive", delta_color="inverse")
    view = st.radio("Map shows", ["Co-Pilot (optimised)", "Naive shortest path"], horizontal=True)
    try:
        from streamlit_folium import st_folium
        st_folium(make_map(D, res, use_naive=view.startswith("Naive")), height=560, width=1200,
                  returned_objects=[])
    except Exception as exc:
        st.warning(f"Map could not be drawn: {exc}")
    st.markdown("**Congestion hotspots (streets)**")
    hs = res["hotspots"]
    if len(hs):
        st.dataframe(hs[["street", "road_type", "lanes", "segments", "load_pcu_hr", "capacity_pcu_hr", "vc", "fed_by"]]
                     .rename(columns={"vc": "V/C"}).head(10), hide_index=True)
    st.markdown("**Recommended diversions for the worst hotspots**")
    dv = pd.DataFrame([{"Hotspot": d["name"], "V/C": d["vc"], "Feasible": d["feasible"],
                        "Extra metres": d.get("extra_m"), "Extra seconds": d.get("extra_s"), "Note": d["note"]}
                       for d in res["diversions"]])
    if len(dv):
        st.dataframe(dv, hide_index=True)
    c = res["corridor"]
    if c:
        hosp_note = "Hospital point is a placeholder." if res.get("hospital_is_placeholder", True) else "Hospital point from manual_locations.csv."
        st.info(f"Protected emergency corridor: {c['length_m']:,} m. ETA {c['free_min']} min if kept clear, "
                f"about {c['unprotected_min']} min if open to event traffic. {hosp_note}")
    st.markdown("**What-if: shifting riders to metro**")
    if st.button("Run what-if comparison (0, 10, 20, 30%)"):
        rows = []
        for sh in (0, 10, 20, 30):
            r2 = E.run_scenario(D, {**res["params"], "shift_pct": float(sh)}, PACK)
            rows.append({"Shift to metro %": sh, "Vehicles": r2["demand"]["total_vehicles"],
                         "Peak PCU/h": round(r2["demand"]["peak_hourly_pcu"]), "Max V/C": r2["sum_opt"]["max_vc"],
                         "Roads over capacity": r2["sum_opt"]["congested"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.markdown("**Scenario Preset Comparison**")
    st.caption("Side-by-side comparison across 4 standard event presets (attendance ASSUMED: 39,000).")
    comp_df = get_preset_comparison(D, PACK)
    st.dataframe(comp_df, hide_index=True)

# ------------------------------------------------------------------ 5. Operational Plan & Customers
with t5:
    if demo_mode:
        st.caption("ℹ️ **C (Customers):** Look at tailored deliverables for traffic police, event organizers, ambulances, and commuter advisories.")
    
    st.markdown(f"### 📋 Special Traffic Operation Plan: {res['params']['event_name']}")
    st.caption(f"Authority: Hyderabad Traffic Police | Sector: {selected_loc_name} | Operational Phase: {res['params']['phase'].title()}")

    # Quick Download Buttons at the top
    d1, d2, d3 = st.columns(3)
    d1.download_button("📥 Download Plan (.MD)", res["report"], f"traffic_plan_{res['params']['event_name']}.md", key="dl_md_top")
    d1_txt = res["report"].replace("#", "").replace("**", "")
    d2.download_button("📥 Download Plan (.TXT)", d1_txt, f"traffic_plan_{res['params']['event_name']}.txt", key="dl_txt_top")
    d3.download_button("📥 Download Hotspots (.CSV)", res["table_opt"].to_csv(index=False), "hotspots.csv", key="dl_csv_top")

    # Key Tactical Numbers Banner
    km1, km2, km3, km4 = st.columns(4)
    km1.metric("Expected Crowd", f"{res['params']['attendance']:,}")
    km2.metric("Total Vehicles", f"{dem['total_vehicles']:,}")
    km3.metric("Peak Rush", f"{dem['peak_hourly_pcu']:,.0f} PCU/h")
    c_eta = f"{res['corridor']['free_min']} min" if res['corridor'] else "N/A"
    km4.metric("Green Corridor ETA [E-1]", c_eta)

    st.markdown("---")
    # Complete text-based detailed plan for the police to read
    st.markdown(res["report"])

    st.markdown("---")
    st.subheader("Stakeholder Deliverables (Customers)")
    top = hs.head(3)["street"].tolist() if len(hs) else []
    cols = st.columns(2)
    with cols[0]:
        st.markdown("##### Traffic police planners")
        st.write("Full plan with hotspots, diversions and emergency corridor (above, downloadable).")
        st.markdown("##### Event organiser")
        st.write(f"Plan for about {dem['buses']} event buses and {dem['metro_riders']:,.0f} metro riders. "
                 f"{dem['pedestrians']:,.0f} people arrive on foot, so gate queues and metro exits need crowd control.")
    with cols[1]:
        st.markdown("##### Emergency services")
        c = res["corridor"]
        st.write(f"Keep the purple corridor clear ({c['length_m']:,} m, {c['free_min']} min)." if c else "No corridor computed.")
        st.markdown("##### Commuters (draft public message)")
        msg = (f"Heavy traffic expected around {selected_loc_name} from {res['params']['start_time']}. Avoid {', '.join(top) if top else 'the venue roads'}. "
               "Use Metro or TGSRTC special buses.")
        st.code(msg, language=None)

# ------------------------------------------------------------------ 6. Police Copilot Chatbot
with t6:
    st.subheader("💬 Police Copilot Chatbot")
    st.caption("Ask operational questions regarding the traffic plan, bottlenecks [H], diversions [D], green corridors [E], and personnel deployment.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {"role": "assistant", "content": f"Hello, Officer. I have prepared the traffic operation plan for **{res['params']['event_name']}**. How can I help you understand the plan, manage bottlenecks, or position your personnel?"}
        ]

    # Quick prompt buttons
    st.markdown("**Quick Inquiries:**")
    qc1, qc2, qc3, qc4 = st.columns(4)
    quick_q = None
    if qc1.button("🚨 Critical Bottlenecks"):
        quick_q = "What are the critical bottlenecks?"
    if qc2.button("🔀 Diversion Directives"):
        quick_q = "Explain the diversion scheme"
    if qc3.button("🚑 Emergency Corridor"):
        quick_q = "What is the emergency corridor route and ETA?"
    if qc4.button("👮 Police Deployment"):
        quick_q = "What is the recommended police personnel deployment?"

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Ask a question about this traffic plan...") or quick_q
    if user_query:
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        ans = PC.generate_police_response(user_query, res)
        st.session_state["chat_history"].append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans)
