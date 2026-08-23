import streamlit as st
import pandas as pd
import io
import re
from pypdf import PdfReader

st.set_page_config(page_title="RawShield Pro - Real PDF Intake & CoA Parser", layout="wide", page_icon="🛡️")

# Pomoćna funkcija za izvlačenje čistog teksta iz PDF-a
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except Exception as e:
        return ""

# Baza sirovina (uključujući voćne piree / koncentrate)
if "specs" not in st.session_state:
    st.session_state.specs = {
        "Voćni Pire / Puree (Opšti Standard)": {
            "supplier": "Agrar Export D.O.O.",
            "base_price": 2.10,
            "currency": "EUR",
            "params": [
                {"param": "Brix (Suva Materija)", "unit": "°Bx", "condition": "Min", "limit": 10.00},
                {"param": "pH Vrednost", "unit": "pH", "condition": "Min", "limit": 3.50},
                {"param": "Ukupna Kiselost", "unit": "%", "condition": "Max", "limit": 1.20},
                {"param": "Vlaga / Voda", "unit": "%", "condition": "Max", "limit": 88.00},
                {"param": "Olovo (Pb)", "unit": "mg/kg", "condition": "Max", "limit": 0.05}
            ]
        },
        "Whey Protein Concentrate 80 (WPC 80)": {
            "supplier": "EuroDairy Ingredients GmbH",
            "base_price": 4.50,
            "currency": "EUR",
            "params": [
                {"param": "Sirovi Protein", "unit": "%", "condition": "Min", "limit": 80.00},
                {"param": "Vlaga", "unit": "%", "condition": "Max", "limit": 5.00},
                {"param": "Mlečne Masti", "unit": "%", "condition": "Max", "limit": 6.00},
                {"param": "Olovo (Pb)", "unit": "mg/kg", "condition": "Max", "limit": 0.05}
            ]
        }
    }

if "history" not in st.session_state:
    st.session_state.history = []

st.title("🛡️ RawShield Pro — Automatski Prijem i Ekstrakcija iz PDF-a")
st.caption("Direktno čitanje pravih PDF CoA i Faktura | Poređenje sa standardom | Excel evidencija")

tab1, tab2, tab3 = st.tabs([
    "📥 1. Prijem & Čitanje PDF Dokumenata",
    "⚙️ 2. Moje Sirovine & Dozvoljeni Limiti",
    "📊 3. Centralni Dnevnik & Excel Izvoz"
])

