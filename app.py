import os, io, re, zipfile, shutil, tempfile, traceback
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import streamlit as st

# ------------------- PAGE CONFIG -------------------
st.set_page_config(
    page_title="LFJC Paper Processor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------- CUSTOM CSS -------------------
st.markdown("""
<style>
    /* Hide ALL Streamlit branding elements completely */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    header {visibility: hidden !important;}

    /* Specifically target and hide the "Manage Apps" button */
    [data-testid="collapsedControl"] {display: none !important;}
    [data-testid="stMainMenu"] {display: none !important;}
    [data-testid="stSidebarNav"] {display: none !important;}

    /* Hide the hamburger menu and manage app button container */
    .stApp > header {display: none !important;}
    div[data-testid="stDecoration"] {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}

    /* Additional selectors to ensure everything is hidden */
    [data-testid="stToolbar"], 
    [data-testid="stToolbarActions"] {display: none !important;}

    /* Hide any other Streamlit interface elements */
    iframe[title="Manage app"] {display: none !important;}
    iframe[title="Report a bug"] {display: none !important;}

    /* Force hide any remaining elements */
    button[title="Manage app"] {display: none !important;}
    button[aria-label="Manage app"] {display: none !important;}

    /* Clear any remaining Streamlit padding/margins */
    .stApp > div:nth-child(1) > div:nth-child(1) > div > div:nth-child(2) > div {display: none !important;}
    .stApp > div:nth-child(1) > div:nth-child(1) > div > div:nth-child(1) > div {display: none !important;}
    
    /* Professional styling */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        padding: 0.75rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .ratio-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4a90e2;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .selected-file {
        background: #f0f8ff;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #4a90e2;
        font-size: 0.9rem;
    }
    .stSidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Professional styling */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #4a90e2;
    }
    
    /* Sidebar show/hide button */
    .sidebar-toggle {
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 1000;
        background: #4a90e2;
        color: white;
        border: none;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    
    .sidebar-toggle:hover {
        background: #357ae8;
        transform: scale(1.1);
    }
    
    /* Auto-download styles */
    .auto-download-link {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ------------------- SESSION STATE -------------------
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'sidebar_visible' not in st.session_state:
    st.session_state.sidebar_visible = True
if 'auto_download_triggered' not in st.session_state:
    st.session_state.auto_download_triggered = False
if 'download_data' not in st.session_state:
    st.session_state.download_data = None
if 'download_filename' not in st.session_state:
    st.session_state.download_filename = ""
if 'download_type' not in st.session_state:
    st.session_state.download_type = ""

# ------------------- SIDEBAR TOGGLE BUTTON -------------------
if not st.session_state.sidebar_visible:
    st.markdown("""
    <div class="sidebar-toggle" onclick="document.getElementById('sidebar-toggle-script').click()">
        ☰
    </div>
    <script>
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'sidebar-toggle-script';
        toggleBtn.style.display = 'none';
        document.body.appendChild(toggleBtn);
        
        toggleBtn.onclick = function() {
            this.dispatchEvent(new CustomEvent('toggle-sidebar'));
        };
    </script>
    """, unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown("""
<div class="main-header">
    <h1>🎓 LFJC PAPER PROCESSING SYSTEM</h1>
    <p>Professional Answer Sheet Processing | Little Flower Junior College, Uppal</p>
</div>
""", unsafe_allow_html=True)

# ------------------- SIDEBAR -------------------
if st.session_state.sidebar_visible:
    with st.sidebar:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("### ⚙️ SETTINGS PANEL")
        with col2:
            if st.button("✕", help="Close sidebar", key="close_sidebar"):
                st.session_state.sidebar_visible = False
                st.rerun()
        
        st.markdown("---")
        
        st.markdown('<div class="section-header">📋 EXAM DETAILS</div>', unsafe_allow_html=True)
        exam_type = st.text_input("Exam Type", "", placeholder="e.g., Semester I - Physics", key="exam_type")
        exam_date = st.text_input("Exam Date (DD-MM-YYYY)", "", placeholder="15-01-2024", key="exam_date")
        
        st.markdown('<div class="section-header">📐 PAGE ALIGNMENT</div>', unsafe_allow_html=True)
        alignment = st.radio(
            "Image Alignment",
            ["Center", "Left", "Right"],
            horizontal=True,
            index=0,
            help="Position images on the page",
            key="alignment"
        )
        
        st.markdown('<div class="section-header">✂️ STRIP CROPPING SETTINGS</div>', unsafe_allow_html=True)
        
        # Strip 1
        st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            strip_q1 = st.text_input("Question Range 1", "", placeholder="e.g., 1-5", key="strip_q1")
        with col2:
            ratio_option1 = st.selectbox("Ratio 1", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r1")
            if ratio_option1 == "Custom":
                ratio_val1 = st.number_input("Custom Ratio 1", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c1")
            else:
                ratio_val1 = 1/float(ratio_option1.split("/")[1])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Strip 2
        st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            strip_q2 = st.text_input("Question Range 2", "", placeholder="e.g., 6-10", key="strip_q2")
        with col2:
            ratio_option2 = st.selectbox("Ratio 2", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r2")
            if ratio_option2 == "Custom":
                ratio_val2 = st.number_input("Custom Ratio 2", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c2")
            else:
                ratio_val2 = 1/float(ratio_option2.split("/")[1])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Strip 3
        st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            strip_q3 = st.text_input("Question Range 3", "", placeholder="e.g., 11-15", key="strip_q3")
        with col2:
            ratio_option3 = st.selectbox("Ratio 3", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r3")
            if ratio_option3 == "Custom":
                ratio_val3 = st.number_input("Custom Ratio 3", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c3")
            else:
                ratio_val3 = 1/float(ratio_option3.split("/")[1])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">🔢 NUMBERING OPTIONS</div>', unsafe_allow_html=True)
        multi_numbering_input = st.text_input("Custom Numbering Ranges", 
                                            placeholder="Format: 1-5:1, 6-10:41, 11-15:51",
                                            help="Map image ranges to custom starting numbers",
                                            key="multi_numbering")
        skip_numbering_input = st.text_input("Skip Images", 
                                           placeholder="e.g., 2,4-5,7",
                                           help="Images to skip from numbering sequence",
                                           key="skip_numbering")
        
        st.markdown("---")
        
        with st.expander("📖 Quick Help"):
            st.markdown("""
            **Format Examples:**
            - **Question Ranges:** `1-5, 10, 15-20`
            - **Custom Numbering:** `1-5:1, 6-10:41`  
              (Images 1-5 start at 1, Images 6-10 start at 41)
            - **Skip Images:** `2,4-5,7`  
              (Skip images 2, 4, 5, and 7)
            """)
        
        st.markdown("---")
        st.markdown("*Settings panel can be reopened from the ☰ button*")

else:
    st.markdown("""
    <div style='text-align: center; padding: 2rem;'>
        <h3>Settings Panel Hidden</h3>
        <p>Click the ☰ button in the top-left corner to reopen settings.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("☰ Open Settings"):
        st.session_state.sidebar_visible = True
        st.rerun()

# ------------------- MAIN AREA -------------------
st.markdown("### 📁 UPLOAD ANSWER SHEETS")

uploaded_files = st.file_uploader(
    "Choose answer sheet images (PNG, JPG, JPEG format)",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True,
    help="Select multiple images. Each batch processes up to 10 images.",
    key="file_uploader"
)

if uploaded_files:
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 **ADD TO PROCESSING QUEUE**", use_container_width=True, type="primary"):
            for uploaded_file in uploaded_files:
                if not any(f['name'] == uploaded_file.name for f in st.session_state.uploaded_files):
                    st.session_state.uploaded_files.append({
                        'name': uploaded_file.name,
                        'bytes': uploaded_file.read()
                    })
            st.success(f"✅ Successfully added {len(uploaded_files)} new images to processing queue")
            st.rerun()
    
    with col2:
        if st.button("🗑️ **CLEAR PROCESSING QUEUE**", use_container_width=True, type="secondary"):
            st.session_state.uploaded_files = []
            st.session_state.processed_files = []
            st.success("✅ Processing queue cleared successfully")
            st.rerun()

if st.session_state.uploaded_files:
    st.markdown(f"### 📋 PROCESSING QUEUE ({len(st.session_state.uploaded_files)} images)")
    
    for idx, file_info in enumerate(st.session_state.uploaded_files):
        st.markdown(f'<div class="selected-file">📄 {file_info["name"]}</div>', unsafe_allow_html=True)

# ------------------- HELPER FUNCTIONS -------------------
def enhance_image_opencv(pil_img):
    try:
        img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 29, 17)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(thresh, -1, kernel)
        return Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB))
    except:
        return pil_img

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def parse_qnos(qnos_str):
    q_list = []
    if not qnos_str:
        return q_list
    for part in qnos_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            q_list.extend(range(start, end + 1))
        elif part:
            q_list.append(int(part))
    return q_list

