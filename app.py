import streamlit as st
import pandas as pd
from PIL import Image, ImageEnhance
import pytesseract
import re

# ==========================================
# 1. ตั้งค่าหน้าเพจ 
# ==========================================
st.set_page_config(page_title="SkinScan AI", page_icon="woman_5362023.png", layout="wide")

# ==========================================
# 2. โหลดฐานข้อมูล
# ==========================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('database.csv')
        df['ingredient'] = df['ingredient'].astype(str).str.lower()
        return df
    except FileNotFoundError:
        st.error("❌ ไม่พบไฟล์ 'database.csv'")
        return pd.DataFrame()

df_db = load_data()

# ==========================================
# 3. ฟังก์ชันวิเคราะห์ส่วนผสม (อัปเดตระบบ Synonyms)
# ==========================================
def analyze_ingredients(extracted_text, df):
    # คลีนข้อความ
    text_clean = extracted_text.replace('\n', ' ')
    text_clean = re.sub(r'[^\w\s\-/]', ' ', text_clean.lower())
    
    # ดิกชันนารีคำพ้องความหมาย (เพิ่มคำศัพท์ในนี้ได้เลย)
    synonyms = {
        "aqua": "water",
        "fragrance": "parfum",
        "perfume": "parfum",
        "aloe vera": "aloe barbadensis leaf extract",
        "snail extract": "snail secretion filtrate",
        "vitamin b3": "niacinamide",
        "vitamin e": "tocopherol"
    }
    
    # แปลงคำพ้องในข้อความที่สแกนได้ให้ตรงกับฐานข้อมูล
    for word, replacement in synonyms.items():
        # ใช้ regex เพื่อป้องกันการแทนที่คำที่ซ้อนทับกัน
        text_clean = re.sub(fr'\b{word}\b', replacement, text_clean)
        
    found_ingredients = []
    
    for index, row in df.iterrows():
        ing_name = str(row['ingredient']).strip().lower()
        if ing_name in text_clean:
            found_ingredients.append({
                'Ingredient': ing_name.title(),
                'Function': row['function'],
                'Risk': row['risk_level']
            })
            
    # ลบข้อมูลที่ซ้ำซ้อนกรณีชื่อสารสกัดทับซ้อนกัน
    if found_ingredients:
        result_df = pd.DataFrame(found_ingredients)
        result_df = result_df.drop_duplicates(subset=['Ingredient'])
        return result_df
    else:
        return pd.DataFrame()

# ==========================================
# 4. หน้าจอหลัก (UI)
# ==========================================
col_icon, col_title = st.columns([1, 9])
with col_icon:
    st.image("woman_5362023.png", width=65)
with col_title:
    st.title("SkinScan AI")

st.markdown("**ระบบสแกนส่วนผสมเครื่องสำอางและสกินแคร์อัจฉริยะ**")

# --- เพิ่มระบบให้เลือก 2 แท็บ (ถ่ายรูปสด / อัปโหลดรูป) ---
tab1, tab2 = st.tabs(["📸 ถ่ายรูปจากกล้อง", "📂 อัปโหลดรูปภาพ"])

with tab1:
    st.info("""
    💡 **วิธีใช้งานกล้อง:**
    1. อนุญาตให้เว็บเข้าถึงกล้อง
    2. ถ่ายรูปสลากส่วนผสมให้ชัดเจน
    3. รอ AI ประมวลผล
    """)
    camera_file = st.camera_input("ถ่ายรูปสลากผลิตภัณฑ์ให้ชัดเจน")
    
with tab2:
    st.info("""
    💡 **วิธีอัปโหลดรูป:**
    1. ถ่ายรูปหรือครอปรูปส่วนผสมเตรียมไว้
    2. กดปุ่ม Browse files ด้านล่าง
    3. รอ AI ประมวลผล
    """)
    uploaded_file = st.file_uploader("เลือกรูปภาพ...", type=['jpg', 'jpeg', 'png'])

# ดึงไฟล์ภาพมาใช้
img_file = camera_file if camera_file is not None else uploaded_file

