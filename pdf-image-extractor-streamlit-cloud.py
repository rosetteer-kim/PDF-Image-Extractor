import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image
import os
import tempfile
import base64
import cv2
import numpy as np
import zipfile

# 기존의 함수들은 그대로 유지합니다 (extract_images_from_pdf, create_thumbnail, image_to_base64, enhance_graph)

# ZIP 파일 생성 함수 추가
def create_zip_file(images):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for image_filename, image in images:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="PNG")
            zip_file.writestr(image_filename, img_byte_arr.getvalue())
    return zip_buffer

st.set_page_config(layout="wide")
st.title("PDF 이미지 추출 및 개선")

uploaded_file = st.file_uploader("한글(HWP)로 생성한 PDF 파일을 선택하세요", type="pdf")

if uploaded_file is not None:
    st.write("파일이 업로드되었습니다:", uploaded_file.name)

    if 'extracted_images' not in st.session_state:
        st.session_state.extracted_images = None

    if st.button("이미지 추출"):
        with st.spinner("이미지를 추출 중입니다..."):
            st.session_state.extracted_images = extract_images_from_pdf(uploaded_file)
        
        st.success(f"이미지 추출이 완료되었습니다. 총 {len(st.session_state.extracted_images)}개의 이미지가 추출되었습니다.")
    
    if st.session_state.extracted_images:
        st.write("다운로드할 이미지를 선택하세요:")
        
        selected_indices = []
        cols = st.columns(4)  # 4개의 열로 이미지를 표시합니다.
        
        for i, (image_filename, image) in enumerate(st.session_state.extracted_images):
            with cols[i % 4]:
                with st.container():
                    original_image = image.copy()
                    enhanced_image = enhance_graph(image)
                    
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
                        <img src="data:image/png;base64,{image_to_base64(create_thumbnail(enhanced_image.copy(), (150, 150)))}" alt="{image_filename}">
                        <p>{image_filename}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.checkbox("원본", key=f"original_{i}"):
                            selected_indices.append((i, "original"))
                    with col2:
                        if st.checkbox("개선", key=f"enhanced_{i}"):
                            selected_indices.append((i, "enhanced"))
                    with col3:
                        if st.button("비교", key=f"compare_{i}"):
                            st.image([original_image, enhanced_image], caption=["원본", "개선"], use_column_width=True)
        
        if selected_indices:
            if st.button("선택한 이미지 다운로드"):
                images_to_download = []
                for i, image_type in selected_indices:
                    image_filename, original_image = st.session_state.extracted_images[i]
                    if image_type == "original":
                        image_to_save = original_image
                        new_filename = f"original_{image_filename}"
                    else:  # enhanced
                        image_to_save = enhance_graph(original_image)
                        new_filename = f"enhanced_{image_filename}"
                    images_to_download.append((new_filename, image_to_save))
                
                zip_buffer = create_zip_file(images_to_download)
                
                st.download_button(
                    label="ZIP 파일 다운로드",
                    data=zip_buffer.getvalue(),
                    file_name="extracted_images.zip",
                    mime="application/zip"
                )
                
                st.success(f"{len(images_to_download)}개의 이미지가 ZIP 파일에 포함되었습니다. 다운로드 버튼을 클릭하여 저장하세요.")
        else:
            st.warning("다운로드할 이미지를 선택해주세요.")

st.markdown("---")
st.write("Made with ❤️ by Claude 3.5 Sonnet")
