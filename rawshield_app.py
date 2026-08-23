import streamlit as st
import pandas as pd
import io
import json
import google.generativeai as genai

st.set_page_config(page_title="RawShield Pro - Multimodal AI Intake", layout="wide", page_icon="🛡️")

# Inicijalizacija Gemini AI
api_key = st.secrets.get("GEMINI_API_KEY", None)
if api_key:
    genai.configure(api_key=api_key)

def extract_with_gemini(uploaded_file, doc_type):
    if not api_key:
        return {"error": "API ključ nije podešen u Streamlit Secrets."}
    
    file_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type if uploaded_file.type else "application/pdf"

    if doc_type == "invoice":
        prompt = """
        Ti si stručnjak za analizu faktura i prijemnih dokumenata u prehrambenoj i hemijskoj industriji.
        Analiziraj priloženi dokument (fakturu/otpremnicu) i vrati isključivo čist JSON format sa sledećim ključevima:
        {
            "supplier": "Naziv dobavljača/prodavca",
            "invoice_number": "Broj fakture/otpremnice",
            "lot_number": "LOT ili Batch broj pošiljke",
            "quantity_kg": 10000,
            "unit_price_eur": 2.50,
            "raw_material_name": "Naziv sirovine"
        }
        Ako neki podatak nedostaje, proceni ili ostavi prazan string. Nemoj pisati markdown tagove poput ```json, vrati samo čist JSON.
        """
    else:
        prompt = """
        Ti si stručnjak za kontrolu kvaliteta i laboratorijske analize (CoA sertifikate).
        Analiziraj priloženi sertifikat analize / CoA dokument i vrati isključivo čist JSON format sa listom svih očitanih parametara:
        {
            "raw_material_name": "Naziv sirovine sa analize",
            "lot_number": "LOT broj sa CoA",
            "parameters": [
                {
                    "param": "Naziv parametra (npr. Protein, Vlaga, Brix, Pepeo, Olovo)",
                    "unit": "Jedinica mere (npr. %, mg/kg, °Bx)",
                    "measured_value": 12.5,
                    "specification_limit": "npr. Max ≤ 5.0 ili Min ≥ 10"
                }
            ]
        }
        Nemoj pisati markdown tagove poput ```json, vrati samo čist JSON.
        """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            {"mime_type": mime_type, "data": file_bytes},
            prompt
        ])
        clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        return {"error": str(e)}

# Baza i istorija
if "history" not in st.session_state:
    st.session_state.history = []

st.title("🛡️ RawShield Pro — Autonomni AI OCR Prijem & Validacija")
st.caption("AI Multimodal Parser | Čitanje skeniranih faktura i laboratorijskih nalaza | Automatsko mapiranje")

if not api_key:
    st.warning("⚠️ Podešavanje u toku: Potrebno je uneti `GEMINI_API_KEY` u Streamlit Secrets kako bi AI mogao da skenira fizičke PDF dokumente.")

col_u1, col_u2 = st.columns(2)
with col_u1:
    inv_file = st.file_uploader("1. Prevucite Fakturu / Otpremnicu (PDF ili Sliku)", type=["pdf", "png", "jpg", "jpeg"], key="inv_file_ai")
with col_u2:
    coa_file = st.file_uploader("2. Prevucite CoA Sertifikat Analize (PDF ili Sliku)", type=["pdf", "png", "jpg", "jpeg"], key="coa_file_ai")

st.divider()

col_out1, col_out2 = st.columns([1, 1.3])

parsed_invoice = None
parsed_coa = None

# ================= OBRADA FAKTURE =================
with col_out1:
    st.subheader("📄 Ekstrakcija Podataka Fakture")
    if inv_file and api_key:
        with st.spinner("AI skenira fakturu..."):
            parsed_invoice = extract_with_gemini(inv_file, "invoice")
        
        if "error" in parsed_invoice:
            st.error(f"Greška pri obradi: {parsed_invoice['error']}")
        else:
            st.success(f"✅ Faktura uspešno očitana: `{inv_file.name}`")
            st.write(f"🏢 **Dobavljač:** `{parsed_invoice.get('supplier', 'N/A')}`")
            st.write(f"📦 **Sirovina:** `{parsed_invoice.get('raw_material_name', 'N/A')}`")
            st.write(f"🔢 **Broj Fakture:** `{parsed_invoice.get('invoice_number', 'N/A')}`")
            st.write(f"🏷️ **LOT Broj:** `{parsed_invoice.get('lot_number', 'N/A')}`")
            st.write(f"⚖️ **Količina:** `{parsed_invoice.get('quantity_kg', 0)} kg`")
            st.write(f"💶 **Cena:** `{parsed_invoice.get('unit_price_eur', 0.0):.2f} €/kg`")
    elif not inv_file:
        st.info("Ubaci fakturu u polje iznad.")

# ================= OBRADA COA =================
with col_out2:
    st.subheader("🔬 Ekstrakcija Laboratorijskih Nalaza (CoA)")
    if coa_file and api_key:
        with st.spinner("AI analizira parametre sa sertifikata..."):
            parsed_coa = extract_with_gemini(coa_file, "coa")

        if "error" in parsed_coa:
            st.error(f"Greška pri obradi: {parsed_coa['error']}")
        else:
            st.success(f"✅ CoA sertifikat uspešno očitan: `{coa_file.name}`")
            st.write(f"📦 **Identifikovana sirovina:** `{parsed_coa.get('raw_material_name', 'N/A')}`")
            st.write(f"🏷️ **LOT sa analize:** `{parsed_coa.get('lot_number', 'N/A')}`")

            params_list = parsed_coa.get("parameters", [])
            if params_list:
                df_params = pd.DataFrame(params_list)
                st.dataframe(df_params, use_container_width=True, hide_index=True)
                st.success("🟢 Svi parametri, jedinice i vrednosti su automatski prepoznati i razvrstani.")
    elif not coa_file:
        st.info("Ubaci CoA sertifikat u polje iznad.")

st.divider()

if st.button("💾 Zavedi Pošiljku u Centralni Registar", use_container_width=True):
    if parsed_invoice or parsed_coa:
        st.session_state.history.insert(0, {
            "Datum": "23.08.2026",
            "Faktura Fajl": inv_file.name if inv_file else "N/A",
            "CoA Fajl": coa_file.name if coa_file else "N/A",
            "Dobavljač": parsed_invoice.get("supplier", "N/A") if parsed_invoice and "error" not in parsed_invoice else "N/A",
            "Broj Fakture": parsed_invoice.get("invoice_number", "N/A") if parsed_invoice and "error" not in parsed_invoice else "N/A",
            "LOT": parsed_invoice.get("lot_number", "N/A") if parsed_invoice and "error" not in parsed_invoice else (parsed_coa.get("lot_number", "N/A") if parsed_coa else "N/A"),
            "Status": "✅ PROCESUIRANO"
        })
        st.success("Uspešno evidentirano!")

if st.session_state.history:
    st.markdown("### 📊 Centralna Baza Evidencije")
    df_h = pd.DataFrame(st.session_state.history)
    st.dataframe(df_h, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_h.to_excel(writer, index=False, sheet_name='Dnevnik')

    st.download_button(
        label="📥 Preuzmi Dnevnik u Excelu (.xlsx)",
        data=buffer.getvalue(),
        file_name="RawShield_Evidencija.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
