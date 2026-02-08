import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# --- UI CONFIGURATION ---
st.set_page_config(page_title="分貨助手", layout="wide")

# Custom CSS for Mobile Optimization
st.markdown("""
    <style>
    /* Sticky Header for Store Name */
    .sticky-header {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        background-color: #1E1E1E;
        color: white;
        z-index: 999;
        padding: 15px;
        font-size: 32px !important;
        font-weight: bold;
        text-align: center;
        border-radius: 0 0 15px 15px;
        margin-bottom: 20px;
    }
    /* Large Text for Items */
    .item-card {
        background-color: #f0f2f6;
        padding: 5px;
        border-radius: 10px;
        margin-bottom: 5px;
        //border-left: 10px solid #FF4B4B;
    }
    .item-name { font-size: 22px; line-height: 1.2; font-weight: 500; color: #31333F; }
    .item-qty { font-size: 22px; line-height: 1.2; font-weight: bold; color: #FF4B4B; float: right; }
    </style>
    """, unsafe_allow_html=True)

# --- SCRAPER ENGINE ---
def get_data():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Point directly to the Chromium binary installed by packages.txt
    options.binary_location = "/usr/bin/chromium"
    
    # On Streamlit Cloud, we don't use ChromeDriverManager. 
    # The driver is already in the system path.
    driver = webdriver.Chrome(options=options)
    
    url = "https://script.google.com/macros/s/AKfycbysTgeywSBruJEElJ2Wm-FJaWW6ciHOsC3vhInFFRB2QoiBjTwr9BkCFaWWGwdtlEA4/exec"
    
    results = []
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        # Navigate nested iframes
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "sandboxFrame")))
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "userHtmlFrame")))
        # Wait for data
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "shop")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        shops = soup.find_all('section', class_='shop')
        
        for shop in shops:
            shop_name = shop.find('h2').text.split('：')[0] # Get name before the colon
            lines = shop.find_all('div', class_='line')
            for line in lines:
                if "—" in line.text:
                    item, qty = line.text.split("—")
                    results.append({"Shop": shop_name.strip(), "Item": item.strip(), "Qty": qty.strip()})
        return results
    finally:
        driver.quit()

# --- APP INTERFACE ---
st.title("🥬 分貨清單助手 v1.0")

if st.button('🔄 更新最新數據', use_container_width=True):
    with st.spinner('正在從 Google 抓取數據...'):
        data = get_data()
        st.session_state['data'] = data
        st.success('更新成功！')

if 'data' in st.session_state:
    df = pd.DataFrame(st.session_state['data'])
    shop_list = list(df['Shop'].unique())
    total_shops = len(shop_list)
    
    # Initialize shop index if not present
    if 'shop_index' not in st.session_state:
        st.session_state.shop_index = 0

    # --- 1. Progress Bar ---
    # Progress is a float between 0.0 and 1.0
    progress_value = (st.session_state.shop_index + 1) / total_shops
    st.progress(progress_value)
    st.caption(f"進度：第 {st.session_state.shop_index + 1} 家 / 共 {total_shops} 家")

    # --- 2. Navigation Row (Selectbox on Left, Buttons on Right) ---
    # Col 1 is 3 parts wide, Col 2 and 3 are 1 part wide each
    col_select, col_prev, col_next = st.columns([3, 1, 1])

    with col_select:
        # User can still manually pick a shop
        selected_shop = st.selectbox(
            "選擇店鋪：", 
            shop_list, 
            index=st.session_state.shop_index,
            label_visibility="collapsed"
        )
        # Sync index if manually changed
        st.session_state.shop_index = shop_list.index(selected_shop)

    with col_prev:
        if st.button("⬅️", use_container_width=True):
            st.session_state.shop_index = (st.session_state.shop_index - 1) % total_shops
            st.rerun() # Refresh to update progress bar and selectbox immediately

    with col_next:
        if st.button("➡️", use_container_width=True):
            st.session_state.shop_index = (st.session_state.shop_index + 1) % total_shops
            st.rerun()

    # --- 3. Display Content ---
    # Sticky Store Name
    st.markdown(f'<div class="sticky-header">{selected_shop}</div>', unsafe_allow_html=True)
    
    # Show Items for Selected Shop
    items = df[df['Shop'] == selected_shop]
    for _, row in items.iterrows():
        st.markdown(f"""
            <div class="item-card">
                <span class="item-qty">{row['Qty']}</span>
                <div class="item-name">{row['Item']}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("請點擊上方按鈕開始抓取數據。")
