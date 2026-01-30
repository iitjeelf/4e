import os, io, re, zipfile, shutil, tempfile, traceback
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import streamlit as st
import base64

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
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .auto-download-btn {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        text-decoration: none;
        display: inline-block;
        margin: 5px;
    }
    .auto-download-btn:hover {
        background: linear-gradient(135deg, #218838 0%, #1aa179 100%);
    }
</style>
""", unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown("""
<div class="main-header">
    <h1>🎓 LFJC PAPER PROCESSING SYSTEM</h1>
    <p>Professional Answer Sheet Processing | Auto-Download Enabled</p>
</div>
""", unsafe_allow_html=True)

# ------------------- SESSION STATE -------------------
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

# ------------------- LOCAL SAVE FOLDER -------------------
LOCAL_SAVE_FOLDER = "./processed_files/"
os.makedirs(LOCAL_SAVE_FOLDER, exist_ok=True)

# ------------------- HELPER FUNCTIONS -------------------
def enhance_image_opencv(pil_img):
    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 29, 17)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(thresh, -1, kernel)
    return Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB))

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def sanitize_filename(name):
    cleaned_name = re.sub(r'[^\w\s.-]', '_', name)
    cleaned_name = re.sub(r'\s+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')
    return cleaned_name or "untitled"

def create_download_link(file_data, filename, file_type):
    """Create automatic download link"""
    b64 = base64.b64encode(file_data).decode()
    mime_type = "application/pdf" if file_type == "pdf" else "application/zip"
    
    # Create a download link that auto-clicks
    download_html = f'''
    <a href="data:{mime_type};base64,{b64}" 
       download="{filename}" 
       id="auto-download-{file_type}"
       class="auto-download-btn">
       📥 Download {filename}
    </a>
    <script>
        document.getElementById('auto-download-{file_type}').click();
    </script>
    '''
    return download_html

def save_to_local(file_data, filename):
    """Save file to local folder"""
    try:
        filepath = os.path.join(LOCAL_SAVE_FOLDER, filename)
        with open(filepath, 'wb') as f:
            f.write(file_data)
        return True, filepath
    except Exception as e:
        return False, str(e)

def create_pdf(files, exam_type, exam_date):
    """Create PDF from images"""
    try:
        A4_WIDTH, A4_HEIGHT = int(8.27 * 300), int(11.69 * 300)
        
        pdf_pages = []
        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        
        # Simple header
        draw = ImageDraw.Draw(current_page)
        try:
            font = ImageFont.load_default()
            draw.text((100, 50), f"LFJC - {exam_type}", fill="black", font=font)
            draw.text((100, 80), f"Date: {exam_date}", fill="black", font=font)
        except:
            draw.text((100, 50), f"LFJC - {exam_type}", fill="black")
            draw.text((100, 80), f"Date: {exam_date}", fill="black")
        
        y_offset = 150
        
        files.sort(key=lambda x: natural_sort_key(x['name']))
        
        for idx, file_info in enumerate(files, 1):
            try:
                img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                # Resize to fit
                scale = min((A4_WIDTH-200)/img.width, (A4_HEIGHT-200)/img.height) * 0.7
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Check if need new page
                if y_offset + new_size[1] > A4_HEIGHT - 100:
                    pdf_pages.append(current_page)
                    current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
                    y_offset = 100
                
                x = (A4_WIDTH - new_size[0]) // 2
                current_page.paste(img, (x, y_offset))
                y_offset += new_size[1] + 20
                
            except Exception as e:
                st.error(f"Error processing image {idx}: {e}")
                continue
        
        pdf_pages.append(current_page)
        
        # Save to buffer
        pdf_buffer = io.BytesIO()
        pdf_pages[0].save(pdf_buffer, format='PDF', save_all=True, 
                         append_images=pdf_pages[1:])
        pdf_buffer.seek(0)
        
        return pdf_buffer.getvalue()
        
    except Exception as e:
        st.error(f"PDF Creation Error: {str(e)}")
        return None

def create_zip(files):
    """Create ZIP of images"""
    try:
        temp_dir = tempfile.mkdtemp()
        
        for idx, file_info in enumerate(files, 1):
            try:
                img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                filename = f"image_{idx:03d}.png"
                filepath = os.path.join(temp_dir, filename)
                img.save(filepath, "PNG", quality=90)
                
            except Exception as e:
                st.error(f"Error processing image {idx}: {e}")
                continue
        
        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    zipf.write(filepath, file)
        
        zip_buffer.seek(0)
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return zip_buffer.getvalue()
        
    except Exception as e:
        st.error(f"ZIP Creation Error: {str(e)}")
        return None

# ------------------- MAIN APP -------------------
with st.sidebar:
    st.markdown("### ⚙️ SETTINGS")
    exam_type = st.text_input("Exam Type", "", placeholder="e.g., Semester I - Physics")
    exam_date = st.text_input("Exam Date", "", placeholder="DD-MM-YYYY")
    
    st.markdown("---")
    st.markdown("**Auto-downloads enabled**")
    st.info("Files will download automatically when ready")

st.markdown("### 📁 UPLOAD ANSWER SHEETS")

uploaded_files = st.file_uploader(
    "Choose images (PNG, JPG, JPEG)",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("📥 ADD TO PROCESSING QUEUE", use_container_width=True):
        for uploaded_file in uploaded_files:
            if not any(f['name'] == uploaded_file.name for f in st.session_state.uploaded_files):
                st.session_state.uploaded_files.append({
                    'name': uploaded_file.name,
                    'bytes': uploaded_file.read()
                })
        st.success(f"✅ Added {len(uploaded_files)} files")
        st.rerun()

if st.session_state.uploaded_files:
    st.markdown(f"### 📋 QUEUE ({len(st.session_state.uploaded_files)} files)")
    for file_info in st.session_state.uploaded_files:
        st.text(f"📄 {file_info['name']}")
    
    st.markdown("---")
    
    if exam_type and exam_date:
        if st.button("🔄 PROCESS & AUTO-DOWNLOAD", type="primary", use_container_width=True):
            with st.spinner("Processing files..."):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Create PDF
                pdf_data = create_pdf(st.session_state.uploaded_files, exam_type, exam_date)
                
                # Create ZIP
                zip_data = create_zip(st.session_state.uploaded_files)
                
                if pdf_data and zip_data:
                    # Create filenames
                    pdf_filename = f"LFJC_{sanitize_filename(exam_type)}_{timestamp}.pdf"
                    zip_filename = f"LFJC_{sanitize_filename(exam_type)}_{timestamp}.zip"
                    
                    # Save locally
                    pdf_saved, pdf_path = save_to_local(pdf_data, pdf_filename)
                    zip_saved, zip_path = save_to_local(zip_data, zip_filename)
                    
                    # Show success
                    st.success("✅ Files processed successfully!")
                    
                    # Show local save status
                    if pdf_saved:
                        st.info(f"📄 PDF saved to: {pdf_path}")
                    if zip_saved:
                        st.info(f"🗃️ ZIP saved to: {zip_path}")
                    
                    # Create auto-download links
                    st.markdown("### 📥 DOWNLOADING FILES...")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(create_download_link(pdf_data, pdf_filename, "pdf"), unsafe_allow_html=True)
                    with col2:
                        st.markdown(create_download_link(zip_data, zip_filename, "zip"), unsafe_allow_html=True)
                    
                    # Manual download buttons as backup
                    st.markdown("---")
                    st.markdown("### 🔄 MANUAL DOWNLOAD (BACKUP)")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        st.download_button(
                            "📄 DOWNLOAD PDF",
                            pdf_data,
                            pdf_filename,
                            "application/pdf",
                            use_container_width=True
                        )
                    with col4:
                        st.download_button(
                            "🗃️ DOWNLOAD ZIP",
                            zip_data,
                            zip_filename,
                            "application/zip",
                            use_container_width=True
                        )
                    
                else:
                    st.error("❌ Failed to create files")
    else:
        st.warning("⚠️ Please enter Exam Type and Date")

# ------------------- CLEAR QUEUE BUTTON -------------------
if st.session_state.uploaded_files:
    if st.button("🗑️ CLEAR PROCESSING QUEUE", use_container_width=True):
        st.session_state.uploaded_files = []
        st.success("✅ Queue cleared")
        st.rerun()

# ------------------- FOOTER -------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>© 2024 LFJC Paper Processing System | Auto-Download Enabled</p>
</div>
""", unsafe_allow_html=True)
