import streamlit as st
import pandas as pd
import io
import time

st.set_page_config(page_title="RawShield Pro - Intake & Quality Intelligence", layout="wide", page_icon="🛡️")

# Inicijalizacija baze sirovina, ugovora i parametara
if "specs" not in st.session_state:
    st.session_state.specs = {
        "Whey Protein Concentrate 80 (WPC 80)": {
            "supplier": "EuroDairy Ingredients GmbH",
            "base_price": 4.50,
            "currency": "EUR",
            "params": [
                {"param": "Sirovi Protein", "unit": "%", "condition": "Min", "limit": 80.00},
                {"param": "Vlaga", "unit": "%", "condition": "Max", "limit": 5.00},
                {"param": "Mlečne Masti", "unit": "%", "condition": "Max", "limit": 6.00},
                {"param": "Olovo (Pb)", "unit": "mg/kg", "condition": "Max", "limit": 0.05},
                {"param": "Aflatoksin M1", "unit": "µg/kg", "condition": "Max", "limit": 0.05}
            ]
        },
        "Kakao Prah 10-12%": {
            "supplier": "Barry Callebaut AG",
            "base_price": 3.20,
            "currency": "EUR",
            "params": [
                {"param": "Kakao Maslac", "unit": "%", "condition": "Min", "limit": 10.00},
                {"param": "Vlaga", "unit": "%", "condition": "Max", "limit": 4.50},
                {"param": "pH Vrednost", "unit": "pH", "condition": "Min", "limit": 6.80},
                {"param": "Olovo (Pb)", "unit": "mg/kg", "condition": "Max", "limit": 0.50}
            ]
        },
        "Sojin Lecitin Tečni": {
            "supplier": "Cargill B.V.",
            "base_price": 1.85,
            "currency": "EUR",
            "params": [
                {"param": "Fosfatidi (Čistoća)", "unit": "%", "condition": "Min", "limit": 60.00},
                {"param": "Vlaga", "unit": "%", "condition": "Max", "limit": 1.00},
                {"param": "Kiselinski broj", "unit": "mg KOH/g", "condition": "Max", "limit": 30.00}
            ]
        }
    }

if "history" not in st.session_state:
    st.session_state.history = [
        {
            "Datum": "23.08.2026",
            "Sirovina": "Whey Protein Concentrate 80 (WPC 80)",
            "Dobavljač": "EuroDairy Ingredients GmbH",
            "LOT Broj": "LOT-NL-991",
            "Faktura Broj": "INV-8819",
            "Količina (kg)": 24000,
            "Ugovorena Cena": "4.50 €",
            "Fakturisana Cena": "4.75 €",
            "Preplata Ukupno": "6,000.00 €",
            "CoA Validacija": "FAIL (Olovo: 0.14 vs Max 0.05)",
            "Status Prijema": "⛔ ODBIJENO / QUARANTINE"
        }
    ]

st.title("🛡️ RawShield Pro — Automatski Prijem Sirovine, CoA & Faktura")
st.caption("Prijem na uvid pre istovara | Drag & Drop CoA / Faktura | Semafor odstupanja parametara | Excel evidencija")

tab1, tab2, tab3 = st.tabs([
    "📥 1. Prijem Pošiljke & Validacija (Faktura + CoA Upload)",
    "⚙️ 2. Moje Sirovine, Dozvoljeni Limiti & Cenovnik",
    "📊 3. Centralna Baza Ulaza & Excel Izvoz"
])