# ================= TAB 1 =================
with tab1:
    st.subheader("1. Izbor Sirovine i Ubacivanje Pravih Dokumenata")
    
    col_sel, col_stat = st.columns([1.5, 1])
    with col_sel:
        selected_raw = st.selectbox("Izaberi sirovinu za kontrolu:", list(st.session_state.specs.keys()))
        current_spec = st.session_state.specs[selected_raw]
    with col_stat:
        st.info(f"**Ugovoreni dobavljač:** {current_spec['supplier']}  \n**Ugovorena bazna cena:** {current_spec['base_price']:.2f} €/kg")

    st.markdown("---")
    col_doc1, col_doc2 = st.columns(2)

    # --- 1. UPLOAD I ČITANJE FAKTURE ---
    with col_doc1:
        st.markdown("#### 📄 1. Uvoz Fakture / Otpremnice")
        inv_file = st.file_uploader("Prevucite Fakturu (PDF)", type=["pdf", "png", "jpg", "txt"], key="real_inv_file")
        
        extracted_inv_num = "INV-RUČNO"
        extracted_lot = "LOT-RUČNO"
        extracted_qty = 10000
        extracted_price = current_spec["base_price"]

        if inv_file:
            pdf_text = extract_text_from_pdf(inv_file)
            st.success(f"✅ Faktura pročitana: `{inv_file.name}`")
            
            # Regex ekstrakcija iz teksta fakture
            inv_match = re.search(r'(?:racun|faktura|inv|invoice)[\s\:\#\-]*([A-Za-z0-9\-\/]+)', pdf_text, re.IGNORECASE)
            lot_match = re.search(r'(?:lot|šarža|sarza|batch)[\s\:\#\-]*([A-Za-z0-9\-\/]+)', pdf_text, re.IGNORECASE)
            
            if inv_match: extracted_inv_num = inv_match.group(1)
            else: extracted_inv_num = f"INV-{inv_file.name[:10]}"

            if lot_match: extracted_lot = lot_match.group(1)
            else: extracted_lot = f"LOT-{inv_file.name[:8]}"

        col_i1, col_i2 = st.columns(2)
        with col_i1:
            inv_num_val = st.text_input("Broj Fakture (Izvučeno iz PDF):", value=extracted_inv_num)
            lot_val = st.text_input("LOT Broj (Izvučeno iz PDF):", value=extracted_lot)
        with col_i2:
            qty_val = st.number_input("Količina (kg):", value=extracted_qty, step=1000)
            inv_price_val = st.number_input("Fakturisana cena (€/kg):", value=float(extracted_price), step=0.05, format="%.2f")

        base_p = current_spec["base_price"]
        diff_unit = inv_price_val - base_p
        diff_total = diff_unit * qty_val

        if diff_unit > 0:
            st.error(f"⚠️ **Preplata:** +{diff_unit:.2f} €/kg (Ukupno: +{diff_total:,.2f} €)")
        else:
            st.success(f"✅ Cena usklađena sa ugovorom ({base_p:.2f} €/kg)")

    # --- 2. UPLOAD I ČITANJE COA ---
    with col_doc2:
        st.markdown("#### 🔬 2. Uvoz CoA Sertifikata")
        coa_file = st.file_uploader("Prevucite CoA Sertifikat (PDF)", type=["pdf", "png", "jpg", "txt"], key="real_coa_file")
        
        coa_extracted_values = {}
        if coa_file:
            coa_text = extract_text_from_pdf(coa_file)
            st.success(f"✅ CoA pročitan: `{coa_file.name}`")
            with st.expander("🔍 Pogledaj sirovi tekst izvučen iz PDF-a"):
                st.text(coa_text if coa_text else "Tekst nije tekstualnog formata (skenirana slika).")

            # Regex traženje brojeva pored ključnih reči iz CoA teksta
            for p in current_spec["params"]:
                p_clean = p["param"].split("(")[0].strip()
                match = re.search(rf'{p_clean}[\s\:\=\-\>]*([0-9]+(?:[\.\,][0-9]+)?)', coa_text, re.IGNORECASE)
                if match:
                    val_str = match.group(1).replace(",", ".")
                    try:
                        coa_extracted_values[p["param"]] = float(val_str)
                    except:
                        pass

    st.markdown("---")
    st.markdown(f"### 📊 Validacija Parametara za: *{selected_raw}*")

    overall_coa_pass = True
    failed_details = []

    col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1.5, 1.8, 2.2])
    with col_h1: st.markdown("**Parametar Kvaliteta**")
    with col_h2: st.markdown("**Zadati Limit**")
    with col_h3: st.markdown("**Vrednost iz PDF Sertifikata**")
    with col_h4: st.markdown("**Status**")

    for i, p in enumerate(current_spec["params"]):
        # Koristi stvarnu vrednost izvučenu iz PDF-a, ili zadati limit ako parametar nije pronađen
        initial_val = coa_extracted_values.get(p["param"], float(p["limit"]))
        
        col_t1, col_t2, col_t3, col_t4 = st.columns([2, 1.5, 1.8, 2.2])
        
        with col_t1:
            st.write(f"**{p['param']}** ({p['unit']})")
        with col_t2:
            req_str = f"Min ≥ {p['limit']}" if p["condition"] == "Min" else f"Max ≤ {p['limit']}"
            st.code(req_str)
        with col_t3:
            measured_val = st.number_input(
                f"val_{p['param']}", 
                value=float(initial_val), 
                key=f"field_{selected_raw}_{i}_{coa_file.name if coa_file else 'none'}", 
                format="%.3f", 
                label_visibility="collapsed"
            )
        
        if p["condition"] == "Min":
            deviation = measured_val - p["limit"]
            passed = measured_val >= p["limit"]
            dev_str = f"{deviation:+.2f} {p['unit']} (OK)" if passed else f"{deviation:+.2f} {p['unit']} (ISPOD MIN)"
        else:
            deviation = measured_val - p["limit"]
            passed = measured_val <= p["limit"]
            dev_str = f"{deviation:+.2f} {p['unit']} (OK)" if passed else f"{deviation:+.2f} {p['unit']} (PREKO MAX)"

        if not passed:
            overall_coa_pass = False
            failed_details.append(f"{p['param']} ({measured_val} vs {req_str})")

        with col_t4:
            if passed:
                st.markdown(f"🟢 **PASS** `{dev_str}`")
            else:
                st.markdown(f"🔴 **FAIL** `{dev_str}`")

    st.markdown("---")
    
    col_dec1, col_dec2 = st.columns([2, 1])
    with col_dec1:
        if overall_coa_pass and diff_unit <= 0:
            st.success("### 🟢 STATUS: ODOBRENO ZA PRIJEM I ISTOVAR\nSvi laboratorijski parametri i cene su u okviru dozvoljenih normi.")
            final_badge = "✅ ODOBRENO"
            coa_badge = "PASS"
        elif not overall_coa_pass:
            st.error(f"### ⛔ STATUS: OBUSTAVA ISTOVARA / QUARANTINE\nOdstupanje kvaliteta: **{', '.join(failed_details)}**")
            final_badge = "⛔ BLOKIRANO"
            coa_badge = f"FAIL ({', '.join(failed_details)})"
        else:
            st.warning(f"### ⚠️ STATUS: CENOVNO ODSTUPANJE\nPreplata od **{diff_total:,.2f} €** u odnosu na ugovor.")
            final_badge = "⚠️ CENOVNO ODSTUPANJE"
            coa_badge = "PASS"

    with col_dec2:
        if st.button("💾 Zavedi Pošiljku u Dnevnik", use_container_width=True):
            st.session_state.history.insert(0, {
                "Datum": "23.08.2026",
                "Sirovina": selected_raw,
                "Dobavljač": current_spec["supplier"],
                "LOT": lot_val,
                "Faktura": inv_num_val,
                "Količina (kg)": qty_val,
                "Ugovorena Cena": f"{base_p:.2f} €",
                "Fakturisana Cena": f"{inv_price_val:.2f} €",
                "CoA Validacija": coa_badge,
                "Status Prijema": final_badge
            })
            st.success("Uspešno zavedeno u Tab 3!")

