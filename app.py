
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Drug Interaction Platform")

st.title("💊 Drug Interaction Intelligence Platform")
st.caption("Comprehensive Pharmacological & Clinical Interaction Analysis")

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    return pd.read_csv("ultimate_drug_interaction_dataset.csv")

data = load_data()

drug_list = sorted(set(data['Drug1']).union(set(data['Drug2'])))

# ---------------- INPUT ----------------
col1, col2 = st.columns(2)

with col1:
    drug1 = st.selectbox("Select Drug 1", drug_list)

with col2:
    drug2 = st.selectbox("Select Drug 2", drug_list)

# ---------------- PATIENT PROFILE ----------------
st.subheader("Patient Profile")

colP1, colP2, colP3 = st.columns(3)

with colP1:
    age = st.number_input("Age", 1, 100, 30, key="age")

with colP2:
    liver = st.selectbox("Liver Impairment", ["No", "Yes"], key="liver")

with colP3:
    renal = st.selectbox("Renal Impairment", ["No", "Yes"], key="renal")

# ---------------- DOSAGE ----------------
st.subheader("Dosage Information")

colD1, colD2 = st.columns(2)

with colD1:
    dose1 = st.number_input(f"{drug1} Dose (mg)", 0.0, key="dose1")

with colD2:
    dose2 = st.number_input(f"{drug2} Dose (mg)", 0.0, key="dose2")

# ---------------- PUBCHEM ----------------
def get_pubchem(drug):
    try:
        cid = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug}/cids/JSON"
        ).json()['IdentifierList']['CID'][0]

        return (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG",
            f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        )
    except:
        return None, None

# ---------------- RISK ----------------
def calculate_risk(severity, age, liver, renal, dose1, dose2):
    base = {"Minor": 3, "Moderate": 6, "Major": 9}.get(severity, 5)

    if age > 65:
        base += 1
    if liver == "Yes":
        base += 1.5
    if renal == "Yes":
        base += 1.5
    if dose1 > 500 or dose2 > 500:
        base += 1

    return min(round(base, 2), 10)

# ---------------- PDF ----------------
def generate_pdf(drug1, drug2, severity, risk, advice, outcome):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("Drug Interaction Report", styles['Title']),
        Paragraph(f"Drugs: {drug1} + {drug2}", styles['Normal']),
        Paragraph(f"Severity: {severity}", styles['Normal']),
        Paragraph(f"Risk Score: {risk}", styles['Normal']),
        Paragraph(f"Clinical Outcome: {outcome}", styles['Normal']),
        Paragraph(f"Advice: {advice}", styles['Normal']),
    ]

    doc.build(content)
    buffer.seek(0)
    return buffer

