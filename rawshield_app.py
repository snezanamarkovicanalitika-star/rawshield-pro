import streamlit as st
import pandas as pd
import io
import json
import os
import tempfile
import google.generativeai as genai

st.set_page_config(page_title="RawShield Pro - AI Document Intelligence", layout="wide", page_icon="🛡️")

# Konfiguracija API ključa
api_key = st.secrets.get("GEMINI_API_KEY", None)
if api_key:
    genai.configure(api_key=api_key)

# Funkcija koja šalje skenirani PDF preko Files API-ja
@st.cache_data(show_spinner=False)
def parse_pdf_with_gemini(file_bytes, file_name, doc_type):
    if not api_key:
        return {"error": "API ključ nije podešen u Streamlit Secrets."}
    
    # 1. Čuvamo fajl privremeno na disku
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        # 2. Upload na Google Gemini Files API (pravi način za skenirane PDF-ove)
        uploaded_doc = genai.upload_file(path=tmp_path, mime_type="application/pdf")
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        if doc_type == "invoice":
            prompt = """
            Ti si ekspert za analizu faktura, otpremnica i CMR-ova.
            Pažljivo pregledaj ceo priloženi skenirani PDF dokument i izvuci podatke.
            Vrati ISKLJUČIVO JSON u sledećem formatu:
            {
                "supplier": "Tačan naziv dobavljača / izdavaoca računa",
                "raw_material": "Tačan naziv sirovine / artikla sa računa",
                "invoice_number": "Broj fakture / računa",
                "lot_number": "LOT / Šarža / Batch broj (ako postoji, inače N/A)",
                "quantity_kg": "Količina (samo broj u kg ili litrima)",
                "unit_price": "Cena po kg / jedinici (samo broj)",
                "currency": "Valuta (npr. EUR, RSD, USD)"
            }
            """
        else:
            prompt = """
            Ti si šef kontrole kvaliteta u prehrambenoj i procesnoj industriji.
            Pažljivo pregledaj ovaj CoA (Certificate of Analysis / Sertifikat Analize / Laboratorijski Izveštaj).
            Pronađi sve laboratorijske parametre, fizičko-hemijske i mikrobiološke analize (npr. Brix, Suva materija, Vlaga, Protein, Pepeo, Kiselost, pH, Teški metali...).
            Vrati ISKLJUČIVO JSON u sledećem formatu:
            {
                "raw_material": "Naziv ispitivanog proizvoda / sirovine",
                "lot_number": "LOT / Šarža / Batch sa sertifikata",
                "parameters": [
                    {
                        "param": "Naziv parametra",
                        "unit": "Jedinica mere (npr. %, °Bx, mg/kg, pH)",
                        "measured_value": "Izmereni rezultat (broj ili tekst)",
                        "spec_limit": "Zadata granica / specifikacija sa dokumenta (npr. Min 10 ili Max 5)"
                    }
                ]
            }
            """

        response = model.generate_content([uploaded_doc, prompt])
        
        # 3. Brisanje privremenog fajla sa Google servera
        genai.delete_file(uploaded_doc.name)
        
        return json.loads(response.text)

    except Exception as e:
        return {"error": str(e)}
    finally:
        # Brisanje lokalnog privremenog fajla
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# Istorija
if "history" not in st.session_state:
    st.session_state.history = []

st.title("🛡️ RawShield Pro — AI Prijem i Validacija Skeniranih Dokumenata")
st.caption("Autonomno OCR čitanje skeniranih i digitalnih Faktura & CoA sertifikata | Bez ručnog unosa")

if not api_key:
    st.error("⚠️ GEMINI_API_KEY nije pronađen u Secrets. Dodajte ga u Streamlit Settings -> Secrets.")

col_u1, col_u2 = st.columns(2)
with col_u1:
    inv_file = st.file_uploader("1. Prevucite Fakturu / Otpremnicu (PDF)", type=["pdf", "png", "jpg", "jpeg"], key="inv_file")
with col_u2:
    coa_file = st.file_uploader("2. Prevucite CoA Sertifikat Analize (PDF)", type=["pdf", "png", "jpg", "jpeg"], key="coa_file")

st.divider()

col_out1, col_out2 = st.columns([1, 1.2])

parsed_invoice = None
parsed_coa = None

