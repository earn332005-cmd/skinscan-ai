import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re

# ==========================================
# 1. ตั้งค่าหน้าเพจ
# ==========================================
st.set_page_config(page_title="SkinScan AI", page_icon="🌿", layout="centered")

# ==========================================
# 2. ฟังก์ชันโหลดฐานข้อมูล (ใช้ Cache เพื่อความรวดเร็ว)
# ==========================================
@st.cache_data
def load_data():
    try:
        # โหลดไฟล์ database.csv ที่กลุ่มเราเตรียมไว้
        df = pd.read_csv('database.csv')
        # แปลงชื่อสารให้เป็นตัวพิมพ์เล็กทั้งหมดเพื่อความง่ายในการค้นหา
        df['ingredient'] = df['ingredient'].astype(str).str.lower()
        return df
    except FileNotFoundError:
        st.error("❌ ไม่พบไฟล์ 'database.csv' กรุณาตรวจสอบว่ามีไฟล์อยู่ในโฟลเดอร์เดียวกับ app.py ค่ะ")
        return pd.DataFrame()

df_db = load_data()

# ==========================================
# 3. ฟังก์ชันวิเคราะห์ส่วนผสม (อัปเดตแก้บั๊กตัดคำ)
# ==========================================
def analyze_ingredients(extracted_text, df):
    # 1. ลบการปัดบรรทัดทิ้ง เพื่อให้คำที่ถูกตัดบรรทัดมาต่อกัน
    text_clean = extracted_text.replace('\n', ' ')
    
    # 2. คลีนข้อความ (อนุญาตให้มีเครื่องหมายขีด - และเครื่องหมายทับ /)
    text_clean = re.sub(r'[^\w\s\-/]', ' ', text_clean.lower())
    
    found_ingredients = []
    
    # วิ่งเช็กชื่อสารเคมีในฐานข้อมูลของเราทีละตัว
    for index, row in df.iterrows():
        ing_name = str(row['ingredient']).strip()
        # ถ้าเจอชื่อสารในข้อความที่สแกนได้ ให้เก็บข้อมูลไว้
        if ing_name in text_clean:
            found_ingredients.append({
                'Ingredient': ing_name.title(),
                'Function': row['function'],
                'Risk': row['risk_level']
            })
            
    return pd.DataFrame(found_ingredients)

# ==========================================
# 4. หน้าจอส่วนแสดงผล (UI)
# ==========================================
st.title("🌿 SkinScan AI")
st.markdown("**ระบบสแกนส่วนผสมเครื่องสำอางและสกินแคร์อัจฉริยะ**")
st.markdown("อัปโหลดรูปภาพสลากด้านหลังผลิตภัณฑ์ (Ingredients) เพื่อตรวจสอบความปลอดภัย")

# ที่สำหรับให้อัปโหลดรูปภาพ
uploaded_file = st.file_uploader("เลือกรูปภาพ...", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # 4.1 โชว์รูปที่อัปโหลด
    image = Image.open(uploaded_file)
    st.image(image, caption='รูปภาพสลากที่อัปโหลด', use_container_width=True)
    
    st.markdown("---")
    st.subheader("🔍 ผลการวิเคราะห์ส่วนผสม")
    
    with st.spinner('AI กำลังกวาดสายตาอ่านข้อความ...'):
        try:
            # หมายเหตุสำหรับ Windows: ถ้าเออเร่อหา Tesseract ไม่เจอ ให้ลบเครื่องหมาย # บรรทัดล่างออก แล้วแก้ Path ให้ตรงกับเครื่อง
            # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            # ดึงข้อความจากภาพ
            extracted_text = pytesseract.image_to_string(image)
            
            if extracted_text.strip() == "":
                st.error("⚠️ ไม่พบตัวอักษรในรูปภาพ กรุณาถ่ายรูปให้โฟกัสชัดเจนขึ้น หรืออยู่ในที่สว่างค่ะ")
            else:
                # วิเคราะห์ข้อความ
                result_df = analyze_ingredients(extracted_text, df_db)
                
                if result_df.empty:
                    st.warning("สแกนพบข้อความ แต่ไม่พบสารที่ตรงกับฐานข้อมูลของเราค่ะ (อาจเป็นสารสกัดทั่วไป)")
                    with st.expander("ดูข้อความที่สแกนได้ทั้งหมด"):
                        st.write(extracted_text)
                else:
                    st.success(f"ตรวจพบสารสำคัญที่ระบบรู้จักจำนวน {len(result_df)} ชนิด")
                    
                    # 4.2 แสดงผลแยกตามระดับความเสี่ยง
                    for index, row in result_df.iterrows():
                        ing = row['Ingredient']
                        func = row['Function']
                        risk = row['Risk']
                        
                        if risk == 'Safe':
                            st.info(f"🟢 **{ing}** : {func}")
                        elif risk == 'Warning':
                            st.warning(f"🟡 **{ing}** : {func} (ผู้ที่มีผิวแพ้ง่ายควรระวัง)")
                        elif risk == 'Danger':
                            st.error(f"🔴 **{ing}** : {func} (สารกลุ่มเสี่ยง / ควรหลีกเลี่ยง)")
                            
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")

# ==========================================
# 5. ข้อความแจ้งเตือน (Disclaimer) ป้องกันการเข้าใจผิด
# ==========================================
st.markdown("---")
st.caption("📝 **หมายเหตุ:** ระบบวิเคราะห์ข้อมูลอ้างอิงจากสารที่ตรงกับฐานข้อมูลในระบบเท่านั้น หากมีสารสกัดชื่อใหม่หรือสารเคมีที่ระบบยังไม่รู้จัก จะไม่ถูกนำมาประเมินผล โปรดทดสอบอาการแพ้ที่ท้องแขนก่อนใช้งานจริงทุกครั้ง")
