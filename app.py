import streamlit as st
from PIL import Image
import os
from io import BytesIO
import cv2
import numpy as np

def detect_largest_background(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 20, 255])

    lower_blue = np.array([100, 150, 0])
    upper_blue = np.array([140, 255, 255])

    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])

    mask_white = cv2.inRange(hsv, lower_white, upper_white)
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)

    num_labels_white, labels_white, stats_white, _ = cv2.connectedComponentsWithStats(mask_white, connectivity=8)
    num_labels_blue, labels_blue, stats_blue, _ = cv2.connectedComponentsWithStats(mask_blue, connectivity=8)
    num_labels_red, labels_red, stats_red, _ = cv2.connectedComponentsWithStats(mask_red, connectivity=8)

    largest_white_label = 1 + np.argmax(stats_white[1:, cv2.CC_STAT_AREA]) if num_labels_white > 1 else -1
    largest_blue_label = 1 + np.argmax(stats_blue[1:, cv2.CC_STAT_AREA]) if num_labels_blue > 1 else -1
    largest_red_label = 1 + np.argmax(stats_red[1:, cv2.CC_STAT_AREA]) if num_labels_red > 1 else -1

    largest_white_area = stats_white[largest_white_label, cv2.CC_STAT_AREA] if largest_white_label != -1 else 0
    largest_blue_area = stats_blue[largest_blue_label, cv2.CC_STAT_AREA] if largest_blue_label != -1 else 0
    largest_red_area = stats_red[largest_red_label, cv2.CC_STAT_AREA] if largest_red_label != -1 else 0

    if largest_white_area >= largest_blue_area and largest_white_area >= largest_red_area:
        return 'white', labels_white == largest_white_label
    elif largest_blue_area >= largest_white_area and largest_blue_area >= largest_red_area:
        return 'blue', labels_blue == largest_blue_label
    elif largest_red_area >= largest_white_area and largest_red_area >= largest_blue_area:
        return 'red', labels_red == largest_red_label
    else:
        return 'unknown', None

def change_background(image, mask, color):
    if color == '白':
        new_background = [255, 255, 255]
    elif color == '蓝':
        new_background = [67, 142, 219]
    elif color == '红':
        new_background = [255, 0, 0]

    background_image = np.zeros_like(image)
    background_image[:] = new_background

    mask_3ch = np.zeros_like(image)
    mask_3ch[mask] = 255

    masked_image = np.where(mask_3ch == 255, background_image, image)

    return masked_image

def adjust_image(image, size=None, format=None, min_size_kb=None, max_size_kb=None, dpi=None):
    if size:
        image = image.resize(size, Image.LANCZOS)
    
    if format:
        output_format = format.upper()
        if output_format == 'JPG':
            output_format = 'JPEG'
    else:
        output_format = image.format
    
    save_params = {'format': output_format}
    if dpi:
        save_params['dpi'] = (dpi, dpi)
    
    buffer = BytesIO()
    image.save(buffer, **save_params)
    
    if min_size_kb and max_size_kb:
        buffer = adjust_file_size(buffer, min_size_kb, max_size_kb, save_params)
    
    buffer.seek(0)
    return buffer

def adjust_file_size(buffer, min_size_kb, max_size_kb, save_params):
    buffer.seek(0)
    image = Image.open(buffer)
    current_size_kb = len(buffer.getvalue()) / 1024

    quality = 95
    color_modes = ["RGB", "P", "L"]

    for mode in color_modes:
        image = image.convert(mode)
        while current_size_kb > max_size_kb and quality > 10:
            buffer = BytesIO()
            save_params['quality'] = quality
            image.save(buffer, **save_params)
            current_size_kb = len(buffer.getvalue()) / 1024
            quality -= 5
            print(f"Adjusted image quality to {quality}, new size: {current_size_kb:.2f} KB")
        
        while current_size_kb < min_size_kb and quality < 95:
            buffer = BytesIO()
            save_params['quality'] = quality
            image.save(buffer, **save_params)
            current_size_kb = len(buffer.getvalue()) / 1024
            quality += 5
            print(f"Increased image quality to {quality}, new size: {current_size_kb:.2f} KB")

        if min_size_kb <= current_size_kb <= max_size_kb:
            break

    buffer.seek(0)
    return buffer

