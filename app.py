import os, io, re, zipfile, shutil, tempfile, traceback
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import streamlit as st
import base64

# ------------------- GOOGLE DRIVE SETUP -------------------
# Using PyDrive2 which is simpler than Google Cloud Console
try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    st.warning("Google Drive integration requires pydrive2. Install with: pip install pydrive2")

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
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .status-success {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #28a745;
    }
    .status-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #ffc107;
    }
    .status-error {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #dc3545;
    }
    .download-section {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 2px dashed #4a90e2;
    }
    .auto-download-btn {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        font-weight: bold;
        border: none;
    }
    .auto-download-btn:hover {
        background: linear-gradient(135deg, #218838 0%, #1aa179 100%);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown("""
<div class="main-header">
    <h1>🎓 LFJC PAPER PROCESSING SYSTEM</h1>
    <p>Professional Answer Sheet Processing | Little Flower Junior College, Uppal</p>
    <p><small>📥 Auto-Download Enabled | ☁️ Auto-Save to Google Drive | 💾 Auto-Save to Server</small></p>
</div>
""", unsafe_allow_html=True)

# ------------------- SESSION STATE -------------------
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'last_generated_pdf' not in st.session_state:
    st.session_state.last_generated_pdf = None
if 'last_generated_zip' not in st.session_state:
    st.session_state.last_generated_zip = None
if 'google_drive_connected' not in st.session_state:
    st.session_state.google_drive_connected = False
if 'drive_service' not in st.session_state:
    st.session_state.drive_service = None

# ------------------- CONFIGURATION -------------------
# Your Google Drive Folder ID
GOOGLE_DRIVE_FOLDER_ID = "1JT7hvyfDR4SXKEZR7sMwcccZU_LUFj8u"

# Local save folder (change this to your desired path)
LOCAL_SAVE_FOLDER = "C:/LFJC_Processed/"  # For Windows
# LOCAL_SAVE_FOLDER = "/home/user/LFJC_Processed/"  # For Linux/Mac

# Create local save folder if it doesn't exist
os.makedirs(LOCAL_SAVE_FOLDER, exist_ok=True)

# ------------------- GOOGLE DRIVE FUNCTIONS -------------------
def authenticate_google_drive():
    """Authenticate with Google Drive using PyDrive2"""
    try:
        # Create minimal settings for authentication
        settings = {
            "client_config_backend": "settings",
            "client_config": {
                "client_id": "202264815644.apps.googleusercontent.com",
                "client_secret": "X4Z3ca8xfWDb1Voo-F9a7ZxJ"
            },
            "save_credentials": True,
            "save_credentials_backend": "file",
            "save_credentials_file": "credentials.json",
            "get_refresh_token": True,
            "oauth_scope": ["https://www.googleapis.com/auth/drive.file"]
        }
        
        # Save settings to file
        import yaml
        with open('settings.yaml', 'w') as f:
            yaml.dump(settings, f)
        
        # Authenticate
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()  # Creates local webserver for auth
        drive = GoogleDrive(gauth)
        
        st.session_state.drive_service = drive
        st.session_state.google_drive_connected = True
        return drive
        
    except Exception as e:
        st.error(f"Google Drive authentication failed: {str(e)}")
        return None

def upload_to_google_drive(file_data, filename, folder_id):
    """Upload file to Google Drive"""
    try:
        if not st.session_state.drive_service:
            return {"success": False, "error": "Not connected to Google Drive"}
        
        drive = st.session_state.drive_service
        
        # Create a temporary file
        temp_path = f"temp_{filename}"
        with open(temp_path, 'wb') as f:
            f.write(file_data)
        
        # Create file metadata
        file_metadata = {
            'title': filename,
            'parents': [{'id': folder_id}]
        }
        
        # Create and upload file
        file_drive = drive.CreateFile(file_metadata)
        file_drive.SetContentFile(temp_path)
        file_drive.Upload()
        
        # Get file URL
        file_drive.InsertPermission({
            'type': 'anyone',
            'value': 'anyone',
            'role': 'reader'
        })
        file_url = f"https://drive.google.com/file/d/{file_drive['id']}/view"
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "success": True, 
            "url": file_url,
            "filename": filename
        }
        
    except Exception as e:
        return {"success": False, "error": str(e), "filename": filename}

# ------------------- AUTO-SAVE FUNCTIONS -------------------
def save_to_local_folder(file_data, filename, folder_path):
    """Save file to local folder"""
    try:
        filepath = os.path.join(folder_path, filename)
        with open(filepath, 'wb') as f:
            f.write(file_data)
        
        return {
            "success": True,
            "path": filepath,
            "filename": filename
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filename": filename
        }

def create_download_link(file_data, filename, file_type):
    """Create automatic download link"""
    b64 = base64.b64encode(file_data).decode()
    
    if file_type == "pdf":
        mime_type = "application/pdf"
    else:  # zip
        mime_type = "application/zip"
    
    return f'<a href="data:{mime_type};base64,{b64}" download="{filename}" class="auto-download-btn">📥 Download {filename}</a>'

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
    cleaned_name = re.sub(r'[^À-῿Ⰰ-퟿豈-﷏\w\s.-]', '_', name)
    cleaned_name = re.sub(r'\s+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')
    if not cleaned_name:
        return "untitled"
    return cleaned_name

# ------------------- SETUP SIDEBAR -------------------
with st.sidebar:
    st.markdown("### ⚙️ SETTINGS")
    
    # Exam Details
    exam_type = st.text_input("Exam Type", "", placeholder="e.g., Semester I - Physics")
    exam_date = st.text_input("Exam Date (DD-MM-YYYY)", "", placeholder="15-01-2024")
    
    st.markdown("---")
    
    # Google Drive Connection
    st.markdown("### ☁️ GOOGLE DRIVE")
    
    if not st.session_state.google_drive_connected and GOOGLE_DRIVE_AVAILABLE:
        if st.button("🔗 Connect to Google Drive"):
            with st.spinner("Connecting to Google Drive..."):
                if authenticate_google_drive():
                    st.success("✅ Connected to Google Drive!")
                    st.rerun()
                else:
                    st.error("❌ Failed to connect")
    
    if st.session_state.google_drive_connected:
        st.success("✅ Connected to Google Drive")
        st.info(f"Folder ID: {GOOGLE_DRIVE_FOLDER_ID}")
    
    st.markdown("---")
    
    # Local Save Info
    st.markdown("### 💾 LOCAL SAVE")
    st.info(f"Files will also save to:\n`{LOCAL_SAVE_FOLDER}`")
    
    st.markdown("---")
    
    # Quick Help
    with st.expander("📖 How It Works"):
        st.markdown("""
        **Automatic Saves:**
        1. **Auto-download**: Files download to your computer immediately
        2. **Google Drive**: Saves to LFJC folder automatically
        3. **Local Server**: Saves to server folder as backup
        
        **Note**: First-time Google Drive connection requires browser authentication
        """)

# ------------------- MAIN INTERFACE -------------------
st.markdown("### 📁 UPLOAD ANSWER SHEETS")

uploaded_files = st.file_uploader(
    "Choose answer sheet images (PNG, JPG, JPEG)",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True,
    help="Select multiple images"
)

if uploaded_files:
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 ADD TO QUEUE", use_container_width=True):
            for uploaded_file in uploaded_files:
                if not any(f['name'] == uploaded_file.name for f in st.session_state.uploaded_files):
                    st.session_state.uploaded_files.append({
                        'name': uploaded_file.name,
                        'bytes': uploaded_file.read()
                    })
            st.success(f"✅ Added {len(uploaded_files)} files to queue")
            st.rerun()
    
    with col2:
        if st.button("🗑️ CLEAR QUEUE", use_container_width=True):
            st.session_state.uploaded_files = []
            st.success("✅ Queue cleared")
            st.rerun()

# Show queue
if st.session_state.uploaded_files:
    st.markdown(f"### 📋 QUEUE ({len(st.session_state.uploaded_files)} files)")
    for file_info in st.session_state.uploaded_files:
        st.markdown(f"📄 {file_info['name']}")

# ------------------- PROCESSING FUNCTIONS -------------------
def create_pdf(files):
    """Create PDF from images"""
    try:
        A4_WIDTH, A4_HEIGHT = int(8.27 * 300), int(11.69 * 300)
        
        # Create PDF pages
        pdf_pages = []
        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        
        # Sort files
        files.sort(key=lambda x: natural_sort_key(x['name']))
        
        # Simple PDF creation (simplified from your original code)
        for file_info in files:
            try:
                img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                # Resize to fit page
                scale = min(A4_WIDTH/img.width, A4_HEIGHT/img.height) * 0.8
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Paste on page
                x = (A4_WIDTH - new_size[0]) // 2
                y = (A4_HEIGHT - new_size[1]) // 2
                current_page.paste(img, (x, y))
                
            except Exception as e:
                st.error(f"Error processing {file_info['name']}: {e}")
                continue
        
        pdf_pages.append(current_page)
        
        # Save to buffer
        pdf_buffer = io.BytesIO()
        pdf_pages[0].save(pdf_buffer, format='PDF', save_all=True, 
                         append_images=pdf_pages[1:], resolution=300.0)
        pdf_buffer.seek(0)
        
        return pdf_buffer.getvalue()
        
    except Exception as e:
        st.error(f"PDF Creation Error: {str(e)}")
        return None

def create_zip(files):
    """Create ZIP of processed images"""
    try:
        temp_dir = tempfile.mkdtemp()
        processed_files = []
        
        for idx, file_info in enumerate(files, 1):
            try:
                img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                filename = f"Image_{idx:03d}.png"
                filepath = os.path.join(temp_dir, filename)
                img.save(filepath, "PNG", quality=95)
                processed_files.append(filepath)
                
            except Exception as e:
                st.error(f"Error processing {file_info['name']}: {e}")
                continue
        
        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filepath in processed_files:
                zipf.write(filepath, os.path.basename(filepath))
        
        zip_buffer.seek(0)
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return zip_buffer.getvalue(), len(processed_files)
        
    except Exception as e:
        st.error(f"ZIP Creation Error: {str(e)}")
        return None, 0

# ------------------- AUTO PROCESS BUTTON -------------------
st.markdown("---")
st.markdown("### 🚀 AUTO PROCESS & DOWNLOAD")

if st.session_state.uploaded_files and exam_type and exam_date:
    if st.button("🔄 PROCESS & AUTO-DOWNLOAD ALL", type="primary", use_container_width=True):
        
        with st.spinner("Processing files..."):
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Generate PDF
            pdf_data = create_pdf(st.session_state.uploaded_files)
            
            # Generate ZIP
            zip_data, processed_count = create_zip(st.session_state.uploaded_files)
            
            if pdf_data and zip_data:
                # Create filenames
                pdf_filename = f"LFJC_{sanitize_filename(exam_type)}_{timestamp}.pdf"
                zip_filename = f"LFJC_{sanitize_filename(exam_type)}_{timestamp}_Images.zip"
                
                # Store in session state
                st.session_state.last_generated_pdf = pdf_data
                st.session_state.last_generated_zip = zip_data
                
                # Display download section
                st.markdown('<div class="download-section">', unsafe_allow_html=True)
                st.markdown("### 📥 FILES READY FOR DOWNLOAD")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Auto-download PDF
                    pdf_download = create_download_link(pdf_data, pdf_filename, "pdf")
                    st.markdown(pdf_download, unsafe_allow_html=True)
                    
                with col2:
                    # Auto-download ZIP
                    zip_download = create_download_link(zip_data, zip_filename, "zip")
                    st.markdown(zip_download, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Status messages
                status_msgs = []
                
                # 1. Save to Local Folder
                local_pdf = save_to_local_folder(pdf_data, pdf_filename, LOCAL_SAVE_FOLDER)
                local_zip = save_to_local_folder(zip_data, zip_filename, LOCAL_SAVE_FOLDER)
                
                if local_pdf['success']:
                    status_msgs.append(f"✅ PDF saved to server: {local_pdf['path']}")
                else:
                    status_msgs.append(f"⚠️ Local PDF save failed: {local_pdf['error']}")
                
                if local_zip['success']:
                    status_msgs.append(f"✅ ZIP saved to server: {local_zip['path']}")
                else:
                    status_msgs.append(f"⚠️ Local ZIP save failed: {local_zip['error']}")
                
                # 2. Save to Google Drive (if connected)
                if st.session_state.google_drive_connected:
                    drive_pdf = upload_to_google_drive(pdf_data, pdf_filename, GOOGLE_DRIVE_FOLDER_ID)
                    drive_zip = upload_to_google_drive(zip_data, zip_filename, GOOGLE_DRIVE_FOLDER_ID)
                    
                    if drive_pdf['success']:
                        status_msgs.append(f"✅ PDF uploaded to Google Drive: [View]({drive_pdf['url']})")
                    else:
                        status_msgs.append(f"⚠️ Google Drive PDF failed: {drive_pdf['error']}")
                    
                    if drive_zip['success']:
                        status_msgs.append(f"✅ ZIP uploaded to Google Drive: [View]({drive_zip['url']})")
                    else:
                        status_msgs.append(f"⚠️ Google Drive ZIP failed: {drive_zip['error']}")
                else:
                    status_msgs.append("ℹ️ Google Drive not connected. Connect in settings to enable auto-upload.")
                
                # Display all status messages
                st.markdown("### 📋 SAVE STATUS")
                for msg in status_msgs:
                    if "✅" in msg:
                        st.markdown(f'<div class="status-success">{msg}</div>', unsafe_allow_html=True)
                    elif "⚠️" in msg:
                        st.markdown(f'<div class="status-warning">{msg}</div>', unsafe_allow_html=True)
                    else:
                        st.info(msg)
                
                # File info
                st.markdown("### 📊 FILE INFO")
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("PDF Size", f"{len(pdf_data) / (1024*1024):.1f} MB")
                with col_info2:
                    st.metric("Images Processed", processed_count)
                
            else:
                st.error("❌ Failed to create files")
        
elif not exam_type or not exam_date:
    st.warning("⚠️ Please enter Exam Type and Date in the sidebar")
else:
    st.info("📤 Upload answer sheets and add to queue to begin")

# ------------------- MANUAL DOWNLOAD (BACKUP) -------------------
if st.session_state.last_generated_pdf or st.session_state.last_generated_zip:
    st.markdown("---")
    st.markdown("### 🔄 MANUAL DOWNLOAD (BACKUP)")
    
    col_manual1, col_manual2 = st.columns(2)
    
    with col_manual1:
        if st.session_state.last_generated_pdf:
            st.download_button(
                label="📄 DOWNLOAD PDF",
                data=st.session_state.last_generated_pdf,
                file_name=f"LFJC_Backup_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    
    with col_manual2:
        if st.session_state.last_generated_zip:
            st.download_button(
                label="🗃️ DOWNLOAD ZIP",
                data=st.session_state.last_generated_zip,
                file_name=f"LFJC_Backup_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
                use_container_width=True
            )

# ------------------- FOOTER -------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1.5rem;'>
    <p>© 2024 LFJC Paper Processing System | Auto-Save Enabled</p>
    <p><small>📥 Auto-download | ☁️ Google Drive Auto-save | 💾 Server Backup</small></p>
</div>
""", unsafe_allow_html=True)

# ------------------- JAVASCRIPT FOR AUTO-DOWNLOAD -------------------
st.components.v1.html("""
<script>
    // Auto-click download links after a short delay
    setTimeout(function() {
        const downloadLinks = document.querySelectorAll('.auto-download-btn');
        downloadLinks.forEach(link => {
            link.click();
        });
    }, 1000);
</script>
""", height=0)
