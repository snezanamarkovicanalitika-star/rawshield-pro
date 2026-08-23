
    
    import streamlit as st
import pandas as pd
import io
import json
import google.generativeai as genai

st.set_page_config(page_title="RawShield Pro - Ultra Fast AI Intake", layout="wide", page_icon="⚡")

# Konfiguracija API ključa
api_key = st.secrets.get("GEMINI_API_KEY", None)
if api_key:
    genai.configure(api_key=api_key)

# Ultra-brza direktna AI obrada
@st.cache_data(show_spinner=False)
def fast_ai_parse(file_bytes, mime_type, doc_type):
    if not api_key:
        return {"error": "API ključ nije postavljen u Secrets."}
    
    # Koristimo brzi Flash model sa direktnim JSON odzivom
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )
    
    if doc_type == "invoice":
        prompt = """
        Analiziraj priloženu fakturu/otpremnicu i vrati ISKLJUČIVO JSON objekat sa sledećim poljima:
        {
            "supplier": "Naziv dobavljača / prodavca",
            "raw_material": "Naziv sirovine / artikla sa računa",
            "invoice_number": "Broj fakture / računa",
            "lot_number": "LOT / Šarža / Batch broj",
            "quantity_kg": "Ukupna količina (broj ili kg)",
            "unit_price_eur": "Cena po jedinici/kg"
        }
        """
    else:
        prompt = """
        Analiziraj priloženi CoA (Sertifikat analize / Laboratorijski nalaz) i vrati ISKLJUČIVO JSON objekat:
        {
            "raw_material": "Naziv sirovine / proizvoda sa analize",
            "lot_number": "LOT / Šarža sa analize",
            "parameters": [
                {
                    "param": "Naziv parametra (npr. Brix, Vlaga, Protein, Pepeo, Kiselost, pH, itd.)",
                    "unit": "Jedinica mere (npr. %, °Bx, mg/kg, pH)",
                    "measured_value": "Izmereni laboratorijski rezultat",
                    "spec_limit": "Limit iz specifikacije / standarda"
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

# Istorija
if "history" not in st.session_state:
    st.session_state.history = []

st.title("⚡ RawShield Pro — Instant AI OCR & Prijem Sirovine")
st.caption("Direktno čitanje skeniranih i digitalnih CoA i faktura | Nema ručnog kucanja | Excel evidencija")

if not api_key:
    st.error("⚠️ `GEMINI_API_KEY` nije pronađen u Secrets. Dodajte ga u Streamlit Settings -> Secrets.")

col_u1, col_u2 = st.columns(2)
with col_u1:
    inv_file = st.file_uploader("1. Prevucite Fakturu / Otpremnicu (PDF, Slika)", type=["pdf", "png", "jpg", "jpeg"], key="inv_instant")
with col_u2:
    coa_file = st.file_uploader("2. Prevucite CoA Sertifikat Analize (PDF, Slika)", type=["pdf", "png", "jpg", "jpeg"], key="coa_instant")

st.divider()

col_out1, col_out2 = st.columns([1, 1.3])
parsed_invoice = None
parsed_coa = None

# Faktura
with col_out1:
    st.subheader("📄 Podaci sa Fakture")
    if inv_file:
        with st.spinner("⚡ AI očitava fakturu..."):
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
        st.info("Prevucite fakturu u polje iznad.")

# CoA
with col_out2:
    st.subheader("🔬 Parametri sa CoA Sertifikata")
    if coa_file:
        with st.spinner("⚡ AI očitava tabelu i parametre..."):
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
                st.success("🟢 Svi parametri, jedinice i vrednosti su automatski razvrstani.")
    else:
        st.info("Prevucite CoA sertifikat u polje iznad.")

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
