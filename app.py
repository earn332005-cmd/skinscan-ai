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
# 3. ฟังก์ชันวิเคราะห์ส่วนผสม
# ==========================================
def analyze_ingredients(extracted_text, df):
    text_clean = extracted_text.replace('\n', ' ')
    text_clean = re.sub(r'[^\w\s\-/]', ' ', text_clean.lower())
    
    found_ingredients = []
    
    for index, row in df.iterrows():
        ing_name = str(row['ingredient']).strip()
        if ing_name in text_clean:
            found_ingredients.append({
                'Ingredient': ing_name.title(),
                'Function': row['function'],
                'Risk': row['risk_level']
            })
            
    return pd.DataFrame(found_ingredients)

# ==========================================
# 4. หน้าจอหลัก (UI)
# ==========================================
col_icon, col_title = st.columns([1, 9])
with col_icon:
    st.image("woman_5362023.png", width=65)
with col_title:
    st.title("SkinScan AI")

st.markdown("**ระบบสแกนส่วนผสมเครื่องสำอางและสกินแคร์อัจฉริยะ**")

# --- ย้ายวิธีการใช้งานมาแสดงตรงหน้าแรก ---
st.info("💡 **วิธีการใช้งาน:** 1. ถ่ายรูปส่วนผสม (Ingredients) ให้ชัดเจน ➔ 2. อัปโหลดรูปลงระบบ ➔ 3. รอ AI ประมวลผลแยกหมวดหมู่สาร")

# --- เพิ่มระบบให้เลือก 2 แท็บ (ถ่ายรูปสด / อัปโหลดรูป) ---
tab1, tab2 = st.tabs(["📸 ถ่ายรูปจากกล้อง", "📂 อัปโหลดรูปภาพ"])

with tab1:
    camera_file = st.camera_input("ถ่ายรูปสลากผลิตภัณฑ์ให้ชัดเจน")
with tab2:
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
                # --- พัฒนาระบบ AI ปรับแต่งภาพ (ลดความแข็งของฟิลเตอร์ลง) ---
                # 1. ปรับเป็นภาพสีเทา เพื่อลดความสับสนของสีพื้นหลัง
                gray_img = image.convert('L')
                # 2. เพิ่มคอนทราสต์แค่เล็กน้อย (1.5) ไม่ให้แสงมืดหรือกลืนเกินไป
                enhancer_contrast = ImageEnhance.Contrast(gray_img)
                processed_img = enhancer_contrast.enhance(1.5)
                
                with st.expander("👁️ ดูมุมมองภาพจำลองที่ AI ใช้สแกนข้อความ"):
                    st.image(processed_img, caption='ภาพปรับสีเทาเพื่อการอ่าน', use_container_width=True)

                # ดึงข้อความ
                extracted_text = pytesseract.image_to_string(processed_img)
                
                if extracted_text.strip() == "":
                    st.error("⚠️ ไม่พบตัวอักษร AI อ่านข้อความไม่ได้ แนะนำให้ถ่ายให้โฟกัสชัดเจนขึ้นค่ะ")
                else:
                    result_df = analyze_ingredients(extracted_text, df_db)
                    
                    if result_df.empty:
                        st.warning("สแกนพบข้อความ แต่ไม่พบสารที่ตรงกับฐานข้อมูล")
                        with st.expander("ดูข้อความที่สแกนได้ทั้งหมด"):
                            st.write(extracted_text)
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
                                
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

st.markdown("---")
st.caption("📝 **หมายเหตุ:** ระบบวิเคราะห์ข้อมูลอ้างอิงจากฐานข้อมูลเท่านั้น หากมีอาการแพ้ควรปรึกษาแพทย์ทันที")
