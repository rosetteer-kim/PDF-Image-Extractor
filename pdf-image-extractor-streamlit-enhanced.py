import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image
import os
import tempfile
import base64
import cv2
import numpy as np

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

def enhance_graph(image):
    # Convert PIL Image to OpenCV format
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    
    # Apply slight Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Apply adaptive thresholding to separate text and lines
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    
    # Create a mask for text and lines
    text_line_mask = cv2.bitwise_not(thresh)
    
    # Dilate the text and line mask slightly to ensure full coverage
    kernel = np.ones((2,2), np.uint8)
    text_line_mask = cv2.dilate(text_line_mask, kernel, iterations=1)
    
    # Identify potential shaded areas
    _, shaded_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Remove text and lines from the shaded mask
    shaded_mask = cv2.bitwise_and(shaded_mask, cv2.bitwise_not(text_line_mask))
    
    # Apply morphological closing to clean up the shaded mask
    kernel = np.ones((5,5), np.uint8)
    shaded_mask = cv2.morphologyEx(shaded_mask, cv2.MORPH_CLOSE, kernel)
    
    # Enhance shaded areas
    shaded_areas = cv2.bitwise_and(gray, shaded_mask)
    shaded_areas = cv2.equalizeHist(shaded_areas)
    
    # Create result image
    result = cv_image.copy()
    
    # Blend the enhanced shaded areas with the result
    for c in range(3):  # For each color channel
        result[:, :, c] = cv2.addWeighted(result[:, :, c], 1, shaded_areas, 0.3, 0)
    
    # Apply sharpening to the non-text areas
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(result, -1, kernel)
    
    # Combine sharpened image with original text and lines
    result = cv2.bitwise_and(sharpened, sharpened, mask=cv2.bitwise_not(text_line_mask))
    result = cv2.add(result, cv2.bitwise_and(cv_image, cv_image, mask=text_line_mask))
    
    # Increase contrast slightly
    alpha = 1.1  # Contrast control (1.0-3.0)
    beta = 5    # Brightness control (0-100)
    result = cv2.convertScaleAbs(result, alpha=alpha, beta=beta)
    
    # Convert back to PIL Image
    enhanced_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    
    return enhanced_image

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
        st.write("저장할 이미지를 선택하세요:")
        
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
            output_folder = st.text_input("선택한 이미지 저장 폴더 경로를 입력하세요:", value="/Users/kims/Documents/LaTeX-temp/")
            if st.button("선택한 이미지 저장"):
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                
                saved_count = 0
                for i, image_type in selected_indices:
                    image_filename, original_image = st.session_state.extracted_images[i]
                    if image_type == "original":
                        image_to_save = original_image
                        new_filename = f"original_{image_filename}"
                    else:  # enhanced
                        image_to_save = enhance_graph(original_image)
                        new_filename = f"enhanced_{image_filename}"
                    
                    image_path = os.path.join(output_folder, new_filename)
                    image_to_save.save(image_path)
                    saved_count += 1
                
                st.success(f"{saved_count}개의 이미지가 {output_folder}에 저장되었습니다.")
        else:
            st.warning("저장할 이미지를 선택해주세요.")

st.markdown("---")
st.write("Made with ❤️ by Claude 3.5 Sonnet")