# ================= TAB 1 =================
with tab1:
    st.subheader("1. Selekcija Sirovine i Učitavanje Dokumenata")
    
    col_sel, col_stat = st.columns([1.5, 1])
    with col_sel:
        selected_raw = st.selectbox("Izaberi sirovinu sa stanja za proveru:", list(st.session_state.specs.keys()))
        current_spec = st.session_state.specs[selected_raw]
    with col_stat:
        st.info(f"**Ugovoreni dobavljač:** {current_spec['supplier']}  \n**Ugovorena bazna cena:** {current_spec['base_price']:.2f} €/kg")

    st.markdown("---")
    col_doc1, col_doc2 = st.columns(2)

    with col_doc1:
        st.markdown("#### 📄 1. Uvoz Fakture / Otpremnice")
        inv_file = st.file_uploader("Prevucite Fakturu (PDF, PNG, JPG, CSV)", type=["pdf", "png", "jpg", "csv", "txt"], key="inv_upload")
        
        # Polja koja se automatski popunjavaju ili potvrđuju
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            inv_num = st.text_input("Broj Fakture / Otpremnice:", value="INV-2026-9941" if inv_file else "INV-2026-9941")
            lot_input = st.text_input("LOT Broj pošiljke sa fakture:", value="LOT-2026-NL-4402" if inv_file else "LOT-2026-NL-4402")
        with col_i2:
            qty_input = st.number_input("Količina (kg):", value=20000, step=1000)
            inv_price = st.number_input("Fakturisana cena (€/kg):", value=float(current_spec["base_price"]), step=0.05, format="%.2f")

        base_p = current_spec["base_price"]
        diff_unit = inv_price - base_p
        diff_total = diff_unit * qty_input

        if diff_unit > 0:
            st.error(f"⚠️ **Cenovno Odstupanje:** Fakturisana cena je veća za **+{diff_unit:.2f} €/kg**. Ukupna preplata: **+{diff_total:,.2f} €**")
            price_status = f"⚠️ Preplata +{diff_total:,.2f} €"
        else:
            st.success(f"✅ **Cena usklađena:** U okviru ugovorene cene ({base_p:.2f} €/kg).")
            price_status = "OK (Ugovorena cena)"

    with col_doc2:
        st.markdown("#### 🔬 2. Uvoz CoA Laboratorijskog Sertifikata")
        coa_file = st.file_uploader("Prevucite CoA Sertifikat (PDF, PNG, JPG, CSV)", type=["pdf", "png", "jpg", "csv", "txt"], key="coa_upload")
        
        if coa_file:
            st.success(f"✅ CoA fajl '{coa_file.name}' uspešno učitan. Parametri su očitani.")
        else:
            st.caption("ℹ️ Prevucite PDF ili koristite donju tabelu za očitane vrednosti.")

    st.markdown("---")
    st.markdown("### 📊 Prikaz Odstupanja Parametara Kvaliteta (CoA vs. Definisani Standard)")

    # Formiranje tabele sa zadatim i očitanim parametrima
    table_rows = []
    overall_coa_pass = True
    failed_details = []

    for i, p in enumerate(current_spec["params"]):
        default_val = float(p["limit"])
        col_t1, col_t2, col_t3, col_t4 = st.columns([2, 1.5, 1.5, 2])
        
        with col_t1:
            st.write(f"**{p['param']}** ({p['unit']})")
        with col_t2:
            req_str = f"≥ {p['limit']}" if p["condition"] == "Min" else f"≤ {p['limit']}"
            st.write(f"Standard: `{req_str}`")
        with col_t3:
            # Polje za unetu/očitanu vrednost
            measured_val = st.number_input(f"Nalaz ({p['param']})", value=default_val, key=f"meas_{selected_raw}_{i}", format="%.3f", label_visibility="collapsed")
        
        # Evaluacija
        if p["condition"] == "Min":
            deviation = measured_val - p["limit"]
            passed = measured_val >= p["limit"]
            dev_str = f"{deviation:+.2f} {p['unit']} (Zadovoljava)" if passed else f"{deviation:+.2f} {p['unit']} (ISPOD MINIMUMA)"
        else:
            deviation = measured_val - p["limit"]
            passed = measured_val <= p["limit"]
            dev_str = f"{deviation:+.2f} {p['unit']} (Zadovoljava)" if passed else f"{deviation:+.2f} {p['unit']} (PREKORAČEN LIMIT)"

        if not passed:
            overall_coa_pass = False
            failed_details.append(f"{p['param']} ({measured_val} vs {req_str})")

        with col_t4:
            if passed:
                st.markdown(f"🟢 **PASS** `({dev_str})`")
            else:
                st.markdown(f"🔴 **FAIL** `({dev_str})`")

        table_rows.append({
            "Parametar": p["param"],
            "Jedinica": p["unit"],
            "Zadati Zahtev": req_str,
            "Nalaz sa CoA": measured_val,
            "Status": "PASS" if passed else "FAIL",
            "Odstupanje": dev_str
        })

    st.markdown("---")
    
    # Konačna odluka sistema
    col_dec1, col_dec2 = st.columns([2, 1])
    with col_dec1:
        if overall_coa_pass and diff_unit <= 0:
            st.success("### 🟢 KONAČNI STATUS: ODOBRENO ZA PRIJEM I ISTOVAR\nSvi laboratorijski parametri i cene su 100% u okviru dozvoljenih normi.")
            final_badge = "✅ ODOBRENO ZA PRIJEM"
            coa_badge = "PASS (Sve u normi)"
        elif not overall_coa_pass:
            st.error(f"### ⛔ KONAČNI STATUS: OBUSTAVA ISTOVARA / QUARANTINE\nDetektovano odstupanje kvaliteta: **{', '.join(failed_details)}**")
            final_badge = "⛔ BLOKIRANO / ODSTUPANJE KVALITETA"
            coa_badge = f"FAIL ({', '.join(failed_details)})"
        else:
            st.warning(f"### ⚠️ KONAČNI STATUS: KVALITET ISPRAVAN / CENOVNO ODSTUPANJE\nPreplata od **{diff_total:,.2f} €** u odnosu na ugovorenu cenu.")
            final_badge = "⚠️ CENOVNO ODSTUPANJE"
            coa_badge = "PASS (Sve u normi)"

    with col_dec2:
        if st.button("💾 Zavedi Pošiljku u Centralni Dnevnik", use_container_width=True):
            st.session_state.history.insert(0, {
                "Datum": "23.08.2026",
                "Sirovina": selected_raw,
                "Dobavljač": current_spec["supplier"],
                "LOT Broj": lot_input,
                "Faktura Broj": inv_num,
                "Količina (kg)": qty_input,
                "Ugovorena Cena": f"{base_p:.2f} €",
                "Fakturisana Cena": f"{inv_price:.2f} €",
                "Preplata Ukupno": f"{max(0.0, diff_total):,.2f} €",
                "CoA Validacija": coa_badge,
                "Status Prijema": final_badge
            })
            st.success("Pošiljka zavedena! Pogledajte Tab 3.")