# ================= 1. FAKTURA =================
with col_out1:
    st.subheader("📄 Podaci sa Fakture (Sken)")
    if inv_file:
        with st.spinner("🔍 AI pregleda skeniranu fakturu..."):
            parsed_invoice = parse_pdf_with_gemini(inv_file.getvalue(), inv_file.name, "invoice")

        if "error" in parsed_invoice:
            st.error(f"Greška pri očitavanju: {parsed_invoice['error']}")
        else:
            st.success(f"✅ Faktura pročitana: `{inv_file.name}`")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.text_input("🏢 Dobavljač:", value=str(parsed_invoice.get("supplier", "N/A")), key="out_supp")
                st.text_input("🔢 Broj Fakture:", value=str(parsed_invoice.get("invoice_number", "N/A")), key="out_inv")
                st.text_input("🏷️ LOT Broj:", value=str(parsed_invoice.get("lot_number", "N/A")), key="out_lot")
            with col_f2:
                st.text_input("📦 Sirovina:", value=str(parsed_invoice.get("raw_material", "N/A")), key="out_raw")
                st.text_input("⚖️ Količina (kg):", value=str(parsed_invoice.get("quantity_kg", "N/A")), key="out_qty")
                curr = parsed_invoice.get("currency", "EUR")
                st.text_input(f"💶 Cena ({curr}):", value=str(parsed_invoice.get("unit_price", "N/A")), key="out_price")
    else:
        st.info("Prevucite fakturu u levo polje.")

# ================= 2. COA =================
with col_out2:
    st.subheader("🔬 Laboratorijski Nalaz (CoA Sken)")
    if coa_file:
        with st.spinner("🔍 AI očitava laboratorijsku tabelu..."):
            parsed_coa = parse_pdf_with_gemini(coa_file.getvalue(), coa_file.name, "coa")

        if "error" in parsed_coa:
            st.error(f"Greška pri očitavanju: {parsed_coa['error']}")
        else:
            st.success(f"✅ CoA sertifikat pročitan: `{coa_file.name}`")
            st.write(f"📦 **Ispitivani proizvod:** `{parsed_coa.get('raw_material', 'N/A')}`")
            st.write(f"🏷️ **LOT Broj:** `{parsed_coa.get('lot_number', 'N/A')}`")
            
            params_list = parsed_coa.get("parameters", [])
            if params_list:
                df_p = pd.DataFrame(params_list)
                st.dataframe(
                    df_p.rename(columns={
                        "param": "Parametar Analize",
                        "unit": "Jedinica Mere",
                        "measured_value": "Izmereno (CoA)",
                        "spec_limit": "Zadati Standard / Granica"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                st.success("🟢 Svi parametri iz sertifikata su uspešno prepoznati i razvrstani.")
            else:
                st.warning("Tabela sa parametrima nije pronađena u dokumentu.")
    else:
        st.info("Prevucite CoA sertifikat u desno polje.")

st.divider()

# ================= 3. ZAVOĐENJE =================
if (inv_file or coa_file) and st.button("💾 Zavedi Očitane Podatke u Master Dnevnik", use_container_width=True):
    supp_val = parsed_invoice.get("supplier", "N/A") if parsed_invoice and "error" not in parsed_invoice else "N/A"
    inv_num_val = parsed_invoice.get("invoice_number", "N/A") if parsed_invoice and "error" not in parsed_invoice else "N/A"
    lot_val = parsed_invoice.get("lot_number", "N/A") if parsed_invoice and "error" not in parsed_invoice else (parsed_coa.get("lot_number", "N/A") if parsed_coa and "error" not in parsed_coa else "N/A")
    raw_val = parsed_coa.get("raw_material", "N/A") if parsed_coa and "error" not in parsed_coa else (parsed_invoice.get("raw_material", "N/A") if parsed_invoice and "error" not in parsed_invoice else "N/A")
    
    st.session_state.history.insert(0, {
        "Datum": "23.08.2026",
        "Dobavljač": supp_val,
        "Sirovina": raw_val,
        "Broj Fakture": inv_num_val,
        "LOT Broj": lot_val,
        "Faktura Dokument": inv_file.name if inv_file else "N/A",
        "CoA Dokument": coa_file.name if coa_file else "N/A",
        "Status": "✅ OČITANO I ARHIVIRANO"
    })
    st.success("Pošiljka je uspešno zavedena!")

if st.session_state.history:
    st.markdown("### 📊 Master Evidencija Ulaza")
    df_h = pd.DataFrame(st.session_state.history)
    st.dataframe(df_h, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_h.to_excel(writer, index=False, sheet_name='Master_Dnevnik')
    
    st.download_button(
        label="📥 Preuzmi Dnevnik u Excelu (.xlsx)",
        data=buffer.getvalue(),
        file_name="Master_Dnevnik_Prijema.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
 