if img_file is not None:
    # แบ่งหน้าจอเป็น 2 ฝั่ง (ซ้าย: รูป / ขวา: ผลลัพธ์)
    col_img, col_res = st.columns([1, 2])
    
    with col_img:
        image = Image.open(img_file)
        st.image(image, caption='ภาพสลากที่กำลังตรวจสอบ', use_container_width=True)
        
    with col_res:
        with st.spinner('🤖 AI กำลังปรับภาพและกวาดสายตาอ่านข้อความ...'):
            try:
                # --- พัฒนาระบบ AI ปรับแต่งภาพ ---
                gray_img = image.convert('L')
                enhancer_contrast = ImageEnhance.Contrast(gray_img)
                processed_img = enhancer_contrast.enhance(1.5)
                
                with st.expander("👁️ ดูมุมมองภาพจำลองที่ AI ใช้สแกนข้อความ"):
                    st.image(processed_img, caption='ภาพปรับสีเทาเพื่อการอ่าน', use_container_width=True)

                # ดึงข้อความดิบจากภาพ
                extracted_text = pytesseract.image_to_string(processed_img)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่านภาพ: {e}")
                extracted_text = ""
                
        if extracted_text.strip() == "":
            st.error("⚠️ ไม่พบตัวอักษร AI อ่านข้อความไม่ได้ แนะนำให้ถ่ายให้โฟกัสชัดเจนขึ้นค่ะ")
        else:
            # --- เพิ่มกล่อง Form ให้ผู้ใช้แก้ไขคำผิดก่อนวิเคราะห์ ---
            with st.form("edit_form"):
                st.markdown("### 📝 ตรวจสอบและแก้ไขคำผิด")
                st.caption("💡 ทริค: แสงสะท้อนอาจทำให้ AI อ่านคำเพี้ยนไป (เช่นตัว l กลายเป็น i) สามารถเช็กและพิมพ์แก้ข้อความในกล่องนี้ให้ถูกต้องก่อนได้ค่ะ")
                
                edited_text = st.text_area("ข้อความที่ AI กวาดสายตาได้:", value=extracted_text, height=200)
                
                # ปุ่มกดเพื่อเริ่มวิเคราะห์ (จะทำงานก็ต่อเมื่อกดปุ่มนี้)
                submit_button = st.form_submit_button("🔍 วิเคราะห์ส่วนผสม", type="primary")
            
            # เมื่อกดปุ่มวิเคราะห์
            if submit_button:
                result_df = analyze_ingredients(edited_text, df_db)
                
                if result_df.empty:
                    st.warning("สแกนพบข้อความ แต่ไม่พบสารที่ตรงกับฐานข้อมูล")
                else:
                    st.success(f"✅ ตรวจพบสารสำคัญที่รู้จัก {len(result_df)} ชนิด")
                    
                    # --- แยกระดับความเสี่ยงเป็น 3 คอลัมน์ ---
                    safe_df = result_df[result_df['Risk'] == 'Safe']
                    warn_df = result_df[result_df['Risk'] == 'Warning']
                    danger_df = result_df[result_df['Risk'] == 'Danger']
                    
                    c1, c2, c3 = st.columns(3)
                    
                    with c1:
                        st.info(f"🟢 **ปลอดภัย ({len(safe_df)})**")
                        for _, row in safe_df.iterrows():
                            st.write(f"- **{row['Ingredient']}**<br><small>{row['Function']}</small>", unsafe_allow_html=True)
                            
                    with c2:
                        st.warning(f"🟡 **เฝ้าระวัง ({len(warn_df)})**")
                        for _, row in warn_df.iterrows():
                            st.write(f"- **{row['Ingredient']}**<br><small>{row['Function']}</small>", unsafe_allow_html=True)
                            
                    with c3:
                        st.error(f"🔴 **อันตราย ({len(danger_df)})**")
                        for _, row in danger_df.iterrows():
                            st.write(f"- **{row['Ingredient']}**<br><small>{row['Function']}</small>", unsafe_allow_html=True)

st.markdown("---")
st.caption("📝 **หมายเหตุ:** ระบบวิเคราะห์ข้อมูลอ้างอิงจากฐานข้อมูลเท่านั้น หากมีอาการแพ้ควรปรึกษาแพทย์ทันที")
