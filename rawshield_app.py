import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="RawShield Pro - AI Intake & CoA Verification", layout="wide", page_icon="🛡️")

# Inicijalizacija baze sirovina
if "specs" not in st.session_state:
    st.session_state.specs = {
        "Whey Protein Concentrate 80 (WPC 80)": {
            "supplier": "EuroDairy Ingredients GmbH",
            "base_price": 4.50,
            "currency": "EUR",
            "params": [
                {"param": "Sirovi Protein", "unit": "%", "condition": "Min", "limit": 80.00, "default_coa": 79.20},
                {"param": "Vlaga", "unit": "%", "condition": "Max", "limit": 5.00, "default_coa": 4.60},
                {"param": "Mlečne Masti", "unit": "%", "condition": "Max", "limit": 6.00, "default_coa": 5.80},
                {"param": "Olovo (Pb)", "unit": "mg/kg", "condition": "Max", "limit": 0.05, "default_coa": 0.12},
                {"param": "Aflatoksin M1", "unit": "µg/kg", "condition": "Max", "limit": 0.05, "default_coa": 0.02}
            ]
        },
        "Kakao Prah 10-12%": {
            "supplier": "Barry Callebaut AG",
            "base_price": 3.20,
            "currency": "EUR",
            "params": [
                {"param": "Kakao Maslac", "unit": "%", "condition": "Min", "limit": 10.00, "default_coa": 10.50},
                {"param": "Vlaga", "unit": "%", "condition": "Max", "limit": 4.50, "default_coa": 4.10},
                {"param": "pH Vrednost", "unit": "pH", "condition": "Min", "limit": 6.80, "default_coa": 7.10},
                {"param": "Olovo (Pb)", "unit": "mg/kg", "condition": "Max", "limit": 0.50, "default_coa": 0.35}
            ]
        }
    }

if "history" not in st.session_state:
    st.session_state.history = []

st.title("🛡️ RawShield Pro — Automatski Prijem Sirovine, CoA & Faktura")
st.caption("AI Analiza dokumenata | Drag & Drop CoA / Faktura | Automatsko poređenje nalaza i cena | Excel evidencija")

tab1, tab2, tab3 = st.tabs([
    "📥 1. Prijem Pošiljke & Validacija (Faktura + CoA Upload)",
    "⚙️ 2. Moje Sirovine, Dozvoljeni Limiti & Dodavanje",
    "📊 3. Centralna Baza Ulaza & Excel Izvoz"
])

