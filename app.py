import streamlit as st
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import re

# ==========================================
# 1. ตั้งค่าหน้าเพจ (ปรับเป็น Wide ให้กว้างขึ้น)
# ==========================================
st.set_page_config(page_title="SkinScan AI", page_icon="🌿", layout="wide")

# ==========================================
# 2. แถบเมนูด้านข้าง (Sidebar - วิธีใช้งาน)
# ==========================================
with st.sidebar:
    st.header("💡 วิธีการใช้งาน")
    st.markdown("""
    1. **เตรียมสลาก:** พลิกหลังซอง/ขวดผลิตภัณฑ์
    2. **ถ่ายรูป:** ถ่ายให้เห็นตัวอักษร Ingredients ชัดเจน
    3. **อัปโหลด:** กดปุ่ม Browse files เพื่ออัปโหลดรูป
    4. **รอผล:** AI จะแยกหมวดหมู่สารให้ทันที
    """)
    st.info("📌 **Tip:** หากตัวอักษรเล็กมาก กรุณาถ่ายในที่สว่าง หรือครอปรูปเฉพาะส่วนผสมก่อนอัปโหลด")

# ==========================================
# 3. โหลดฐานข้อมูล
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
# 4. ฟังก์ชันวิเคราะห์ส่วนผสม
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
# 5. หน้าจอหลัก (UI)
# ==========================================
# st.image("banner.png") # ถ้าออกแบบแบนเนอร์จาก Canva เสร็จแล้ว ให้นำภาพมาใส่โฟลเดอร์เดียวกับโค้ด แล้วลบเครื่องหมาย # บรรทัดนี้ออก
st.title("🌿 SkinScan AI")
st.markdown("**ระบบสแกนส่วนผสมเครื่องสำอางและสกินแคร์อัจฉริยะ**")

uploaded_file = st.file_uploader("📸 อัปโหลดรูปภาพสลากด้านหลังผลิตภัณฑ์ (Ingredients)", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # แบ่งหน้าจอเป็น 2 ฝั่ง (ซ้าย: รูป / ขวา: ผลลัพธ์)
    col_img, col_res = st.columns([1, 2])
    
    with col_img:
        image = Image.open(uploaded_file)
        st.image(image, caption='รูปภาพสลากที่อัปโหลด', use_container_width=True)
        
    with col_res:
        with st.spinner('🤖 AI กำลังปรับความคมชัดและกวาดสายตาอ่านข้อความ...'):
            try:
                # --- พัฒนาระบบ AI ปรับแต่งภาพ (แก้ภาพเบลอ/สีกลืน) ---
                # 1. แปลงขาวดำ
                gray_img = image.convert('L')
                # 2. ดันคอนทราสต์ให้จัด
                enhancer_contrast = ImageEnhance.Contrast(gray_img)
                img_contrast = enhancer_contrast.enhance(3.0)
                # 3. เพิ่มความคมชัด (Sharpness) ให้ขอบตัวอักษร
                enhancer_sharpness = ImageEnhance.Sharpness(img_contrast)
                img_sharp = enhancer_sharpness.enhance(3.0)
                # 4. บังคับแยกสีขาวดำ (Thresholding) ตัดนอยส์พื้นหลัง
                processed_img = img_sharp.point(lambda x: 0 if x < 140 else 255, '1')
                
                with st.expander("👁️ ดูมุมมองภาพจำลองที่ AI ใช้สแกนข้อความ"):
                    st.image(processed_img, caption='ภาพผ่านกระบวนการ Binarization & Enhancement', use_container_width=True)

                # ดึงข้อความ
                extracted_text = pytesseract.image_to_string(processed_img)
                
                if extracted_text.strip() == "":
                    st.error("⚠️ ไม่พบตัวอักษร AI อ่านข้อความไม่ได้ แนะนำให้ถ่ายใหม่ในที่สว่างค่ะ")
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
