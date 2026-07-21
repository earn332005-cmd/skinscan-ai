import streamlit as st
import pandas as pd
from PIL import Image, ImageEnhance, ImageDraw
import pytesseract
import re
import difflib

# ==========================================
# 1. ตั้งค่าหน้าเพจ 
# =========================================
st.markdown("""
    <style>
    /* ปรับพื้นหลังหลักให้เป็นสีเทานวลสะอาดตา อ่านง่ายสบายตาในทุกโหมด */
    [data-testid="stAppViewContainer"] {
        background-color: #f8f9fa;
    }
    
    [data-testid="stHeader"] {
        background-color: transparent;
    }
    
    /* บังคับให้ตัวหนังสือหลักเป็นสีเข้มคมชัด */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #2c3e50 !important;
    }
    
    /* ตกแต่งกล่องข้อความอธิบาย (Info) ให้เด่นชัด ขอบมนสวยงาม */
    div.stAlert {
        background-color: #e3f2fd !important;
        color: #0d47a1 !important;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        border: none;
    }
    div.stAlert p {
        color: #0d47a1 !important;
    }
    
    /* ตกแต่งปุ่มกดให้เป็นสีชมพูพาสเทลสกินแคร์ น่ารักสดใส */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        border: none;
        background-color: #ffb6c1;
        color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        background-color: #ff9eaa;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* ตกแต่งกล่อง Expander ผลลัพธ์ */
    .streamlit-expanderHeader {
        background-color: #ffffff;
        border-radius: 8px;
        font-weight: bold;
        color: #2c3e50 !important;
    }
    </style>
    """, unsafe_allow_html=True)

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
# 3. ฟังก์ชันวิเคราะห์ส่วนผสม (แก้พิกัดไฮไลต์ไม่ให้หลุดขอบ)
# ==========================================
def analyze_ingredients_with_boxes(processed_img, df):
    data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DATAFRAME)
    data = data[data.text.notnull() & (data.text.str.strip() != "")]
    
    full_text = " ".join(data['text'].tolist())
    text_clean = full_text.lower()
    
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
    
    for word, replacement in synonyms.items():
        text_clean = re.sub(fr'\b{word}\b', replacement, text_clean)
        
    db_ingredients = df['ingredient'].tolist()
    found_ingredients = []
    
    # วนลูปเช็กจากคำในภาพจริงเพื่อให้ได้พิกัด (Bounding Box) ที่ถูกต้องแม่นยำ
    for i, row_ocr in data.iterrows():
        word_token = str(row_ocr['text']).strip().lower()
        if len(word_token) <= 2:
            continue
            
        # 1. เช็กแบบตรงตัว
        matched_ing = None
        if word_token in db_ingredients:
            matched_ing = word_token
        else:
            # 2. เช็กแบบใกล้เคียง (Fuzzy Match)
            matches = difflib.get_close_matches(word_token, db_ingredients, n=1, cutoff=0.75)
            if matches:
                matched_ing = matches[0]
                
        if matched_ing:
            db_row = df[df['ingredient'] == matched_ing].iloc[0]
            existing_ings = [x['Ingredient'].lower() for x in found_ingredients]
            
            # ถ้ายังไม่มีในลิสต์ ให้เพิ่มพร้อมพิกัดจริงจาก OCR ของคำนั้นๆ
            if matched_ing not in existing_ings:
                found_ingredients.append({
                    'Ingredient': matched_ing.title(),
                    'Function': db_row['function'],
                    'Risk': db_row['risk_level'],
                    'box': (row_ocr['left'], row_ocr['top'], row_ocr['width'], row_ocr['height'])
                })

    # เพิ่มเติม: สำหรับสารสกัดยาวๆ ที่ OCR อาจจะตัดคำแยกกัน ให้กวาดหาภาพรวมเพิ่มเติม
    for index, row in df.iterrows():
        ing_name = str(row['ingredient']).strip().lower()
        existing_ings = [x['Ingredient'].lower() for x in found_ingredients]
        if len(ing_name) > 3 and ing_name in text_clean and ing_name not in existing_ings:
            # หาคำแรกที่เป็นส่วนประกอบเพื่อดึงพิกัดใกล้เคียง
            first_word = ing_name.split()[0]
            matched_row = data[data['text'].str.lower().str.contains(first_word, na=False)]
            if not matched_row.empty:
                r = matched_row.iloc[0]
                box_coords = (r['left'], r['top'], r['width'] * len(ing_name.split()), r['height'])
            else:
                box_coords = (50, 50, 100, 20) # พิกัดกันเหนียวตรงกลางรูป
                
            found_ingredients.append({
                'Ingredient': ing_name.title(),
                'Function': row['function'],
                'Risk': row['risk_level'],
                'box': box_coords
            })

    if found_ingredients:
        result_df = pd.DataFrame(found_ingredients)
        result_df = result_df.drop_duplicates(subset=['Ingredient']).reset_index(drop=True)
        return result_df, data
    else:
        return pd.DataFrame(), data
    
# ==========================================
# 4. หน้าจอหลัก (UI)
# ==========================================
col_icon, col_title = st.columns([1, 9])
with col_icon:
    st.image("woman_5362023.png", width=65)
with col_title:
    st.title("SkinScan AI")

st.markdown("**ระบบสแกนส่วนผสมเครื่องสำอางและสกินแคร์อัจฉริยะ (พร้อมระบบคลิกไฮไลต์ตำแหน่ง)**")