def parse_multi_numbering(input_str):
    numbering_map = {}
    if not input_str:
        return numbering_map
    for part in input_str.split(','):
        part = part.strip()
        if ':' in part:
            img_range, start_num = part.split(':')
            try:
                start_num = int(start_num)
            except ValueError:
                continue
            if '-' in img_range:
                start_idx, end_idx = map(int, img_range.split('-'))
                for i, idx in enumerate(range(start_idx, end_idx + 1)):
                    numbering_map[idx] = start_num + i
            else:
                idx = int(img_range)
                numbering_map[idx] = start_num
    return numbering_map

def parse_skip_images(skip_str):
    skip_list = []
    if not skip_str:
        return skip_list
    for part in skip_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            skip_list.extend(range(start, end + 1))
        elif part:
            skip_list.append(int(part))
    return skip_list

def sanitize_filename(name):
    cleaned_name = re.sub(r'[^À-῿Ⰰ-퟿豈-﷏\w\s.-]', '_', name)
    cleaned_name = re.sub(r'\s+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')
    if not cleaned_name:
        return "untitled"
    return cleaned_name

def get_strip_mapping():
    mapping = {}
    if strip_q1:
        for q in parse_qnos(strip_q1):
            mapping[q] = ratio_val1
    if strip_q2:
        for q in parse_qnos(strip_q2):
            mapping[q] = ratio_val2
    if strip_q3:
        for q in parse_qnos(strip_q3):
            mapping[q] = ratio_val3
    return mapping