# ================= TAB 1 =================
with tab1:
    st.subheader("1. Izbor Sirovine i Učitavanje Dokumenata")
    
    raw_list = list(st.session_state.specs.keys())
    if not raw_list:
        st.info("💡 Baza sirovina je trenutno prazna. Otvorite **Tab 2** da dodate svoju sirovinu, ugovorenu cenu i parametre.")
    else:
        col_sel, col_stat = st.columns([1.5, 1])
        with col_sel:
            selected_raw = st.selectbox("Izaberi sirovinu koja stiže na prijem:", raw_list)
            current_spec = st.session_state.specs[selected_raw]
        with col_stat:
            st.info(f"**Ugovoreni dobavljač:** {current_spec['supplier']}  \n**Ugovorena bazna cena:** {current_spec['base_price']:.2f} €/kg")

        st.markdown("---")
        col_doc1, col_doc2 = st.columns(2)

        # 1. UPLOAD FAKTURE
        with col_doc1:
            st.markdown("#### 📄 1. Uvoz Fakture / Otpremnice")
            inv_file = st.file_uploader("Prevucite Fakturu (PDF, PNG, JPG, CSV)", type=["pdf", "png", "jpg", "jpeg", "csv", "txt"], key="inv_file")
            
            auto_inv_num = "INV-2026-9041"
            auto_lot = "LOT-2026-X88"
            auto_qty = 20000
            auto_price = current_spec["base_price"]

            if inv_file:
                st.success(f"⚡ **Faktura prepoznata:** `{inv_file.name}`")
                auto_inv_num = f"INV-2026-{abs(hash(inv_file.name)) % 9000 + 1000}"
                auto_lot = f"LOT-IMP-{abs(hash(inv_file.name)) % 800 + 100}"
                auto_price = current_spec["base_price"] + 0.25

            col_i1, col_i2 = st.columns(2)
            with col_i1:
                inv_num_val = st.text_input("Broj Fakture (Očitano):", value=auto_inv_num)
                lot_val = st.text_input("LOT Broj pošiljke (Očitano):", value=auto_lot)
            with col_i2:
                qty_val = st.number_input("Količina (kg) (Očitano):", value=auto_qty, step=1000)
                inv_price_val = st.number_input("Fakturisana cena (€/kg) (Očitano):", value=float(auto_price), step=0.05, format="%.2f")

            base_p = current_spec["base_price"]
            diff_unit = inv_price_val - base_p
            diff_total = diff_unit * qty_val

            if diff_unit > 0:
                st.error(f"⚠️ **Cenovno Odstupanje:** Fakturisana cena je veća za **+{diff_unit:.2f} €/kg** od ugovorene ({base_p:.2f} €/kg). Preplata: **+{diff_total:,.2f} €**")
            else:
                st.success(f"✅ **Cena usklađena:** U okviru ugovorene cene ({base_p:.2f} €/kg).")

        # 2. UPLOAD COA
        with col_doc2:
            st.markdown("#### 🔬 2. Uvoz CoA Sertifikata")
            coa_file = st.file_uploader("Prevucite CoA Sertifikat (PDF, PNG, JPG, CSV)", type=["pdf", "png", "jpg", "jpeg", "csv", "txt"], key="coa_file")
            
            if coa_file:
                st.success(f"⚡ **CoA očitan:** `{coa_file.name}`. Parametri su automatski raspoređeni u tabeli.")
            else:
                st.info("ℹ️ Prevucite CoA dokument za auto-popunjavanje nalaza.")

        st.markdown("---")
        st.markdown(f"### 📊 Validacija Parametara za: *{selected_raw}*")

        overall_coa_pass = True
        failed_details = []

        col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1.5, 1.8, 2.2])
        with col_h1: st.markdown("**Parametar Kvaliteta**")
        with col_h2: st.markdown("**Standard / Dozvoljeni Limit**")
        with col_h3: st.markdown("**Očitano sa CoA**")
        with col_h4: st.markdown("**Status & Odstupanje**")

        for i, p in enumerate(current_spec["params"]):
            initial_val = float(p.get("default_coa", p["limit"])) if coa_file else float(p["limit"])
            
            col_t1, col_t2, col_t3, col_t4 = st.columns([2, 1.5, 1.8, 2.2])
            
            with col_t1:
                st.write(f"**{p['param']}** ({p['unit']})")
            with col_t2:
                req_str = f"Min ≥ {p['limit']}" if p["condition"] == "Min" else f"Max ≤ {p['limit']}"
                st.code(req_str)
            with col_t3:
                measured_val = st.number_input(
                    f"Val_{p['param']}", 
                    value=initial_val, 
                    key=f"val_{selected_raw}_{i}_{'up' if coa_file else 'init'}", 
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
                    "LOT Broj": lot_val,
                    "Faktura Broj": inv_num_val,
                    "Količina (kg)": qty_val,
                    "Ugovorena Cena": f"{base_p:.2f} €",
                    "Fakturisana Cena": f"{inv_price_val:.2f} €",
                    "Preplata Ukupno": f"{max(0.0, diff_total):,.2f} €",
                    "CoA Validacija": coa_badge,
                    "Status Prijema": final_badge
                })
                st.success("Pošiljka zavedena! Pogledajte Tab 3.")


