import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="RawShield Pro - Quality & Invoice Intake", layout="wide", page_icon="🛡️")

# Inicijalizacija baze u sesiji
if "specs" not in st.session_state:
    st.session_state.specs = {
        "Whey Protein Concentrate 80 (WPC 80)": {
            "supplier": "EuroDairy Ingredients GmbH",
            "base_price": 4.50,
            "params": {
                "Sirovi Protein (%)": {"min": 80.0, "max": 100.0, "type": "min"},
                "Vlaga (%)": {"min": 0.0, "max": 5.0, "type": "max"},
                "Mlečne Masti (%)": {"min": 0.0, "max": 6.0, "type": "max"},
                "Olovo - Pb (mg/kg)": {"min": 0.0, "max": 0.05, "type": "max"},
                "Aflatoksin M1 (µg/kg)": {"min": 0.0, "max": 0.05, "type": "max"}
            }
        },
        "Sojin Lecitin Tečni": {
            "supplier": "Cargill B.V.",
            "base_price": 1.85,
            "params": {
                "Čistoća / Fosfatidi (%)": {"min": 60.0, "max": 100.0, "type": "min"},
                "Vlaga (%)": {"min": 0.0, "max": 1.0, "type": "max"},
                "Kiselinski broj (mg KOH/g)": {"min": 0.0, "max": 30.0, "type": "max"}
            }
        }
    }

if "history" not in st.session_state:
    st.session_state.history = [
        {
            "Datum": "23.08.2026",
            "Sirovina": "Whey Protein Concentrate 80 (WPC 80)",
            "Dobavljač": "EuroDairy Ingredients GmbH",
            "LOT Broj": "LOT-NL-2026-991",
            "Faktura": "INV-8819",
            "Količina (kg)": 24000,
            "Ugovorena Cena (€/kg)": 4.50,
            "Fakturisana Cena (€/kg)": 4.75,
            "Cenovna Razlika (€)": 6000.00,
            "CoA Status": "FAIL (Olovo Pb: 0.14 mg/kg)",
            "Konačni Status": "⛔ BLOKIRANO / KONTAMINACIJA"
        },
        {
            "Datum": "21.08.2026",
            "Sirovina": "Sojin Lecitin Tečni",
            "Dobavljač": "Cargill B.V.",
            "LOT Broj": "LOT-CG-108",
            "Faktura": "RN-1148",
            "Količina (kg)": 5000,
            "Ugovorena Cena (€/kg)": 1.85,
            "Fakturisana Cena (€/kg)": 1.85,
            "Cenovna Razlika (€)": 0.00,
            "CoA Status": "PASS (Sve u normi)",
            "Konačni Status": "✅ ODOBRENO ZA PRIJEM"
        }
    ]

st.title("🛡️ RawShield Pro — Modul za Prijem Sirovine, CoA & Faktura")
st.caption("Interni standardi kvaliteta | Automatsko poređenje nalaza | Detekcija preplata | Excel evidencija")

tab1, tab2, tab3 = st.tabs([
    "📥 1. Validacija Novog Prijema (CoA + Faktura)",
    "⚙️ 2. Moje Sirovine & Podešavanje Dozvoljenih Limita",
    "📊 3. Centralni Dnevnik Ulaza & Excel Export"
])

