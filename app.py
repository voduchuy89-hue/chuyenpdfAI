import streamlit as st
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import io
import os
from openai import OpenAI

# ========================================================================================
# CẤU HÌNH TRANG
# ========================================================================================
st.set_page_config(
    page_title="Trợ lý OCR Thông minh",
    page_icon="📄",
    layout="wide"
)

# ========================================================================================
# HÀM HỖ TRỢ (LOGIC XỬ LÝ)
# ========================================================================================

@st.cache_data  # Sử dụng cache để không xử lý lại file đã xử lý
def process_file(file_bytes, file_extension):
    """
    Hàm trung tâm xử lý file đầu vào (ảnh hoặc PDF) và trả về văn bản được trích xuất.
    Mặc định sử dụng chế độ song ngữ Việt + Anh.
    """
    # Cố định ngôn ngữ xử lý là Việt + Anh
    lang_code = "vie+eng"
    
    extracted_text = ""
    try:
        if file_extension == 'pdf':
            images = convert_from_bytes(file_bytes)
            all_text = []
            progress_bar = st.progress(0, text="Đang xử lý file PDF...")
            for i, img in enumerate(images):
                all_text.append(pytesseract.image_to_string(img, lang=lang_code))
                progress_bar.progress((i + 1) / len(images))
            extracted_text = "\n\n--- Hết trang ---\n\n".join(all_text)
        elif file_extension in ['png', 'jpg', 'jpeg']:
            image = Image.open(io.BytesIO(file_bytes))
            extracted_text = pytesseract.image_to_string(image, lang=lang_code)
        return extracted_text, None
    except Exception as e:
        return None, f"Đã xảy ra lỗi trong quá trình xử lý: {e}"


def call_openai_proofread(text: str) -> str:
    """
    Gọi OpenAI để kiểm tra lỗi, chỉnh sửa văn bản sau OCR.
    Ưu tiên lấy khóa từ Streamlit secrets (OPENAI_API_KEY).
    """
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        raise RuntimeError(
            "Chưa cấu hình OpenAI. Vào Manage app → Settings → Secrets và thêm OPENAI_API_KEY."
        )

    # Đảm bảo thư viện OpenAI đọc được API key từ biến môi trường
    os.environ["OPENAI_API_KEY"] = api_key

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là trợ lý giúp chỉnh sửa văn bản tiếng Việt và tiếng Anh "
                    "được trích xuất từ OCR. Hãy sửa lỗi chính tả, dấu câu và cách "
                    "xuống dòng hợp lý. Chỉ trả về văn bản đã chỉnh sửa, không giải thích gì thêm."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content

# ========================================================================================
# GIAO DIỆN CHÍNH CỦA ỨNG DỤNG
# ========================================================================================

st.title("📄 Trợ lý OCR Thông minh")
st.write("Trích xuất văn bản từ file ảnh hoặc PDF. Mặc định xử lý song ngữ Tiếng Việt và Tiếng Anh.")

# Cột cho phần tải lên và hướng dẫn
col1, col2 = st.columns([2, 1])

with col1:
    # Tiện ích tải file đã được đơn giản hóa
    uploaded_files = st.file_uploader(
        "Tải lên MỘT hoặc NHIỀU file...",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )

with col2:
    with st.expander("💡 Mẹo sử dụng", expanded=True):
        st.info("""
        - Ứng dụng được tối ưu để nhận dạng tài liệu có cả Tiếng Việt và Tiếng Anh.
        - Bạn có thể kéo thả nhiều file vào đây cùng một lúc.
        - Để có kết quả tốt nhất, hãy sử dụng ảnh rõ nét, chữ không bị mờ.
        """)

# Xử lý nếu người dùng đã tải file lên
if uploaded_files:
    st.markdown("---")
    st.header("Kết quả trích xuất")

    for uploaded_file in uploaded_files:
        with st.expander(f"Kết quả cho file: {uploaded_file.name}", expanded=True):
            with st.spinner(f"Đang xử lý '{uploaded_file.name}'..."):
                file_bytes = uploaded_file.getvalue()
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                # Gọi hàm xử lý đã được đơn giản hóa
                text, error = process_file(file_bytes, file_extension)

            if error:
                st.error(error)
            else:
                st.text_area("Văn bản:", text, height=300, key=f"text_{uploaded_file.name}")
                st.download_button(
                    label="📥 Tải kết quả này",
                    data=text.encode('utf-8'),
                    file_name=f"ket_qua_{uploaded_file.name}.txt",
                    mime="text/plain",
                    key=f"download_{uploaded_file.name}"
                )

                use_ai = st.button(
                    "✨ Dùng OpenAI kiểm tra và sửa lỗi văn bản",
                    key=f"ai_fix_{uploaded_file.name}",
                )

                if use_ai:
                    try:
                        with st.spinner("OpenAI đang kiểm tra và hoàn thiện văn bản..."):
                            fixed_text = call_openai_proofread(text)

                        st.text_area(
                            "Văn bản đã được AI hiệu đính:",
                            fixed_text,
                            height=300,
                            key=f"text_ai_{uploaded_file.name}",
                        )
                        st.download_button(
                            label="📥 Tải văn bản đã hiệu đính",
                            data=fixed_text.encode('utf-8'),
                            file_name=f"ket_qua_AI_{uploaded_file.name}.txt",
                            mime="text/plain",
                            key=f"download_ai_{uploaded_file.name}",
                        )
                    except Exception as e:
                        st.error(f"Không gọi được OpenAI: {e}")
