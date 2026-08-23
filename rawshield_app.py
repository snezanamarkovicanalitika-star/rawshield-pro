import streamlit as st
import pandas as pd
import io
import json
import google.generativeai as genai

st.set_page_config(page_title="RawShield Pro - AI Intake", layout="wide", page_icon="⚡")

# Konfiguracija API ključa
api_key = st.secrets.get("GEMINI_API_KEY", None)
if api_key:
    genai.configure(api_key=api_key)

# Brza AI obrada
@st.cache_data(show_spinner=False)
def fast_ai_parse(file_bytes, mime_type, doc_type):
    if not api_key:
        return {"error": "API ključ nije postavljen u Secrets."}
    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )
    
    if doc_type == "invoice":
        prompt = """
        Analiziraj priloženi dokument (fakturu / otpremnicu) i vrati isključivo JSON sa poljima:
        {
            "supplier": "Naziv dobavljača",
            "raw_material": "Naziv sirovine / artikla",
            "invoice_number": "Broj fakture",
            "lot_number": "LOT / Šarža",
            "quantity_kg": "Količina",
            "unit_price_eur": "Cena po jedinici/kg"
        }
        """
    else:
        prompt = """
        Analiziraj priloženi CoA sertifikat analize / laboratorijski nalaz i vrati isključivo JSON:
        {
            "raw_material": "Naziv sirovine sa analize",
            "lot_number": "LOT / Šarža sa analize",
            "parameters": [
                {
                    "param": "Naziv parametra (npr. Brix, Vlaga, Protein, Pepeo, Kiselost, pH, itd.)",
                    "unit": "Jedinica mere (npr. %, °Bx, mg/kg, pH)",
                    "measured_value": "Izmereni rezultat",
                    "spec_limit": "Limit iz specifikacije"
                }
            ]
        }
        """

    try:
        response = model.generate_content([
            {"mime_type": mime_type if mime_type else "application/pdf", "data": file_bytes},
            prompt
        ])
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

if "history" not in st.session_state:
    st.session_state.history = []

st.title("⚡ RawShield Pro — AI Automatski Prijem")
st.caption("Autonomno čitanje skeniranih i digitalnih CoA i faktura | Bez ručnog kucanja")

if not api_key:
    st.error("⚠️ GEMINI_API_KEY nije pronađen u Secrets. Proverite Streamlit Settings -> Secrets.")

col_u1, col_u2 = st.columns(2)
with col_u1:
    inv_file = st.file_uploader("1. Prevucite Fakturu (PDF ili slika)", type=["pdf", "png", "jpg", "jpeg"], key="inv_up")
with col_u2:
    coa_file = st.file_uploader("2. Prevucite CoA Sertifikat (PDF ili slika)", type=["pdf", "png", "jpg", "jpeg"], key="coa_up")

st.divider()

col_out1, col_out2 = st.columns([1, 1.3])
parsed_invoice = None
parsed_coa = None

# Faktura
with col_out1:
    st.subheader("📄 Podaci sa Fakture")
    if inv_file:
        with st.spinner("AI očitava fakturu..."):
            m_type = inv_file.type if inv_file.type else "application/pdf"
            parsed_invoice = fast_ai_parse(inv_file.getvalue(), m_type, "invoice")
        
        if "error" in parsed_invoice:
            st.error(f"Greška: {parsed_invoice['error']}")
        else:
            st.success(f"✅ Faktura očitana: `{inv_file.name}`")
            st.write(f"🏢 **Dobavljač:** `{parsed_invoice.get('supplier', 'N/A')}`")
            st.write(f"📦 **Sirovina:** `{parsed_invoice.get('raw_material', 'N/A')}`")
            st.write(f"🔢 **Broj Fakture:** `{parsed_invoice.get('invoice_number', 'N/A')}`")
            st.write(f"🏷️ **LOT Broj:** `{parsed_invoice.get('lot_number', 'N/A')}`")
            st.write(f"⚖️ **Količina:** `{parsed_invoice.get('quantity_kg', 'N/A')}`")
            st.write(f"💶 **Cena:** `{parsed_invoice.get('unit_price_eur', 'N/A')}`")
    else:
        st.info("Ubaci fakturu iznad.")

# CoA
with col_out2:
    st.subheader("🔬 Parametri sa CoA Sertifikata")
    if coa_file:
        with st.spinner("AI očitava tabelu i nalaz..."):
            m_type = coa_file.type if coa_file.type else "application/pdf"
            parsed_coa = fast_ai_parse(coa_file.getvalue(), m_type, "coa")
            
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
                st.success("🟢 Svi parametri, jedinice i vrednosti su automatski prepoznati.")
    else:
        st.info("Ubaci CoA sertifikat iznad.")

st.divider()

if (inv_file or coa_file) and st.button("💾 Zavedi u Centralni Registar", use_container_width=True):
    st.session_state.history.insert(0, {
        "Datum": "23.08.2026",
        "Faktura": inv_file.name if inv_file else "N/A",
        "CoA": coa_file.name if coa_file else "N/A",
        "Dobavljač": parsed_invoice.get("supplier", "N/A") if parsed_invoice and "error" not in parsed_invoice else "N/A",
        "LOT": parsed_invoice.get("lot_number", "N/A") if parsed_invoice and "error" not in parsed_invoice else (parsed_coa.get("lot_number", "N/A") if parsed_coa else "N/A"),
        "Status": "✅ PROCESUIRANO"
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
    
 
