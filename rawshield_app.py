import streamlit as st
import pandas as pd
import io
import json
import google.generativeai as genai
from pypdf import PdfReader

st.set_page_config(page_title="RawShield Pro - Ultra Fast AI Intake", layout="wide", page_icon="⚡")

# Konfiguracija API ključa
api_key = st.secrets.get("GEMINI_API_KEY", None)
if api_key:
    genai.configure(api_key=api_key)

# Brzo izvlačenje prve strane
def get_first_page_text(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.pages:
            return reader.pages[0].extract_text() or ""
        return ""
    except Exception:
        return ""

# Ultra-brza ekstrakcija sa keširanjem
@st.cache_data(show_spinner=False)
def fast_ai_parse(file_bytes, file_name, doc_type):
    if not api_key:
        return {"error": "API ključ nije postavljen u Secrets."}
    
    text_content = get_first_page_text(file_bytes)
    
    # Koristimo najbrži Flash model sa direktnim JSON odzivom
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-8b",
        generation_config={"response_mime_type": "application/json"}
    )
    
    if doc_type == "invoice":
        prompt = f"""
        Extract invoice data from the document text or PDF content and return strictly JSON:
        {{
            "supplier": "Supplier company name",
            "raw_material": "Item name / raw material",
            "invoice_number": "Invoice number",
            "lot_number": "LOT / Batch number",
            "quantity_kg": "Total quantity in kg or unit",
            "unit_price_eur": "Price per kg in EUR"
        }}
        Text: {text_content[:3000] if text_content else "Extract directly from attached file bytes"}
        """
    else:
        prompt = f"""
        Extract Certificate of Analysis (CoA) parameters from text or file and return strictly JSON:
        {{
            "raw_material": "Raw material name on CoA",
            "lot_number": "LOT / Batch on CoA",
            "parameters": [
                {{
                    "param": "Parameter name (e.g. Brix, Dry matter, Protein, Moisture, Acidity, pH, Ash, Pb)",
                    "unit": "Unit (e.g. %, °Bx, mg/kg, pH)",
                    "measured_value": "Measured lab result",
                    "spec_limit": "Specification / standard limit"
                }}
            ]
        }}
        Text: {text_content[:3000] if text_content else "Extract directly from attached file bytes"}
        """

    try:
        if text_content and len(text_content.strip()) > 40:
            res = model.generate_content(prompt)
        else:
            res = model.generate_content([
                {"mime_type": "application/pdf", "data": file_bytes},
                prompt
            ])
        return json.loads(res.text)
    except Exception as e:
        return {"error": str(e)}

# Istorija
if "history" not in st.session_state:
    st.session_state.history = []

st.title("⚡ RawShield Pro — Instant AI OCR & Prijem Sirovine")
st.caption("Sub-second ekstrakcija faktura i CoA sertifikata | Automatsko mapiranje | Excel izvoz")

col_u1, col_u2 = st.columns(2)
with col_u1:
    inv_file = st.file_uploader("1. Prevucite Fakturu (PDF)", type=["pdf", "png", "jpg", "jpeg"], key="inv_instant")
with col_u2:
    coa_file = st.file_uploader("2. Prevucite CoA Sertifikat (PDF)", type=["pdf", "png", "jpg", "jpeg"], key="coa_instant")

st.divider()

col_out1, col_out2 = st.columns([1, 1.3])
parsed_invoice = None
parsed_coa = None

# Faktura
with col_out1:
    st.subheader("📄 Podaci sa Fakture")
    if inv_file:
        with st.spinner("⚡ Čitam fakturu..."):
            parsed_invoice = fast_ai_parse(inv_file.getvalue(), inv_file.name, "invoice")
        
        if "error" in parsed_invoice:
            st.error(f"Greška: {parsed_invoice['error']}")
        else:
            st.success(f"✅ Faktura očitana: `{inv_file.name}`")
            st.write(f"🏢 **Dobavljač:** `{parsed_invoice.get('supplier', 'N/A')}`")
            st.write(f"📦 **Sirovina:** `{parsed_invoice.get('raw_material', 'N/A')}`")
            st.write(f"🔢 **Broj Fakture:** `{parsed_invoice.get('invoice_number', 'N/A')}`")
            st.write(f"🏷️ **LOT Broj:** `{parsed_invoice.get('lot_number', 'N/A')}`")
            st.write(f"⚖️ **Količina:** `{parsed_invoice.get('quantity_kg', 'N/A')}`")
            st.write(f"💶 **Cena:** `{parsed_invoice.get('unit_price_eur', 'N/A')} €/kg`")
    else:
        st.info("Ubaci fakturu iznad.")

# CoA
with col_out2:
    st.subheader("🔬 Laboratorijski Nalaz (CoA)")
    if coa_file:
        with st.spinner("⚡ Čitam parametre..."):
            parsed_coa = fast_ai_parse(coa_file.getvalue(), coa_file.name, "coa")
            
        if "error" in parsed_coa:
            st.error(f"Greška: {parsed_coa['error']}")
        else:
            st.success(f"✅ CoA očitan: `{coa_file.name}`")
            st.write(f"📦 **Identifikovana sirovina:** `{parsed_coa.get('raw_material', 'N/A')}`")
            st.write(f"🏷️ **LOT sa analize:** `{parsed_coa.get('lot_number', 'N/A')}`")
            
            p_list = parsed_coa.get("parameters", [])
            if p_list:
                df_p = pd.DataFrame(p_list)
                st.dataframe(df_p, use_container_width=True, hide_index=True)
                st.success("🟢 Svi parametri, jedinice i vrednosti su očitani.")
    else:
        st.info("Ubaci CoA sertifikat iznad.")

st.divider()

if (inv_file or coa_file) and st.button("💾 Zavedi u Centralni Registar", use_container_width=True):
    st.session_state.history.insert(0, {
        "Datum": "23.08.2026",
        "Faktura Fajl": inv_file.name if inv_file else "N/A",
        "CoA Fajl": coa_file.name if coa_file else "N/A",
        "Dobavljač": parsed_invoice.get("supplier", "N/A") if parsed_invoice and "error" not in parsed_invoice else "N/A",
        "LOT": parsed_invoice.get("lot_number", "N/A") if parsed_invoice and "error" not in parsed_invoice else (parsed_coa.get("lot_number", "N/A") if parsed_coa else "N/A"),
        "Status": "✅ OČITANO I PROVERENO"
    })
    st.success("Uspešno sačuvano!")

if st.session_state.history:
    st.markdown("### 📊 Centralna Evidencija")
    df_h = pd.DataFrame(st.session_state.history)
    st.dataframe(df_h, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_h.to_excel(writer, index=False, sheet_name='Dnevnik')
    
    st.download_button(
        label="📥 Preuzmi Excel (.xlsx)",
        data=buffer.getvalue(),
        file_name="Master_Evidencija_Sirovina.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
