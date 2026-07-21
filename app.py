import streamlit as st
import pandas as pd
from PIL import Image, ImageEnhance
import pytesseract
import re
import difflib # เพิ่มไลบรารีสำหรับเดาคำผิดอัตโนมัติ

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
        df['ingredient'] = df['ingredient'].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        st.error("❌ ไม่พบไฟล์ 'database.csv'")
        return pd.DataFrame()

df_db = load_data()

# ==========================================
# 3. ฟังก์ชันวิเคราะห์ส่วนผสม (อัปเดตระบบ AI เดาคำผิดอัตโนมัติ)
# ==========================================
def analyze_ingredients(extracted_text, df):
    # ดิกชันนารีคำพ้องความหมาย (Synonyms)
    synonyms = {
        "aqua": "water",
        "fragrance": "parfum",
        "perfume": "parfum",
        "aloe vera": "aloe barbadensis leaf extract",
        "snail extract": "snail secretion filtrate",
        "vitamin b3": "niacinamide",
        "vitamin e": "tocopherol",
        "vitamin c": "ascorbic acid"
    }

    # 1. คลีนข้อความเบื้องต้นและแปลงคำพ้องความหมาย
    text_clean = extracted_text.lower()
    for word, replacement in synonyms.items():
        text_clean = re.sub(fr'\b{word}\b', replacement, text_clean)

    # 2. แยกข้อความออกเป็นคำๆ หรือวลี ด้วยเครื่องหมาย คอมมา, วงเล็บ, หรือการขึ้นบรรทัดใหม่
    tokens = [t.strip() for t in re.split(r'[,.();:|\n]', text_clean) if len(t.strip()) > 2]
    
    db_ingredients = df['ingredient'].tolist()
    found_ingredients = []
    
    # 3. ใช้ AI (Fuzzy Matching) ตรวจสอบความคล้ายคลึงของคำ
    # แม้ตัวอักษรจะเพี้ยนไปบ้าง ก็ยังสามารถโยงไปหาสารที่ถูกต้องได้
    for token in tokens:
        # กำหนดความแม่นยำ (คล้ายกัน 80% ขึ้นไปถือว่าใช่)
        matches = difflib.get_close_matches(token, db_ingredients, n=1, cutoff=0.80)
        
        if matches:
            matched_ing = matches[0]
            row = df[df['ingredient'] == matched_ing].iloc[0]
            found_ingredients.append({
                'Ingredient': matched_ing.title(),
                'Function': row['function'],
                'Risk': row['risk_level']
            })
            
    # 4. เพิ่มการกวาดสายตาแบบปกติ (Exact Match) เผื่อกรณีสารซ่อนอยู่ในประโยคยาวๆ
    for index, row in df.iterrows():
        ing_name = str(row['ingredient'])
        if ing_name in text_clean:
            found_ingredients.append({
                'Ingredient': ing_name.title(),
                'Function': row['function'],
                'Risk': row['risk_level']
            })

    # ลบข้อมูลที่ซ้ำซ้อน
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

st.markdown("**ระบบสแกนส่วนผสมเครื่องสำอางและสกินแคร์อัจฉริยะ (ฉบับผู้ใช้งานทั่วไป)**")

# --- ระบบให้เลือก 2 แท็บ ---
tab1, tab2 = st.tabs(["📸 ถ่ายรูปจากกล้อง", "📂 อัปโหลดรูปภาพ"])

with tab1:
    st.info("💡 **วิธีใช้งาน:** ถ่ายรูปสลากส่วนผสมให้ชัดเจนที่สุด แล้วรอ AI ประมวลผลอัตโนมัติ")
    camera_file = st.camera_input("ถ่ายรูปสลากผลิตภัณฑ์")
    
with tab2:
    st.info("💡 **วิธีใช้งาน:** อัปโหลดรูปภาพสลากผลิตภัณฑ์ แล้วรอ AI ประมวลผลอัตโนมัติ")
    uploaded_file = st.file_uploader("เลือกรูปภาพ...", type=['jpg', 'jpeg', 'png'])

img_file = camera_file if camera_file is not None else uploaded_file

if img_file is not None:
    col_img, col_res = st.columns([1, 2])
    
    with col_img:
        image = Image.open(img_file)
        st.image(image, caption='ภาพสลากที่กำลังตรวจสอบ', use_container_width=True)
        
    with col_res:
        with st.spinner('🤖 AI กำลังอ่านและชดเชยคำผิดอัตโนมัติ...'):
            try:
                # ปรับแต่งภาพให้ AI อ่านง่ายขึ้น
                gray_img = image.convert('L')
                enhancer_contrast = ImageEnhance.Contrast(gray_img)
                processed_img = enhancer_contrast.enhance(1.5)
                
                # ดึงข้อความดิบ
                extracted_text = pytesseract.image_to_string(processed_img)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่านภาพ: {e}")
                extracted_text = ""
                
        if extracted_text.strip() == "":
            st.error("⚠️ ไม่พบตัวอักษร แนะนำให้ถ่ายรูปใหม่ในที่สว่างขึ้นค่ะ")
        else:
            # นำข้อความไปวิเคราะห์ทันที ไม่ต้องให้ผู้ใช้มานั่งตรวจเอง
            result_df = analyze_ingredients(extracted_text, df_db)
            
            if result_df.empty:
                st.warning("สแกนพบข้อความ แต่ไม่พบสารที่ตรงกับฐานข้อมูล ลองถ่ายรูปให้ชัดขึ้นอีกนิดนะคะ")
            else:
                st.success(f"✅ ตรวจพบสารสำคัญ {len(result_df)} ชนิด (ประมวลผลคำผิดอัตโนมัติแล้ว)")
                
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
st.caption("📝 **หมายเหตุ:** ข้อมูลอ้างอิงจากฐานข้อมูล หากมีอาการแพ้ควรปรึกษาแพทย์ทันที")