# --- TAB 1: VALIDACIJA PRIJEMA ---
with tab1:
    st.subheader("Prijem Pošiljke na Uvid i Provera Pre Istovara")
    col_l, col_r = st.columns([1, 1.2])

    with col_l:
        st.markdown("##### 1. Osnovni Podaci o Pošiljci")
        raw_options = list(st.session_state.specs.keys())
        selected_raw = st.selectbox("Izaberi sirovinu sa stanja:", raw_options)
        
        raw_data = st.session_state.specs[selected_raw]
        supplier = st.text_input("Dobavljač:", value=raw_data["supplier"])
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            invoice_num = st.text_input("Broj Fakture / Otpremnice:", value="INV-2026-9041")
            lot_num = st.text_input("LOT Broj pošiljke:", value="LOT-2026-X88")
        with col_f2:
            qty = st.number_input("Količina (kg):", value=10000, step=1000)
            inv_price = st.number_input("Fakturisana cena (€/kg):", value=raw_data["base_price"], step=0.05, format="%.2f")

        base_price = raw_data["base_price"]
        price_diff = (inv_price - base_price) * qty

        if inv_price > base_price:
            st.error(f"⚠️ UPOZORENJE O PREPLATI: Fakturisana cena ({inv_price:.2f} €) je veća od ugovorene ({base_price:.2f} €). Preplata: +{price_diff:,.2f} €")
        else:
            st.success(f"✅ Cenovna usklađenost: Cena odgovara ugovorenoj ({base_price:.2f} €/kg).")

    with col_r:
        st.markdown("##### 2. Laboratorijski Nalaz (CoA) vs. Vaši Zadati Standardi")
        st.info("Unesite očitane parametre sa CoA sertifikata koji je poslao dobavljač:")

        coa_results = {}
        all_passed = True
        failed_params = []

        for p_name, p_rule in raw_data["params"].items():
            col_p1, col_p2 = st.columns([1.2, 1])
            with col_p1:
                limit_label = f"Min ≥ {p_rule['min']}" if p_rule["type"] == "min" else f"Max ≤ {p_rule['max']}"
                st.write(f"**{p_name}** *(Standard: {limit_label})*")
            with col_p2:
                val = st.number_input(f"Očitano ({p_name}):", value=float(p_rule["min"] if p_rule["type"]=="min" else p_rule["max"]), key=f"inp_{p_name}", format="%.3f")
                coa_results[p_name] = val
                
                # Provera usklađenosti
                if p_rule["type"] == "min" and val < p_rule["min"]:
                    all_passed = False
                    failed_params.append(f"{p_name} ({val} < min {p_rule['min']})")
                elif p_rule["type"] == "max" and val > p_rule["max"]:
                    all_passed = False
                    failed_params.append(f"{p_name} ({val} > max {p_rule['max']})")

        st.divider()
        if all_passed and inv_price <= base_price:
            st.success("🟢 STATUS: ODOBRENO ZA PRIJEM I PLAĆANJE (Svi parametri i cene su u normi)")
            final_status = "✅ ODOBRENO ZA PRIJEM"
            coa_summary = "PASS (Sve u normi)"
        elif not all_passed:
            st.error(f"⛔ STATUS: QUARANTINE / OBUSTAVA PRIJEMA (Neusaglašenost: {', '.join(failed_params)})")
            final_status = "⛔ BLOKIRANO / ODSUPANJE KVALITETA"
            coa_summary = f"FAIL ({', '.join(failed_params)})"
        else:
            st.warning("⚠️ STATUS: KVALITET ISPRAVAN / CENOVNO ODSTUPANJE")
            final_status = "⚠️ CENOVNO ODSTUPANJE"
            coa_summary = "PASS (Sve u normi)"

        if st.button("💾 Sačuvaj Pošiljku u Centralni Dnevnik"):
            new_entry = {
                "Datum": "23.08.2026",
                "Sirovina": selected_raw,
                "Dobavljač": supplier,
                "LOT Broj": lot_num,
                "Faktura": invoice_num,
                "Količina (kg)": qty,
                "Ugovorena Cena (€/kg)": base_price,
                "Fakturisana Cena (€/kg)": inv_price,
                "Cenovna Razlika (€)": max(0.0, price_diff),
                "CoA Status": coa_summary,
                "Konačni Status": final_status
            }
            st.session_state.history.insert(0, new_entry)
            st.success("Pošiljka je uspešno zavedena u centralni registar!")

# --- TAB 2: PODEŠAVANJE SIROVINA I PARAMETARA ---
with tab2:
    st.subheader("Konfiguracija Sirovine i Dozvoljenih Granica")
    st.write("Ovde kompanija samostalno unosi svoje sirovine, definisane parametre i cene.")

    with st.expander("➕ Dodaj Novu Sirovinu u Standard", expanded=False):
        new_name = st.text_input("Naziv nove sirovine:")
        new_supp = st.text_input("Podrazumevani dobavljač:")
        new_price = st.number_input("Ugovorena bazna cena (€/kg):", value=1.00, step=0.10)
        
        st.write("**Definiši osnovne parametre:**")
        p1_name = st.text_input("Naziv Parametra 1 (npr. Vlaga %):", value="Vlaga (%)")
        p1_type = st.selectbox("Tip ograničenja:", ["Maksimalno dozvoljeno (Max ≤)", "Minimalno zahtevano (Min ≥)"])
        p1_limit = st.number_input("Granična vrednost:", value=5.0)

        if st.button("Sačuvaj Sirovinu u Bazu"):
            if new_name:
                st.session_state.specs[new_name] = {
                    "supplier": new_supp,
                    "base_price": new_price,
                    "params": {
                        p1_name: {
                            "min": 0.0 if "Max" in p1_type else p1_limit,
                            "max": p1_limit if "Max" in p1_type else 1000.0,
                            "type": "max" if "Max" in p1_type else "min"
                        }
                    }
                }
                st.success(f"Sirovina '{new_name}' je uspešno konfigurisana!")

    st.markdown("##### Pregled Trenutno Podešenih Standarda:")
    for raw, details in st.session_state.specs.items():
        with st.container():
            st.markdown(f"**📦 {raw}** | Ugovoreni dobavljač: *{details['supplier']}* | Bazna cena: *{details['base_price']:.2f} €/kg*")
            param_df = pd.DataFrame([
                {"Parametar": p, "Zahtev": f"Min ≥ {r['min']}" if r['type']=='min' else f"Max ≤ {r['max']}"}
                for p, r in details["params"].items()
            ])
            st.dataframe(param_df, use_container_width=True, hide_index=True)
            st.divider()

# --- TAB 3: CENTRALNI DNEVNIK & EXCEL ---
with tab3:
    st.subheader("Digitalna Baza Pošiljki i Izvoz Izveštaja")
    df_history = pd.DataFrame(st.session_state.history)
    
    st.dataframe(df_history, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_history.to_excel(writer, index=False, sheet_name='Dnevnik_Ulaza_Sirovine')
    
    excel_bytes = buffer.getvalue()

    st.download_button(
        label="📥 Preuzmi Kompletan Dnevnik u Excelu (.xlsx)",
        data=excel_bytes,
        file_name="RawShield_Dnevnik_Ulaza_Sirovina.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