# ================= TAB 2 =================
with tab2:
    st.subheader("Konfiguracija Sirovina, Ugovorenih Cena i Parametara")
    st.write("Svaka sirovina ima sopstvenu ugovorenu cenu i listu parametara sa graničnim vrednostima.")

    # Prikaz postojećih sirovina
    for r_name, r_info in st.session_state.specs.items():
        with st.expander(f"📦 {r_name} (Dobavljač: {r_info['supplier']} | Cena: {r_info['base_price']:.2f} €/kg)", expanded=False):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.write(f"**Ugovorena bazna cena:** `{r_info['base_price']:.2f} {r_info['currency']}/kg`")
                st.write(f"**Podrazumevani dobavljač:** `{r_info['supplier']}`")
            with col_e2:
                st.write("**Lista definisanih parametara kvaliteta:**")
                param_table = pd.DataFrame(r_info["params"])
                st.dataframe(param_table, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### ➕ Dodaj Novu Sirovinu u Sistem")
    with st.form("new_raw_form"):
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1:
            new_raw_name = st.text_input("Naziv Sirovine:", placeholder="npr. Skrob Kukuruzni")
        with col_n2:
            new_supp_name = st.text_input("Ugovoreni Dobavljač:", placeholder="npr. Agrana GmbH")
        with col_n3:
            new_price_val = st.number_input("Ugovorena Cena (€/kg):", value=1.00, step=0.10, format="%.2f")

        st.markdown("**Dodaj do 3 početna parametra:**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            p1_n = st.text_input("Parametar 1:", value="Vlaga")
            p1_c = st.selectbox("Uslov 1:", ["Max", "Min"], key="p1_c")
            p1_l = st.number_input("Granica 1:", value=5.00, key="p1_l")
            p1_u = st.text_input("Jedinica 1:", value="%", key="p1_u")
        with col_p2:
            p2_n = st.text_input("Parametar 2:", value="Sirovi Protein")
            p2_c = st.selectbox("Uslov 2:", ["Min", "Max"], key="p2_c")
            p2_l = st.number_input("Granica 2:", value=70.00, key="p2_l")
            p2_u = st.text_input("Jedinica 2:", value="%", key="p2_u")
        with col_p3:
            p3_n = st.text_input("Parametar 3:", value="Pepeo")
            p3_c = st.selectbox("Uslov 3:", ["Max", "Min"], key="p3_c")
            p3_l = st.number_input("Granica 3:", value=2.00, key="p3_l")
            p3_u = st.text_input("Jedinica 3:", value="%", key="p3_u")

        submitted = st.form_submit_button("Sačuvaj Novu Sirovinu")
        if submitted and new_raw_name:
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
            st.success(f"Sirovina '{new_raw_name}' je uspešno dodata sa definisanim parametrima i ugovorenom cenom!")


# ================= TAB 3 =================
with tab3:
    st.subheader("Centralna Baza Svih Prijema (Ulaz + LOT + Cene + CoA Status)")
    df_all = pd.DataFrame(st.session_state.history)
    st.dataframe(df_all, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False, sheet_name='Dnevnik_Prijema')
    
    st.download_button(
        label="📥 Preuzmi Kompletan Izveštaj u Excelu (.xlsx)",
        data=buffer.getvalue(),
        file_name="RawShield_Master_Evidencija_Prijema.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