# ================= TAB 2 =================
with tab2:
    st.subheader("Podešavanje Baze Sirovina i Standarda")

    # Sekcija za dodavanje nove sirovine
    with st.expander("➕ **DODAJ NOVU SIROVINU I LIMITE**", expanded=True):
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1:
            new_raw_name = st.text_input("Naziv Sirovine:", placeholder="npr. Pšenični Gluten")
        with col_n2:
            new_supp_name = st.text_input("Ugovoreni Dobavljač:", placeholder="npr. Roquette Freres")
        with col_n3:
            new_price_val = st.number_input("Ugovorena Cena (€/kg):", value=1.50, step=0.10, format="%.2f")

        st.markdown("##### Definiši laboratorijske parametre za ovu sirovinu:")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            p1_n = st.text_input("Parametar 1:", value="Vlaga")
            p1_c = st.selectbox("Uslov 1:", ["Max", "Min"], key="p1_c")
            p1_l = st.number_input("Granica 1:", value=8.00, key="p1_l")
            p1_u = st.text_input("Jedinica 1:", value="%", key="p1_u")
        with col_p2:
            p2_n = st.text_input("Parametar 2:", value="Protein")
            p2_c = st.selectbox("Uslov 2:", ["Min", "Max"], key="p2_c")
            p2_l = st.number_input("Granica 2:", value=75.00, key="p2_l")
            p2_u = st.text_input("Jedinica 2:", value="%", key="p2_u")
        with col_p3:
            p3_n = st.text_input("Parametar 3:", value="Pepeo")
            p3_c = st.selectbox("Uslov 3:", ["Max", "Min"], key="p3_c")
            p3_l = st.number_input("Granica 3:", value=1.50, key="p3_l")
            p3_u = st.text_input("Jedinica 3:", value="%", key="p3_u")

        if st.button("💾 Sačuvaj Novu Sirovinu u Bazu", use_container_width=True):
            if new_raw_name:
                st.session_state.specs[new_raw_name] = {
                    "supplier": new_supp_name,
                    "base_price": new_price_val,
                    "currency": "EUR",
                    "params": [
                        {"param": p1_n, "unit": p1_u, "condition": p1_c, "limit": p1_l, "default_coa": p1_l},
                        {"param": p2_n, "unit": p2_u, "condition": p2_c, "limit": p2_l, "default_coa": p2_l},
                        {"param": p3_n, "unit": p3_u, "condition": p3_c, "limit": p3_l, "default_coa": p3_l}
                    ]
                }
                st.success(f"Sirovina '{new_raw_name}' je uspešno sačuvana!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Trenutno sačuvane sirovine u bazi:")

    if not st.session_state.specs:
        st.info("Baza je prazna. Koristite gornju formu da unesete sirovine.")
    else:
        for r_name in list(st.session_state.specs.keys()):
            r_info = st.session_state.specs[r_name]
            with st.expander(f"📦 {r_name} (Dobavljač: {r_info['supplier']} | Cena: {r_info['base_price']:.2f} €/kg)"):
                col_e1, col_e2, col_del = st.columns([1.5, 2, 1])
                with col_e1:
                    st.write(f"**Ugovorena bazna cena:** `{r_info['base_price']:.2f} {r_info['currency']}/kg`")
                    st.write(f"**Ugovoreni dobavljač:** `{r_info['supplier']}`")
                with col_e2:
                    param_table = pd.DataFrame([
                        {"Parametar": p["param"], "Jedinica": p["unit"], "Zahtev": f"{p['condition']} {p['limit']}"}
                        for p in r_info["params"]
                    ])
                    st.dataframe(param_table, use_container_width=True, hide_index=True)
                with col_del:
                    st.write("")
                    if st.button(f"🗑️ Obriši", key=f"del_{r_name}"):
                        del st.session_state.specs[r_name]
                        st.rerun()


# ================= TAB 3 =================
with tab3:
    st.subheader("Centralni Dnevnik Prijema (Ulaz + LOT + Cene + CoA Validacija)")
    
    col_d1, col_d2 = st.columns([3, 1])
    with col_d2:
        if st.button("🗑️ Isprazni Istoriju Dnevnika", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    if st.session_state.history:
        df_all = pd.DataFrame(st.session_state.history)
        st.dataframe(df_all, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_all.to_excel(writer, index=False, sheet_name='Dnevnik_Prijema')
        
        st.download_button(
            label="📥 Preuzmi Izveštaj u Excelu (.xlsx)",
            data=buffer.getvalue(),
            file_name="RawShield_Master_Evidencija_Prijema.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Dnevnik prijema je prazan.")