def estimate_file_size(image, size=None, format='JPEG', dpi=300):
    buffer = BytesIO()
    if format.upper() == 'JPG':
        format = 'JPEG'
    save_params = {'format': format, 'quality': 85}
    if dpi:
        save_params['dpi'] = (dpi, dpi)
    
    if size:
        image = image.resize(size, Image.LANCZOS)
    
    image.save(buffer, **save_params)
    estimated_size = len(buffer.getvalue()) / 1024
    
    return estimated_size

st.title('证件照处理工具')

st.sidebar.title("关于我")
st.sidebar.write("""
大家好，我是阮同学，目前在北京师范大学攻读博士。我平时喜欢编程捣鼓一些有趣的玩意儿。如果你有什么新奇的想法或者对我的作品有什么改进建议，欢迎告诉我！\n商务与学习交流：ruan_bilibili@163.com
""")

uploaded_file = st.file_uploader("上传证件照", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='上传的证件照', use_column_width=True)
    
    st.write("### 调整参数")

    width = st.number_input("宽度 (像素)", min_value=1, value=image.width)
    height = st.number_input("高度 (像素)", min_value=1, value=image.height)
    format = st.selectbox("输出格式", options=["jpg", "png", "bmp", "gif", "tiff"], index=0)
    if format == "保持原格式":
        format = None
    min_size_kb = st.number_input("目标文件最小大小 (KB)", min_value=1, value=50)
    max_size_kb = st.number_input("目标文件最大大小 (KB)", min_value=1, value=100)
    dpi = st.number_input("分辨率 DPI", min_value=1, value=300)

    st.write("### 背景颜色替换")
    bg_color = st.selectbox("选择背景颜色", ["显示原图", "白", "蓝", "红"])

    if st.button("处理证件照"):
        new_size = (width, height)
        image = image.convert('RGB')
        if bg_color != "显示原图":
            np_image = np.array(image)
            background_color, mask = detect_largest_background(np_image)
            if background_color == 'unknown':
                st.write("无法检测背景颜色，请上传白色、蓝色或红色背景的照片")
            else:
                np_image = change_background(np_image, mask, bg_color)
                image = Image.fromarray(np_image)

        estimated_size = estimate_file_size(image, size=new_size, format=format, dpi=dpi)
        st.write(f"预估的文件大小约为：{estimated_size:.2f} KB")
        
        buffer = adjust_image(image, size=new_size, format=format, min_size_kb=min_size_kb, max_size_kb=max_size_kb, dpi=dpi)
        final_size_kb = len(buffer.getvalue()) / 1024

        if min_size_kb <= final_size_kb <= max_size_kb:
            st.write("### 处理后的证件照")
            st.image(buffer, caption='处理后的证件照', use_column_width=True)
            
            output_filename = os.path.splitext(uploaded_file.name)[0] + ('.' + format.lower() if format else os.path.splitext(uploaded_file.name)[1])
            st.download_button(label="下载处理后的证件照", data=buffer, file_name=output_filename, mime="image/" + (format.lower() if format else 'jpeg'))
            st.markdown("---")
            money = Image.open("Image/money.jpg")
            st.image(money, caption="打赏一下吧！", use_column_width=True)
            st.write("""
            谢谢你使用我的作品！如果觉得好用的话，看在UP这么无私奉献的份上，可否支持下UP呢？我会更加努力做出更好更实用的作品的！
            """)
        else:
            st.write(f"生成的文件大小为：{final_size_kb:.2f} KB，不在预期范围内，请调整参数后重试。")




# python /nfs/home/1002_sunbo/RW_Experiments/Personal_project/Photo_Processing_Tools/app.py
