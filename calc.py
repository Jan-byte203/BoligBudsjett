import streamlit as st
import pandas as pd
import re
from urllib.parse import urlparse, parse_qs
import plotly.express as px
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import json

# Page configuration
st.set_page_config(
    page_title="BoligBudsjett | Oppussingskalkulator",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS to match Solgt.no style
st.markdown("""
    <style>
    /* Global styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container */
    .main {
        background-color: #f8fafc;
        padding: 1rem 2rem;
    }
    
    /* Header styling */
    h1 {
        color: #0f172a;
        font-weight: 700;
        font-size: 1.875rem;
    }
    
    h2, h3 {
        color: #1e293b;
        font-weight: 600;
    }
    
    /* Card styling */
    .stMetric, div.css-1r6slb0 {
        background-color: white;
        padding: 1.25rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
    }
    
    /* Metric values */
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 600;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #1d4ed8;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        color: #64748b;
    }
    
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #2563eb;
    }
    
    /* Inputs */
    .stNumberInput input, .stTextInput input {
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: white;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
    }
    
    /* Charts */
    .js-plotly-plot {
        border-radius: 0.75rem;
        background-color: white;
        padding: 1rem;
        border: 1px solid #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)

# Add navigation tabs like Solgt.no
tabs = st.tabs([
    "🏠 Oversikt",
    "💰 Oppussing",
    "📊 Finansiering",
    "📍 Område"
])

# First, add these constants at the top of the file after imports
RENOVATION_COSTS = {
    "Overflater": {
        "Maling av vegger": {
            "Budget": 200,
            "Standard": 300,
            "Premium": 400,
            "unit": "m²",
            "description": "Inkluderer sparkling, grunning og to strøk maling"
        },
        "Nytt gulv": {
            "Budget": 800,
            "Standard": 1200,
            "Premium": 2000,
            "unit": "m²",
            "description": "Inkluderer riving av eksisterende gulv og legging av nytt"
        }
    },
    "Våtrom": {
        "Nytt bad": {
            "Budget": 15000,
            "Standard": 25000,
            "Premium": 40000,
            "unit": "m²",
            "description": "Komplett rehabilitering inkl. membran, fliser og sanitærutstyr"
        }
    },
    "Kjøkken": {
        "Nytt kjøkken": {
            "Budget": 8000,
            "Standard": 15000,
            "Premium": 30000,
            "unit": "m²",
            "description": "Inkluderer skap, benkeplate og montering (eks. hvitevarer)"
        }
    },
    "Teknisk": {
        "Ny elektrisk": {
            "Budget": 800,
            "Standard": 1000,
            "Premium": 1500,
            "unit": "m²",
            "description": "Oppgradering av elektrisk anlegg"
        },
        "Ny ventilasjon": {
            "Budget": 1500,
            "Standard": 2000,
            "Premium": 3000,
            "unit": "m²",
            "description": "Balansert ventilasjon med varmegjenvinning"
        }
    },
    "Annet": {
        "Nye vinduer": {
            "Budget": 6000,
            "Standard": 8000,
            "Premium": 12000,
            "unit": "stk",
            "description": "Pris per vindu inkl. montering"
        },
        "Nye dører": {
            "Budget": 3000,
            "Standard": 5000,
            "Premium": 8000,
            "unit": "stk",
            "description": "Pris per dør inkl. montering"
        }
    }
}

def get_finn_data(url):
    """Fetch and parse data from Finn.no listing"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'nb-NO,nb;q=0.9,no-NO;q=0.8,no;q=0.6,en-US;q=0.5,en;q=0.4',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize property data with all fields
        property_data = {
            'price': None,
            'size': None,
            'rooms': None,
            'bedrooms': None,
            'year_built': None,
            'address': None,
            'property_type': None,
            'floor': None,
            'total_price': None,
            'shared_debt': None,
            'ownership_type': None,
            'bra_total': None,
            'bra_primary': None,
            'bra_external': None,
            'balcony_size': None,
            'energy_rating': None,
            'plot_size': None,
            'bra_internal': None,
        }

        # Find all key-value pairs in the listing
        key_value_pairs = soup.find_all(['dt', 'dd'])
        
        current_key = None
        for elem in key_value_pairs:
            if elem.name == 'dt':
                current_key = elem.text.strip().lower()
            elif elem.name == 'dd' and current_key:
                value_text = elem.text.strip()
                
                # Match different data types based on the key
                if 'totalpris' in current_key:
                    property_data['total_price'] = int(''.join(filter(str.isdigit, value_text)))
                elif 'prisantydning' in current_key:
                    property_data['price'] = int(''.join(filter(str.isdigit, value_text)))
                elif 'fellesgjeld' in current_key:
                    property_data['shared_debt'] = int(''.join(filter(str.isdigit, value_text)))
                elif 'bruksareal' in current_key:
                    # Check for internal area first
                    internal_match = re.search(r'(\d+)\s*m²\s*\(BRA-i\)', value_text)
                    if internal_match:
                        property_data['bra_internal'] = float(internal_match.group(1))
                    # Then check for total area if no internal area was found
                    elif 'primær' not in current_key:
                        match = re.search(r'(\d+)\s*m²', value_text)
                        if match:
                            property_data['bra_total'] = float(match.group(1))
                elif 'primærrom' in current_key or 'p-rom' in current_key:
                    match = re.search(r'(\d+)\s*m²', value_text)
                    if match:
                        property_data['size'] = float(match.group(1))
                elif 'byggeår' in current_key:
                    try:
                        property_data['year_built'] = int(''.join(filter(str.isdigit, value_text)))
                    except ValueError:
                        pass
                elif 'boligtype' in current_key:
                    property_data['property_type'] = value_text
                elif 'eieform' in current_key:
                    property_data['ownership_type'] = value_text
                elif 'etasje' in current_key:
                    try:
                        property_data['floor'] = int(''.join(filter(str.isdigit, value_text)))
                    except ValueError:
                        pass
                elif 'soverom' in current_key:
                    try:
                        property_data['bedrooms'] = int(''.join(filter(str.isdigit, value_text)))
                    except ValueError:
                        pass
                elif 'rom' in current_key and 'sove' not in current_key:
                    try:
                        property_data['rooms'] = int(value_text.split()[0])
                    except (ValueError, IndexError):
                        pass
                elif 'balkong' in current_key or 'terrasse' in current_key:
                    match = re.search(r'(\d+)\s*m²', value_text)
                    if match:
                        property_data['balcony_size'] = float(match.group(1))
                elif 'energimerking' in current_key:
                    property_data['energy_rating'] = value_text
                elif 'tomteareal' in current_key:
                    match = re.search(r'(\d+)\s*m²', value_text)
                    if match:
                        property_data['plot_size'] = float(match.group(1))

        # Get address from breadcrumb or title
        address_elem = soup.find('h1', {'class': 'u-t3'}) or soup.find('h1')
        if address_elem:
            property_data['address'] = address_elem.text.strip()
        
        return property_data, True, "Data hentet successfully"
        
    except requests.RequestException as e:
        return None, False, f"Nettverksfeil: {str(e)}"
    except Exception as e:
        return None, False, f"Feil ved henting av data: {str(e)}"

with tabs[0]:
    # Property overview section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.title("Oppussingskalkulator")
        finn_url = st.text_input(
            "Finn.no annonse URL",
            placeholder="https://www.finn.no/realestate/homes/ad.html?finnkode=..."
        )
    
    with col2:
        if st.button("Hent boligdata", type="primary"):
            if finn_url:
                with st.spinner("Henter data fra Finn.no..."):
                    property_data, success, message = get_finn_data(finn_url)
                    
                    if success:
                        st.success("✅ Boligdata hentet")
                        # Store the data in session state
                        st.session_state.property_data = property_data
                    else:
                        st.error(f"❌ {message}")
            else:
                st.warning("⚠️ Vennligst lim inn en Finn.no URL")

    if finn_url and 'property_data' in st.session_state:
        st.markdown("### Boligdetaljer")
        col1, col2, col3, col4 = st.columns(4)
        
        data = st.session_state.property_data
        
        with col1:
            price = data['total_price'] or data['price'] or 0
            price_formatted = f"{price:,}".replace(",", " ")
            st.metric("Totalpris", f"{price_formatted} kr")
            
            if data['shared_debt']:
                st.caption(f"Inkl. fellesgjeld: {data['shared_debt']:,}".replace(",", " ") + " kr")
            if data['property_type']:
                st.caption(f"Type: {data['property_type']}")
        
        with col2:
            size = (data['bra_internal'] or 
                    data['size'] or 
                    data['bra_total'] or 0)
            st.metric("Areal", f"{size:.0f} m²" if size else "N/A")
            
            # Add area details in caption
            area_details = []
            if data['bra_internal']:
                area_details.append(f"BRA-i: {data['bra_internal']} m²")
            if data['bra_total']:
                area_details.append(f"BRA: {data['bra_total']} m²")
            if data['size']:
                area_details.append(f"P-ROM: {data['size']} m²")
            if area_details:
                st.caption(" | ".join(area_details))
            
            if data['rooms']:
                st.caption(f"{data['rooms']} rom ({data['bedrooms']} soverom)")
            if data['balcony_size']:
                st.caption(f"Balkong/terrasse: {data['balcony_size']} m²")
        
        with col3:
            year = data['year_built']
            st.metric("Byggeår", str(year) if year else "N/A")
            if data['floor']:
                st.caption(f"{data['floor']}. etasje")
            if data['energy_rating']:
                st.caption(f"Energimerking: {data['energy_rating']}")
        
        with col4:
            if price and size:
                price_per_sqm = int(price / size)
                price_per_sqm_formatted = f"{price_per_sqm:,}".replace(",", " ")
                st.metric("Pris/m²", f"{price_per_sqm_formatted} kr")
            if data['ownership_type']:
                st.caption(f"Eieform: {data['ownership_type']}")
            if data['plot_size']:
                st.caption(f"Tomt: {data['plot_size']} m²")

with tabs[1]:
    if 'property_data' in st.session_state:
        st.markdown("### 🔨 Oppussingsplan")
        data = st.session_state.property_data
        
        # Initialize or get renovation selections from session state
        if 'renovation_selections' not in st.session_state:
            st.session_state.renovation_selections = {}
        
        total_renovation_cost = 0
        total_area = data['bra_internal'] or data['size'] or data['bra_total'] or 0
        
        # Create two columns for the layout
        plan_col, summary_col = st.columns([2, 1])
        
        with plan_col:
            for category, items in RENOVATION_COSTS.items():
                with st.expander(f"📑 {category}", expanded=True):
                    for item_name, item_details in items.items():
                        st.markdown(f"**{item_name}**")
                        st.caption(item_details['description'])
                        
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col1:
                            needs_renovation = st.checkbox(
                                "Skal oppusses",
                                key=f"check_{item_name}",
                                help=f"Velg dette hvis {item_name.lower()} skal oppgraderes"
                            )
                        
                        if needs_renovation:
                            with col2:
                                quality = st.select_slider(
                                    "Kvalitetsnivå",
                                    options=["Budget", "Standard", "Premium"],
                                    value="Standard",
                                    key=f"quality_{item_name}"
                                )
                            
                            with col3:
                                if item_details['unit'] == "m²":
                                    area_percent = st.slider(
                                        "Andel (%)",
                                        0, 100, 100,
                                        key=f"area_{item_name}"
                                    )
                                    area = (total_area * area_percent / 100)
                                else:  # For items counted in pieces
                                    area = st.number_input(
                                        "Antall",
                                        1, 20, 1,
                                        key=f"count_{item_name}"
                                    )
                            
                            # Calculate cost for this item
                            unit_cost = item_details[quality]
                            total_item_cost = unit_cost * area
                            
                            # Store selection
                            st.session_state.renovation_selections[item_name] = {
                                "quality": quality,
                                "area": area,
                                "unit": item_details['unit'],
                                "unit_cost": unit_cost,
                                "total_cost": total_item_cost
                            }
                            
                            total_renovation_cost += total_item_cost
                        else:
                            # Remove from selections if unchecked
                            st.session_state.renovation_selections.pop(item_name, None)
        
        with summary_col:
            st.markdown("### 💰 Kostnadssammendrag")
            
            # Original property cost
            original_price = data['total_price'] or data['price'] or 0
            st.metric(
                "Kjøpspris",
                f"{original_price:,.0f} NOK",
                help="Total kjøpspris inkludert omkostninger"
            )
            
            # Renovation costs
            st.metric(
                "Oppussingskostnad",
                f"{total_renovation_cost:,.0f} NOK",
                delta=f"{total_renovation_cost/original_price:.1%} av kjøpspris"
            )
            
            # Total investment
            total_investment = original_price + total_renovation_cost
            st.metric(
                "Total investering",
                f"{total_investment:,.0f} NOK"
            )
            
            # Cost per m²
            if total_area > 0:
                original_sqm = original_price / total_area
                new_sqm = total_investment / total_area
                st.metric(
                    "Ny pris per m²",
                    f"{new_sqm:,.0f} NOK",
                    delta=f"{new_sqm - original_sqm:,.0f} NOK",
                    delta_color="inverse"
                )
            
            # Show detailed breakdown
            if st.session_state.renovation_selections:
                st.markdown("#### Spesifisert oversikt")
                for item_name, details in st.session_state.renovation_selections.items():
                    st.markdown(f"""
                    **{item_name}**
                    - Kvalitet: {details['quality']}
                    - Omfang: {details['area']:.1f} {details['unit']}
                    - Enhetspris: {details['unit_cost']:,} NOK/{details['unit']}
                    - Total: {details['total_cost']:,.0f} NOK
                    """)
            
            # Download report button
            if st.button("📥 Last ned kostnadsrapport"):
                # Create report content
                report = f"""
                Kostnadsrapport for {data['address']}
                
                Opprinnelig kjøpspris: {original_price:,.0f} NOK
                Oppussingskostnad: {total_renovation_cost:,.0f} NOK
                Total investering: {total_investment:,.0f} NOK
                
                Spesifisert oppussing:
                """
                for item_name, details in st.session_state.renovation_selections.items():
                    report += f"\n{item_name}:"
                    report += f"\n- Kvalitet: {details['quality']}"
                    report += f"\n- Omfang: {details['area']:.1f} {details['unit']}"
                    report += f"\n- Kostnad: {details['total_cost']:,.0f} NOK"
                
                # Convert to PDF or offer as text download
                st.download_button(
                    "Last ned rapport",
                    report,
                    file_name="kostnadsrapport.txt",
                    mime="text/plain"
                )

with tabs[2]:
    if 'property_data' in st.session_state:
        st.markdown("### 💳 Finansieringsplan")
        data = st.session_state.property_data
        
        # Get total investment cost from renovation tab
        total_investment = (data['total_price'] or data['price'] or 0)
        if 'renovation_selections' in st.session_state:
            total_investment += sum(item['total_cost'] for item in st.session_state.renovation_selections.values())
        
        col1, col2 = st.columns([1.5, 1])
        
        with col1:
            st.markdown("#### Lånekalkulator")
            
            # Loan details
            egenkapital_prosent = st.slider(
                "Egenkapital (%)",
                min_value=0,
                max_value=100,
                value=15,
                help="Minimum 15% egenkapital er vanlig krav fra banker"
            )
            
            egenkapital = total_investment * (egenkapital_prosent/100)
            loan_amount = total_investment - egenkapital
            
            col1, col2 = st.columns(2)
            with col1:
                interest_rate = st.number_input(
                    "Lånerente (%)",
                    value=4.5,
                    min_value=0.0,
                    max_value=15.0,
                    step=0.1,
                    help="Effektiv lånerente"
                )
            with col2:
                years = st.number_input(
                    "Nedbetalingstid (år)",
                    value=25,
                    min_value=1,
                    max_value=30
                )
            
            # Monthly costs
            st.markdown("#### Månedlige kostnader")
            
            # Calculate loan payment
            monthly_rate = interest_rate / (100 * 12)
            num_payments = years * 12
            monthly_loan = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
            
            # Additional monthly costs
            felleskostnader = st.number_input(
                "Felleskostnader",
                value=data.get('shared_costs', 2500),
                step=100,
                help="Månedlige felleskostnader"
            )
            
            kommunale_avg = st.number_input(
                "Kommunale avgifter",
                value=500,
                step=100,
                help="Månedlige kommunale avgifter"
            )
            
            forsikring = st.number_input(
                "Forsikring",
                value=300,
                step=100,
                help="Månedlig forsikringskostnad"
            )
            
            vedlikehold = st.number_input(
                "Vedlikeholdsavsetning",
                value=int(total_investment * 0.001),  # 0.1% of property value per month
                step=100,
                help="Anbefalt månedlig avsetning til vedlikehold"
            )
            
            strom = st.number_input(
                "Strøm/oppvarming (estimat)",
                value=1500,
                step=100,
                help="Estimerte månedlige strømkostnader"
            )
        
        with col2:
            st.markdown("#### 💰 Kostnadssammendrag")
            
            # Investment summary
            st.metric(
                "Total investering",
                f"{total_investment:,.0f} NOK"
            )
            
            st.metric(
                "Egenkapital",
                f"{egenkapital:,.0f} NOK",
                delta=f"{egenkapital_prosent}%"
            )
            
            st.metric(
                "Lånebeløp",
                f"{loan_amount:,.0f} NOK"
            )
            
            # Monthly summary
            total_monthly = (
                monthly_loan +
                felleskostnader +
                kommunale_avg +
                forsikring +
                vedlikehold +
                strom
            )
            
            st.markdown("#### 📅 Månedlige kostnader")
            
            # Create a DataFrame for monthly costs
            monthly_costs = pd.DataFrame([
                {"Kostnad": "Lån (renter + avdrag)", "Beløp": monthly_loan},
                {"Kostnad": "Felleskostnader", "Beløp": felleskostnader},
                {"Kostnad": "Kommunale avgifter", "Beløp": kommunale_avg},
                {"Kostnad": "Forsikring", "Beløp": forsikring},
                {"Kostnad": "Vedlikeholdsavsetning", "Beløp": vedlikehold},
                {"Kostnad": "Strøm/oppvarming", "Beløp": strom},
                {"Kostnad": "Totalt", "Beløp": total_monthly}
            ])
            
            # Display as a styled table
            st.markdown("""
            <style>
            .cost-table {
                font-size: 1.1em;
                width: 100%;
            }
            .cost-table tr:last-child {
                font-weight: bold;
                border-top: 2px solid #eee;
            }
            </style>
            """, unsafe_allow_html=True)
            
            for _, row in monthly_costs.iterrows():
                st.metric(
                    row['Kostnad'],
                    f"{row['Beløp']:,.0f} NOK/mnd"
                )
            
            # Annual summary
            st.markdown("#### 📊 Årlig oversikt")
            annual_cost = total_monthly * 12
            st.metric(
                "Årlige kostnader",
                f"{annual_cost:,.0f} NOK/år",
                help="Totale årlige kostnader for boligen"
            )
            
            # Tax deduction (estimate)
            tax_deduction = loan_amount * (interest_rate/100) * 0.22
            st.metric(
                "Skattefradrag (estimat)",
                f"{tax_deduction:,.0f} NOK/år",
                help="Estimert årlig skattefradrag for rentekostnader"
            )
            
            # Net annual cost after tax deduction
            st.metric(
                "Netto årlig kostnad",
                f"{(annual_cost - tax_deduction):,.0f} NOK/år",
                help="Årlige kostnader etter skattefradrag"
            )

with tabs[3]:
    if finn_url:
        # Area analysis like Solgt.no
        st.markdown("### Områdeanalyse")
        st.info("🔍 Viser sammenlignbare boliger i området")
        
        # Mock data for similar properties
        similar_properties = pd.DataFrame({
            "Adresse": ["Testveien 1", "Testveien 2", "Testveien 3"],
            "Pris": [4200000, 4100000, 4300000],
            "Størrelse": [70, 68, 72],
            "Pris/m²": [60000, 60294, 59722]
        })
        
        st.dataframe(
            similar_properties,
            use_container_width=True,
            hide_index=True
        )

# Footer similar to Solgt.no
st.markdown("---")
footer_cols = st.columns(4)
with footer_cols[0]:
    st.markdown("**BoligBudsjett**")
with footer_cols[1]:
    st.markdown("[Om oss](https://example.com)")
with footer_cols[2]:
    st.markdown("[Personvern](https://example.com)")
with footer_cols[3]:
    st.markdown("© 2024 BoligBudsjett")