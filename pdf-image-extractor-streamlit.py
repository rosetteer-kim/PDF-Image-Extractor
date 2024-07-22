import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image
import os
import tempfile
import base64

def extract_images_from_pdf(pdf_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(pdf_file.getvalue())
        tmp_pdf_path = tmp_pdf.name

    pdf_document = fitz.open(tmp_pdf_path)
    images = []

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        page_images = page.get_images()

        for img_index, img in enumerate(page_images):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]

            image = Image.open(io.BytesIO(image_bytes))
            image_filename = f"page{page_num + 1}_img{img_index + 1}.{ext}"
            
            images.append((image_filename, image))

    pdf_document.close()
    os.unlink(tmp_pdf_path)
    return images

def create_thumbnail(image, size=(100, 100)):
    image.thumbnail(size)
    return image

def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

st.set_page_config(layout="wide")
st.title("PDF 이미지 추출")

uploaded_file = st.file_uploader("PDF 파일을 선택하세요", type="pdf")

if uploaded_file is not None:
    st.write("파일이 업로드되었습니다:", uploaded_file.name)

    if 'extracted_images' not in st.session_state:
        st.session_state.extracted_images = None

    if st.button("이미지 추출"):
        with st.spinner("이미지를 추출 중입니다..."):
            st.session_state.extracted_images = extract_images_from_pdf(uploaded_file)
        
        st.success(f"이미지 추출이 완료되었습니다. 총 {len(st.session_state.extracted_images)}개의 이미지가 추출되었습니다.")
    
    if st.session_state.extracted_images:
        st.write("저장할 이미지를 선택하세요:")
        
        selected_indices = []
        cols = st.columns(4)  # 4개의 열로 이미지를 표시합니다.
        
        for i, (image_filename, image) in enumerate(st.session_state.extracted_images):
            with cols[i % 4]:
                with st.container():
                    st.markdown(f"""
                    <style>
                        .image-card {{
                            border: 1px solid #ddd;
                            border-radius: 5px;
                            padding: 10px;
                            margin-bottom: 20px;
                        }}
                        .image-card img {{
                            width: 100%;
                            height: 150px;
                            object-fit: contain;
                        }}
                    </style>
                    <div class="image-card">
                        <img src="data:image/png;base64,{image_to_base64(create_thumbnail(image.copy(), (150, 150)))}" alt="{image_filename}">
                        <p>{image_filename}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.checkbox("선택", key=f"select_{i}"):
                            selected_indices.append(i)
                    with col2:
                        if st.button("전체 보기", key=f"view_{i}"):
                            st.image(image, caption=image_filename, use_column_width=True)
        
        if selected_indices:
            output_folder = st.text_input("선택한 이미지 저장 폴더 경로를 입력하세요:", value="/Users/kims/Documents/LaTeX-temp/")
            if st.button("선택한 이미지 저장"):
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                
                saved_count = 0
                for i in selected_indices:
                    image_filename, image = st.session_state.extracted_images[i]
                    image_path = os.path.join(output_folder, image_filename)
                    image.save(image_path)
                    saved_count += 1
                
                st.success(f"{saved_count}개의 이미지가 {output_folder}에 저장되었습니다.")
        else:
            st.warning("저장할 이미지를 선택해주세요.")

st.markdown("---")
st.write("Made with ❤️ by Claude 3.5 Sonnet")