def load_font_with_size(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except:
            return ImageFont.load_default()

# ------------------- AUTO-DOWNLOAD FUNCTION -------------------
def trigger_auto_download(file_data, filename, file_type):
    """Set up auto-download in session state"""
    st.session_state.auto_download_triggered = True
    st.session_state.download_data = file_data
    st.session_state.download_filename = filename
    st.session_state.download_type = file_type

# ------------------- PDF GENERATION -------------------
def create_pdf(files):
    try:
        A4_WIDTH, A4_HEIGHT = int(8.27 * 300), int(11.69 * 300)
        TOP_MARGIN_FIRST_PAGE, TOP_MARGIN_SUBSEQUENT_PAGES = 125, 110
        BOTTOM_MARGIN = 105
        GAP_BETWEEN_IMAGES = 20
        OVERLAP_PIXELS = 25
        WATERMARK_TEXT = "LFJC"
        WATERMARK_OPACITY = int(255 * 0.20)

        pdf_pages = []
        
        header_font = load_font_with_size(60)
        subheader_font = load_font_with_size(45)
        question_font = load_font_with_size(40)
        page_number_font = load_font_with_size(30)
        watermark_font = load_font_with_size(800)

        strip_mapping = get_strip_mapping()
        numbering_map = parse_multi_numbering(multi_numbering_input)
        skip_list = parse_skip_images(skip_numbering_input)

        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        y_offset = TOP_MARGIN_FIRST_PAGE

        draw_header = ImageDraw.Draw(current_page)
        college_name = "LITTLE FLOWER JUNIOR COLLEGE, UPPAL, HYD-39"
        
        try:
            bbox = draw_header.textbbox((0, 0), college_name, font=header_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw_header.text(((A4_WIDTH - text_width) // 2, y_offset), college_name, fill="black", font=header_font)
            y_offset += text_height + 10
        except:
            draw_header.text((A4_WIDTH // 4, y_offset), college_name, fill="black", font=header_font)
            y_offset += 80

        combined_header = f"{exam_type}   {exam_date}"
        try:
            bbox = draw_header.textbbox((0, 0), combined_header, font=subheader_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw_header.text(((A4_WIDTH - text_width) // 2, y_offset), combined_header, fill="black", font=subheader_font)
            y_offset += text_height + 40
        except:
            draw_header.text((A4_WIDTH // 3, y_offset), combined_header, fill="black", font=subheader_font)
            y_offset += 60

        image_index = 1
        question_number_counter = 0

        files.sort(key=lambda x: natural_sort_key(x['name']))

        for file_info in files:
            question_number_to_display = None
            if image_index in numbering_map:
                question_number_to_display = numbering_map[image_index]
            elif image_index not in skip_list:
                question_number_counter += 1
                question_number_to_display = question_number_counter
            else:
                image_index += 1
                continue
            
            try:
                img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                if alignment == "Center":
                    scale = (A4_WIDTH * 0.9) / img.width
                else:
                    SIDE_MARGIN = 50
                    scale = ((A4_WIDTH - SIDE_MARGIN) * 0.9) / img.width
                
                img_scaled = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
                img_to_process = img_scaled
                is_first_part = True

                while img_to_process:
                    remaining_space = A4_HEIGHT - y_offset - BOTTOM_MARGIN
                    if img_to_process.height <= remaining_space:
                        img_part = img_to_process
                        img_to_process = None
                    else:
                        split_height = remaining_space + OVERLAP_PIXELS
                        img_part = img_to_process.crop((0, 0, img_to_process.width, split_height))
                        img_to_process = img_to_process.crop((0, split_height - OVERLAP_PIXELS, img_to_process.width, img_to_process.height))

                    draw_img = ImageDraw.Draw(img_part)

                    fraction = strip_mapping.get(question_number_to_display, None)
                    if fraction is not None:
                        strip_width = int(img_part.width * fraction)
                        draw_img.rectangle([(0, 0), (strip_width, img_part.height)], fill=(255, 255, 255))

                    if is_first_part and question_number_to_display is not None:
                        try:
                            bbox = draw_img.textbbox((0, 0), f"{question_number_to_display}.", font=question_font)
                            text_width_q = bbox[2] - bbox[0]
                            text_height_q = bbox[3] - bbox[1]
                            text_x = (strip_width - text_width_q - 10) if fraction is not None else 10
                            draw_img.text((text_x, 10), f"{question_number_to_display}.", font=question_font, fill="black")
                        except:
                            draw_img.text((10, 10), f"{question_number_to_display}.", font=question_font, fill="black")
                        is_first_part = False

                    if alignment == "Center":
                        x_position = (A4_WIDTH - img_part.width) // 2
                    elif alignment == "Left":
                        x_position = 50
                    else:
                        x_position = A4_WIDTH - img_part.width - 50
                    
                    current_page.paste(img_part, (x_position, y_offset))
                    y_offset += img_part.height + GAP_BETWEEN_IMAGES

                    if img_to_process:
                        pdf_pages.append(current_page)
                        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
                        y_offset = TOP_MARGIN_SUBSEQUENT_PAGES

                image_index += 1

            except Exception as e:
                st.error(f"Error processing {file_info['name']}: {e}")
                continue

        pdf_pages.append(current_page)

        for i, page in enumerate(pdf_pages):
            try:
                draw_page = ImageDraw.Draw(page)
                draw_page.text((A4_WIDTH//3, A4_HEIGHT//2), WATERMARK_TEXT, fill=(200, 200, 200, 100), font=watermark_font)
            except:
                pass

            if i > 0:
                try:
                    draw_page_num = ImageDraw.Draw(page)
                    page_number_text = str(i + 1)
                    draw_page_num.text((A4_WIDTH//2, A4_HEIGHT - 50), page_number_text, fill="black", font=page_number_font)
                except:
                    pass

        pdf_buffer = io.BytesIO()
        pdf_pages[0].save(pdf_buffer, format='PDF', save_all=True, append_images=pdf_pages[1:], resolution=100.0)
        pdf_buffer.seek(0)
        
        return pdf_buffer.getvalue()

    except Exception as e:
        st.error(f"PDF Creation Error: {str(e)}")
        traceback.print_exc()
        return None

def create_zip(files):
    try:
        temp_dir = tempfile.mkdtemp()
        processed_files = []
        
        strip_mapping = get_strip_mapping()
        numbering_map = parse_multi_numbering(multi_numbering_input)
        skip_list = parse_skip_images(skip_numbering_input)
        
        image_index = 1
        question_number_counter = 0
        
        for file_info in files:
            question_number_to_display = None
            if image_index in numbering_map:
                question_number_to_display = numbering_map[image_index]
            elif image_index not in skip_list:
                question_number_counter += 1
                question_number_to_display = question_number_counter
            
            if question_number_to_display:
                try:
                    img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                    img = enhance_image_opencv(img)
                    
                    strip_fraction = strip_mapping.get(question_number_to_display)
                    if strip_fraction is not None and strip_fraction > 0:
                        original_width = img.width
                        crop_width = int(original_width * (1 - strip_fraction))
                        img = img.crop((original_width - crop_width, 0, original_width, img.height))
                    
                    filename = f"Q{question_number_to_display:03d}.png"
                    filepath = os.path.join(temp_dir, filename)
                    img.save(filepath, "PNG", quality=95)
                    processed_files.append(filepath)
                    
                except Exception as e:
                    st.error(f"Error processing {file_info['name']}: {e}")
            
            image_index += 1
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filepath in processed_files:
                zipf.write(filepath, os.path.basename(filepath))
        
        zip_buffer.seek(0)
        
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return zip_buffer.getvalue(), len(processed_files)
        
    except Exception as e:
        st.error(f"Archive Creation Error: {str(e)}")
        traceback.print_exc()
        return None, 0

# ------------------- GENERATE BUTTONS -------------------
st.markdown("---")
st.markdown("### 🚀 PROCESSING OPTIONS")

if st.session_state.uploaded_files:
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 **GENERATE PDF DOCUMENT**", use_container_width=True, type="primary"):
            if not exam_type or not exam_date:
                st.error("❌ Please enter exam details in the settings panel!")
                if not st.session_state.sidebar_visible:
                    st.info("📝 Click the ☰ button to open settings panel")
            else:
                with st.spinner(f"🔨 Processing {len(st.session_state.uploaded_files)} images into PDF..."):
                    pdf_data = create_pdf(st.session_state.uploaded_files)
                    
                    if pdf_data:
                        filename = f"{sanitize_filename(exam_type)}_{sanitize_filename(exam_date)}_processed.pdf"
                        trigger_auto_download(pdf_data, filename, "pdf")
                        st.success("✅ PDF document created successfully!")
                        st.info("📥 Download will start automatically...")
                        
                        # Create hidden download button for auto-download
                        st.download_button(
                            label=" ",
                            data=pdf_data,
                            file_name=filename,
                            mime="application/pdf",
                            key="auto_download_pdf",
                            use_container_width=True
                        )
                        
                        # Auto-click JavaScript
                        st.markdown("""
                        <script>
                        setTimeout(function() {
                            const buttons = document.querySelectorAll('[data-testid="stDownloadButton"] button');
                            buttons.forEach(btn => {
                                if(btn.textContent.includes('Download') || btn.textContent.trim() === '') {
                                    btn.click();
                                }
                            });
                        }, 500);
                        </script>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("❌ Failed to create PDF document")
    
    with col2:
        if st.button("🗃️ **EXPORT PROCESSED IMAGES**", use_container_width=True, type="secondary"):
            with st.spinner("🔨 Creating archive of processed images..."):
                zip_data, processed_count = create_zip(st.session_state.uploaded_files)
                
                if zip_data:
                    filename = f"{sanitize_filename(exam_type)}_{sanitize_filename(exam_date)}_processed_images.zip"
                    trigger_auto_download(zip_data, filename, "zip")
                    st.success(f"✅ Archive created with {processed_count} processed images!")
                    st.info("📥 Download will start automatically...")
                    
                    # Create hidden download button for auto-download
                    st.download_button(
                        label=" ",
                        data=zip_data,
                        file_name=filename,
                        mime="application/zip",
                        key="auto_download_zip",
                        use_container_width=True
                    )
                    
                    # Auto-click JavaScript
                    st.markdown("""
                    <script>
                    setTimeout(function() {
                        const buttons = document.querySelectorAll('[data-testid="stDownloadButton"] button');
                        buttons.forEach(btn => {
                            if(btn.textContent.includes('Download') || btn.textContent.trim() === '') {
                                btn.click();
                            }
                        });
                    }, 500);
                    </script>
                    """, unsafe_allow_html=True)
                else:
                    st.error("❌ Failed to create ZIP archive")
else:
    st.info("📤 Upload answer sheet images and add them to the processing queue to begin")

# ------------------- COPYRIGHT FOOTER -------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1.5rem; font-size: 0.9rem;'>
    © All Rights Reserved, LFJC 2024 .
</div>
""", unsafe_allow_html=True)

# JavaScript for sidebar toggle
st.components.v1.html("""
<script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'streamlit:setComponentValue' && event.data.value === 'toggle-sidebar') {
            window.location.reload();
        }
    });
</script>
""", height=0)