# ---------------- BUTTON ----------------
if st.button("Analyze Interaction"):

    row = data[
        ((data['Drug1'] == drug1) & (data['Drug2'] == drug2)) |
        ((data['Drug1'] == drug2) & (data['Drug2'] == drug1))
    ]

    st.divider()

    if len(row) > 0:

        r = row.iloc[0]
        severity = r["Severity"]
        risk = calculate_risk(severity, age, liver, renal, dose1, dose2)

        # ---------------- SUMMARY ----------------
        st.subheader("Interaction Summary")

        colA, colB, colC = st.columns(3)

        with colA:
            st.metric("Confidence", "100%")

        with colB:
            if severity == "Major":
                st.error(severity)
            elif severity == "Moderate":
                st.warning(severity)
            else:
                st.success(severity)

        with colC:
            st.metric("Risk Score (0–10)", risk)

        # ---------------- GAUGE ----------------
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk,
            gauge={'axis': {'range': [0, 10]}}
        ))
        st.plotly_chart(fig, use_container_width=True)

        # ---------------- GRAPH ----------------
        st.subheader("Severity Graph")

        fig_bar = go.Figure(go.Bar(
            x=["Minor", "Moderate", "Major"],
            y=[
                1 if severity == "Minor" else 0,
                1 if severity == "Moderate" else 0,
                1 if severity == "Major" else 0
            ]
        ))
        st.plotly_chart(fig_bar, use_container_width=True)

        # ---------------- STRUCTURES ----------------
        st.subheader("Drug Structures & References")

        c1, c2 = st.columns(2)

        with c1:
            img, link = get_pubchem(drug1)
            st.write(f"### {drug1}")
            if img:
                st.image(img, width=250)
                st.markdown(f"[View on PubChem]({link})")

        with c2:
            img, link = get_pubchem(drug2)
            st.write(f"### {drug2}")
            if img:
                st.image(img, width=250)
                st.markdown(f"[View on PubChem]({link})")

        # ---------------- TABS ----------------
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Overview", "Mechanism", "PK/PD", "Clinical"]
        )

        with tab1:
            st.info(r["Interaction"])
            st.write("Evidence:", r["Evidence_Type"])
            st.write("Effect:", r["Effect_Change"])

        with tab2:
            st.write("Mechanism:", r["Mechanism"])
            st.warning(f"CYP: {r['Cytochrome']}")

        with tab3:
            st.write("Pharmacokinetics:", r["Pharmacokinetics"])
            st.write("Pharmacodynamics:", r["Pharmacodynamics"])

        # ---------------- CLINICAL TAB (UPGRADED) ----------------
        with tab4:

            st.subheader("Clinical Summary")

            if severity == "Major":
                st.error("⚠️ Potentially Contraindicated Combination")

            st.subheader("Clinical Action")

            if severity == "Major":
                st.error("Avoid combination or use strict monitoring")
            elif severity == "Moderate":
                st.warning("Monitor patient or adjust dose")
            else:
                st.success("Generally safe")

            st.subheader("Real Clinical Risk")
            st.error(r["Clinical_Outcome"])

            st.subheader("Cytochrome Impact")
            cyp = str(r["Cytochrome"])

            if "3A4" in cyp:
                st.warning("CYP3A4 involvement → major metabolism interaction")
            elif "2D6" in cyp:
                st.warning("CYP2D6 involvement → altered response")
            elif "2C9" in cyp:
                st.warning("CYP2C9 involvement → clearance affected")
            else:
                st.info(cyp)

            st.subheader("What to Monitor")

            monitor = []

            if "Warfarin" in (drug1, drug2):
                monitor.append("INR levels")
            if "Digoxin" in (drug1, drug2):
                monitor.append("Serum digoxin levels")
            if "Aspirin" in (drug1, drug2):
                monitor.append("Bleeding risk")
            if "Insulin" in (drug1, drug2):
                monitor.append("Blood glucose levels")

            if len(monitor) == 0:
                monitor.append("General monitoring")

            for m in monitor:
                st.write("•", m)

            st.subheader("Detailed Clinical Info")

            st.write("Clinical Advice:", r["Clinical_Advice"])
            st.write("Dose:", r["Dose_Consideration"])
            st.write("Therapeutic Index:", r["Therapeutic_Index"])
            st.write("Onset:", r["Onset"])
            st.write("Route:", r["Route_Impact"])
            st.write("Patient Factors:", r["Patient_Factors"])

            st.subheader("Why This Matters")

            points = []

            if severity == "Major":
                points.append("High risk of severe toxicity")
            if liver == "Yes":
                points.append("Liver impairment increases toxicity")
            if renal == "Yes":
                points.append("Renal impairment causes accumulation")
            if age > 65:
                points.append("Elderly are more sensitive")
            if dose1 > 500 or dose2 > 500:
                points.append("High dose increases risk")

            for p in points:
                st.write("•", p)

        # ---------------- PDF ----------------
        pdf = generate_pdf(
            drug1,
            drug2,
            severity,
            risk,
            r["Clinical_Advice"],
            r["Clinical_Outcome"]
        )

        st.download_button(
            "Download Report",
            pdf,
            file_name="interaction_report.pdf"
        )

    else:
        st.warning("No interaction found")

    st.divider()
    st.caption("For research and educational use only")