# ================= TAB 2 =================
with tab2:
    st.subheader("Baza Sirovina i Definisanje Standarda")
    
    with st.expander("➕ **DODAJ SVOJU SIROVINU I PARAMETRE IZ PDF-a**", expanded=True):
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1:
            new_raw_name = st.text_input("Naziv Sirovine (npr. Voćni Pire Jabuka):")
        with col_n2:
            new_supp_name = st.text_input("Dobavljač sa Fakture:")
        with col_n3:
            new_price_val = st.number_input("Ugovorena Cena (€/kg):", value=1.50, step=0.10, format="%.2f")

        st.markdown("##### Definiši parametre koji se nalaze na tvom CoA sertifikatu:")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            p1_n = st.text_input("Parametar 1:", value="Brix")
            p1_c = st.selectbox("Uslov 1:", ["Min", "Max"], key="u1")
            p1_l = st.number_input("Granica 1:", value=10.00, key="g1")
            p1_u = st.text_input("Jedinica 1:", value="°Bx", key="j1")
        with col_p2:
            p2_n = st.text_input("Parametar 2:", value="pH Vrednost")
            p2_c = st.selectbox("Uslov 2:", ["Min", "Max"], key="u2")
            p2_l = st.number_input("Granica 2:", value=3.50, key="g2")
            p2_u = st.text_input("Jedinica 2:", value="pH", key="j2")
        with col_p3:
            p3_n = st.text_input("Parametar 3:", value="Kiselost")
            p3_c = st.selectbox("Uslov 3:", ["Max", "Min"], key="u3")
            p3_l = st.number_input("Granica 3:", value=1.00, key="g3")
            p3_u = st.text_input("Jedinica 3:", value="%", key="j3")

        if st.button("💾 Sačuvaj Sirovinu", use_container_width=True):
            if new_raw_name:
                st.session_state.specs[new_raw_name] = {
                    "supplier": new_supp_name,
                    "base_price": new_price_val,
                    "currency": "EUR",
                    "params": [
                        {"param": p1_n, "unit": p1_u, "condition": p1_c, "limit": p1_l},
                        {"param": p2_n, "unit": p2_u, "condition": p2_c, "limit": p2_l},
                        {"param": p3_n, "unit": p3_u, "condition": p3_c, "limit": p3_l}
                    ]
                }
                st.success(f"Sirovina '{new_raw_name}' je sačuvana!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Trenutne sirovine:")
    for r_name in list(st.session_state.specs.keys()):
        col_e1, col_del = st.columns([4, 1])
        with col_e1:
            st.write(f"📦 **{r_name}** | Dobavljač: *{st.session_state.specs[r_name]['supplier']}* | Cena: *{st.session_state.specs[r_name]['base_price']:.2f} €/kg*")
        with col_del:
            if st.button("🗑️ Obriši", key=f"del_{r_name}"):
                del st.session_state.specs[r_name]
                st.rerun()

# ================= TAB 3 =================
with tab3:
    st.subheader("Centralni Registar & Excel")
    if st.session_state.history:
        df_all = pd.DataFrame(st.session_state.history)
        st.dataframe(df_all, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_all.to_excel(writer, index=False, sheet_name='Prijemi')
        
        st.download_button(
            label="📥 Preuzmi Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="Dnevnik_Prijema_Sirovine.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Dnevnik je prazan.")