tab1, tab2 = st.tabs(["📸 ถ่ายรูปจากกล้อง", "📂 อัปโหลดรูปภาพ"])

with tab1:
    st.info("💡 **วิธีใช้งาน:** ถ่ายรูปสลากส่วนผสมให้ชัดเจน แล้วรอ AI ประมวลผล")
    camera_file = st.camera_input("ถ่ายรูปสลากผลิตภัณฑ์")
    
with tab2:
    st.info("💡 **วิธีใช้งาน:** อัปโหลดรูปภาพสลากผลิตภัณฑ์ แล้วรอ AI ประมวลผล")
    uploaded_file = st.file_uploader("เลือกรูปภาพ...", type=['jpg', 'jpeg', 'png'])

img_file = camera_file if camera_file is not None else uploaded_file

if img_file is not None:
    original_image = Image.open(img_file)
    
    with st.spinner('🤖 AI กำลังอ่านข้อความและประมวลผลตำแหน่งพิกัด...'):
        try:
            gray_img = original_image.convert('L')
            enhancer_contrast = ImageEnhance.Contrast(gray_img)
            processed_img = enhancer_contrast.enhance(1.5)
            
            result_df, ocr_data = analyze_ingredients_with_boxes(processed_img, df_db)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
            result_df = pd.DataFrame()

    if result_df.empty:
        st.warning("สแกนพบภาพ แต่ไม่พบสารสำคัญที่ตรงกับฐานข้อมูล แนะนำให้ถ่ายรูปในมุมที่สว่างและชัดเจนขึ้น")
    else:
        st.success(f"✅ ตรวจพบสารสำคัญที่รู้จัก {len(result_df)} ชนิด")

        # --- สร้างส่วนเลือกสารเพื่อดูไฮไลต์ ---
        st.markdown("### 🔍 คลิกเลือกสารเพื่อดูตำแหน่งไฮไลต์บนรูปภาพ")
        
        # ทำรายชื่อสารให้ผู้ใช้เลือกกดคลิก
        selected_ingredient = st.selectbox(
            "เลือกสารที่ต้องการตรวจสอบตำแหน่ง:",
            options=result_df['Ingredient'].tolist()
        )

        # แบ่งหน้าจอแสดงผล (ซ้าย: รูปภาพไฮไลต์ / ขวา: รายการความเสี่ยงทั้งหมด)
        col_img, col_res = st.columns([1, 1])

        with col_img:
            # วาดกรอบสี่เหลี่ยมทับลงบนรูปภาพต้นฉบับตามพิกัดของสารที่เลือก
            draw_image = original_image.copy()
            draw = ImageDraw.Draw(draw_image)
            
            # ดึงพิกัดของสารที่ถูกเลือก
            target_row = result_df[result_df['Ingredient'] == selected_ingredient].iloc[0]
            bx, by, bw, bh = target_row['box']
            
            # วาดกรอบสีแดงเน้นจุดที่เลือก (ขยายขอบเขตเล็กน้อยเพื่อให้เห็นชัดเจน)
            pad = 5
            draw.rectangle(
                [bx - pad, by - pad, bx + bw + pad, by + bh + pad],
                outline="red",
                width=4
            )
            
            st.image(draw_image, caption=f"ตำแหน่งของสาร: {selected_ingredient}", use_container_width=True)
            st.caption("🔴 กรอบสีแดงบนรูปภาพคือตำแหน่งที่ AI ตรวจพบสารตัวนั้นๆ")

        with col_res:
            st.markdown("### 📋 ผลการวิเคราะห์แยกตามระดับความเสี่ยง")
            
            safe_df = result_df[result_df['Risk'] == 'Safe']
            warn_df = result_df[result_df['Risk'] == 'Warning']
            danger_df = result_df[result_df['Risk'] == 'Danger']
            
            # แสดงผลแบบย่อในกล่องข้อความ
            with st.expander(f"🟢 ปลอดภัย ({len(safe_df)} ชนิด)", expanded=True):
                for _, row in safe_df.iterrows():
                    highlight_mark = " 👉 (กำลังแสดงตำแหน่ง)" if row['Ingredient'] == selected_ingredient else ""
                    st.write(f"- **{row['Ingredient']}**{highlight_mark}<br><small>{row['Function']}</small>", unsafe_allow_html=True)
                    
            with st.expander(f"🟡 เฝ้าระวัง ({len(warn_df)} ชนิด)", expanded=True):
                for _, row in warn_df.iterrows():
                    highlight_mark = " 👉 (กำลังแสดงตำแหน่ง)" if row['Ingredient'] == selected_ingredient else ""
                    st.write(f"- **{row['Ingredient']}**{highlight_mark}<br><small>{row['Function']}</small>", unsafe_allow_html=True)
                    
            with st.expander(f"🔴 อันตราย ({len(danger_df)} ชนิด)", expanded=True):
                for _, row in danger_df.iterrows():
                    highlight_mark = " 👉 (กำลังแสดงตำแหน่ง)" if row['Ingredient'] == selected_ingredient else ""
                    st.write(f"- **{row['Ingredient']}**{highlight_mark}<br><small>{row['Function']}</small>", unsafe_allow_html=True)

st.markdown("---")
st.caption("📝 **หมายเหตุ:** ระบบวิเคราะห์ข้อมูลอ้างอิงจากฐานข้อมูล หากมีอาการแพ้ควรปรึกษาแพทย์ทันที")
