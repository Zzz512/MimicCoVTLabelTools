from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QScrollArea, QMainWindow, QFrame, QTextEdit, QFileDialog, QPushButton)
from PyQt5.QtGui import QPixmap, QImage, QTextCharFormat, QFont, QColor
from PyQt5.QtCore import Qt
from PIL import Image, ImageDraw
import sys
import random
import json
import base64
from io import BytesIO
import copy
import numpy as np
import os
from .label_config import cls2type

def convert_nested_to_int(nested_list):
    """递归将嵌套列表中的所有元素转换为整数"""
    if isinstance(nested_list, list):
        return [convert_nested_to_int(item) for item in nested_list]
    else:
        try:
            return int(nested_list)
        except ValueError:
            return nested_list  # 如果无法转换为整数，保留原始值


def flatten(lst):
    return [item for sublist in lst for item in sublist]


def resize_image(image: Image.Image, max_width: int, max_height: int):
    """
    Resize the image to fit within the specified dimensions, maintaining aspect ratio.
    Keeps lines and points intact by resizing through nearest neighbor interpolation, followed by Lanczos.
    """
    # 计算缩放比例以适应最大尺寸
    ratio = min(max_width / image.width, max_height / image.height)
    new_size = (int(image.width * ratio), (int(image.height * ratio)))

    # 使用最近邻缩放
    nearest_resized = image.resize(new_size, Image.NEAREST)

    # 使用Lanczos平滑处理
    lanczos_resized = nearest_resized.resize(new_size, Image.LANCZOS)

    return lanczos_resized

def clean_sentence(sentence):
    # 指定要删除的字符
    characters_to_remove = "\t\n ."
    # 使用strip方法删除两端的指定字符
    cleaned_sentence = sentence.strip(characters_to_remove)
    return cleaned_sentence

def get_unique_elements(a_list, b_list):
    # 找出存在于a_list但不存在于b_list的元素
    unique_to_a = [item for item in a_list if item not in b_list]
    # 找出存在于b_list但不存在于a_list的元素
    unique_to_b = [item for item in b_list if item not in a_list]
    
    return unique_to_a, unique_to_b

def remove_duplicates(lst):
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

class AnimatedDisplay(QMainWindow):
    def __init__(self, items=None, *args, **kwargs):
        super(AnimatedDisplay, self).__init__(*args, **kwargs)

        self.setWindowTitle("Image and Text Display")
        self.setGeometry(100, 100, 800, 1000)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area_widget = QWidget()
        self.scroll_area.setWidget(self.scroll_area_widget)
        self.scroll_area_layout = QVBoxLayout(self.scroll_area_widget)

        # Set up the main layout
        self.layout.addWidget(self.scroll_area)
        
        self.current_text_label = None
        self.current_image_label = None
        self.current_image = None

        # Warning log display
        self.warning_log_display = QTextEdit()
        self.warning_log_display.setReadOnly(True)
        self.warning_log_display.setFixedHeight(200)  # 设置固定高度
        self.layout.addWidget(self.warning_log_display)

        # Folder selection button
        self.folder_button = QPushButton("Select Folder", self)
        self.folder_button.clicked.connect(self.select_folder)
        self.layout.addWidget(self.folder_button)

        if items is not None:
            self.set_items(items)

        self.current_index = 0
        self.items = []
        self.hist_imgs = []
        self.log_content = []
    
    def clear_layout(self, layout):
        """清空布局中的所有小部件"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def set_items(self, items):
        # 清空当前布局中的所有小部件
        self.clear_layout(self.scroll_area_layout)

        # List of items to display (images and texts)
        self.items = []
        for item in items:
            assert isinstance(item, list)
            new_item = []
            for views in item:
                new_views = []
                if isinstance(views, list):
                    for step in views:
                        if isinstance(step, Image.Image):
                            step = resize_image(step, 512, 512)
                        new_views.append(step)
                else:
                    new_views = views
                new_item.append(new_views)
            self.items.append(new_item)

        self.show_next_item()
        self.update_warning_log()

    def add_random_color_to_mask(self, org_img, img_data):
        """
        为org_img中img_data为255的区域添加显眼的随机颜色。

        :param org_img: 原始RGBA图像 (Pillow Image)
        :param img_data: 二值RGBA图像 (Pillow Image)
        :return: 处理后的图像 (Pillow Image)
        """
        # 将图像转换为数组
        if org_img is not None:
            org_array = np.array(self.hist_imgs[-1])
        else:
            data_array = np.array(img_data)
            return Image.fromarray(data_array, 'RGBA')

        data_array = np.array(img_data)
        # 随机生成颜色
        random_color = [random.randint(0, 255) for _ in range(3)] + [128]  # 保持Alpha值为128
        # 使用掩码设置特定区域的颜色
        selected_array = data_array[:, :, 0] > 250
        org_array[selected_array] = np.uint8(org_array[selected_array] * 0.7) + np.uint8(random_color) * 0.3

        # 将数组转换回图像
        result_img = Image.fromarray(org_array, 'RGBA')
        return result_img

    def show_item(self, item, img_idx=None, is_report=False, is_org_img=False):
        if isinstance(item, str):  # Text
            self.current_text_label = QLabel(item, self)
            font = QFont("Arial", 16)
            if is_report:
                font.setBold(True)
                font.setPointSize(18)
            self.current_text_label.setFont(font)
            self.current_text_label.setWordWrap(True)
            self.current_text_label.setAlignment(Qt.AlignCenter)  # 居中文本
            self.scroll_area_layout.addWidget(self.current_text_label)

        elif isinstance(item, Image.Image):  # PIL Image
            img_data = item.convert("RGBA")
            self.current_image = img_data

            if is_org_img:
                org_img = None
            else:
                org_img = self.org_img1 if img_idx == 0 else self.org_img2
            if len(self.hist_imgs) == 0 and org_img is not None:
                self.hist_imgs.append(org_img)
            img_data = self.add_random_color_to_mask(org_img, img_data)
            self.hist_imgs.append(img_data)

            q_image = QImage(img_data.tobytes(), img_data.width, img_data.height, QImage.Format_RGBA8888)
            self.current_image_label = QLabel(self)
            self.pixmap_full = QPixmap.fromImage(q_image)
            
            # 将 pixmap_full 设置为 QLabel 的 Pixmap
            self.current_image_label.setPixmap(self.pixmap_full)
            self.current_image_label.setAlignment(Qt.AlignCenter)
            self.scroll_area_layout.addWidget(self.current_image_label)

    def add_divider(self):
        """添加分割线"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: gray;")
        self.scroll_area_layout.addWidget(line)

    def show_next_item(self):
        self.org_img1 = self.items[0][0][0].convert("RGBA")
        if len(self.items[0]) > 2:
            self.org_img2 = self.items[0][1][0].convert("RGBA")
        else:
            self.org_img2 = None
        for r_idx, single_report_inference in enumerate(self.items):
            for view_idx, single_view_inference in enumerate(single_report_inference):
                if isinstance(single_view_inference, str):
                    self.show_item(single_view_inference, is_report=True)
                else:
                    assert isinstance(single_view_inference, list)
                    self.hist_imgs = []
                    for step in single_view_inference:
                        is_org_flag = r_idx == 0
                        self.show_item(step, None) if isinstance(step, str) else self.show_item(step, view_idx, is_org_img=is_org_flag)
            self.add_divider()

        self.scroll_to_top()

    def scroll_to_top(self):
        """Scroll to the top of the scroll area."""
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.minimum())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A or event.key() == Qt.Key_Left:  # 向左箭头
            self.current_index -= 1
        elif event.key() == Qt.Key_D or event.key() == Qt.Key_Right:  # 向右箭头
            self.current_index += 1
        elif event.key() == Qt.Key_R:  # 'r' 键
            self.show_next_item()

        # 处理索引越界情况
        self.current_index = max(0, min(self.current_index, len(case_file_list) - 1))

        # 根据索引获取对应的 covt_seq
        self.setWindowTitle(case_file_list[self.current_index])
        covt_seq = self.load_covt_seq(case_file_list[self.current_index])
        if covt_seq:
            self.set_items(covt_seq)

    def load_covt_seq(self, file_dir):
        covt_seq = []
        org_img_list = []
        flags = list()

        json_dir_path = os.path.join(case_file_path, file_dir)
        json_file_list = [file_name for file_name in os.listdir(json_dir_path) if file_name.endswith('.json')]
        self.log_content = []

        for json_file_name in json_file_list:
            json_file_path = os.path.join(json_dir_path, json_file_name)
            with open(json_file_path, 'r') as f:
                json_data = json.load(f)

            if json_data['imageData'] is None:
                self.log_content.append(f"{json_file_name}的imageData属性为空")
                continue
            image_data = base64.b64decode(json_data['imageData'])
            image = Image.open(BytesIO(image_data))

            org_img_list.append([image])
            flags_list = json_data["flags"]
            flags.extend([clean_sentence(flag) for flag in flags_list])
        report_flags = remove_duplicates(flags)

        org_img_list.append("Original chest x-ray images obtained")
        covt_seq.append(org_img_list)

        flags = [clean_sentence(flags[0])]
        for json_file_name in json_file_list:

            json_file_path = os.path.join(json_dir_path, json_file_name)
            with open(json_file_path, 'r') as f:
                json_data = json.load(f)
            
            shapes = json_data['shapes']
            for shape in shapes:
                for k, v in shape['flags'].items():
                    k = clean_sentence(k)
                    if v and k not in flags:
                        flags.append(k)

        for ref_flag in report_flags:
            if ref_flag not in flags:
                self.log_content.append(f"原报告 {ref_flag}未标注，如果是正常修改报告引起的请忽略")

        for flag in flags:
            single_report_seq = []

            assert len(json_file_list) <= 2
            
            for json_file_name in json_file_list:
                single_view_seq = []

                json_file_path = os.path.join(json_dir_path, json_file_name)
                with open(json_file_path, 'r') as f:
                    json_data = json.load(f)
                
                shapes = json_data["shapes"]
                size = (json_data['imageWidth'], json_data['imageHeight'])               
                for shape in shapes:
                    label = shape['label']
                    shape_flags = shape['flags']
                    new_shape_flags = dict()
                    for k, v in shape_flags.items():
                        k = clean_sentence(k)
                        new_shape_flags[k] = v
                    shape_flags = new_shape_flags
                    
                    shape_type = shape['shape_type']

                    if label not in cls2type.keys():
                        self.log_content.append(f"出现了未知标签:{label}")
                        continue
                    if cls2type[label] != shape_type:
                        self.log_content.append(f"{label}的标注类别为{shape_type}, 与期望的{cls2type[label]}不匹配")
                    if flag not in shape_flags.keys():
                        continue
                    if not shape_flags[flag]:
                        continue                            

                    last_txt = single_view_seq[-1] if len(single_view_seq) > 0 else None
                    last_msk = single_view_seq[-2] if len(single_view_seq) > 1 else None
                    new_canvas = Image.new('L', size, 0)

                    points = shape['points']
                    shape_type = shape['shape_type']
                    description = shape["description"]

                    if description is None:
                        self.log_content.append(f"{label}的description为空,请补上")
                        continue
                    if description.endswith('.') or description.endswith('\n'):
                        description = description[:-1]
                    if description == last_txt and len(single_view_seq) > 1:
                        canvas = copy.deepcopy(single_view_seq[-2])
                    else:
                        canvas = copy.deepcopy(new_canvas)

                    draw = ImageDraw.Draw(new_canvas)
                    if len(points) <= 1 and shape_type != 'point':
                        self.log_content.append(f"{label}不是点标签，但是所获取的坐标点却只有一个")
                        continue
                    try:
                        if shape_type == 'polygon':
                            points = [tuple(point) for point in points]
                            draw.polygon(points, fill=255)
                        elif shape_type in ['linestrip', 'line']:
                            for i in range(len(points) - 1):
                                draw.line(points[i] + points[i + 1], fill=255, width=13)
                        elif shape_type == 'point':
                            for point in points:
                                x, y = point
                                r = 15
                                draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=255)
                        elif shape_type == 'rectangle':
                            points = convert_nested_to_int(points)
                            points = flatten(points)
                            draw.rectangle(points, fill=255)
                    except Exception as e:
                        self.log_content.append(f"请检查一下报错:\n"+str(e))
                        continue

                    merged_canvas_array = np.array(canvas) + np.array(new_canvas)
                    merged_canvas_array[merged_canvas_array > 250] = 255
                    if description == last_txt:
                        single_view_seq[-2] = Image.fromarray(merged_canvas_array)
                    else:
                        single_view_seq.extend([Image.fromarray(merged_canvas_array), description])
                single_report_seq.append(single_view_seq)
            single_report_seq.append(f"Findings: {flag}")

            covt_seq.append(single_report_seq)
        return covt_seq

    def update_warning_log(self):
        """从日志文件读取警告信息并更新文本编辑器"""
        self.warning_log_display.clear()
        self.warning_log_display.setAlignment(Qt.AlignCenter)  # 设置文本居中
        font = QFont("Arial", 16)
        red_format = QTextCharFormat()
        red_format.setForeground(QColor("red"))

        self.warning_log_display.setFont(font)
        cursor = self.warning_log_display.textCursor()
        
        for line in self.log_content:
            cursor.insertText(line + '\n', red_format)

        self.warning_log_display.setTextCursor(cursor)

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder_path:
            global case_file_path, case_file_list
            case_file_path = folder_path
            case_file_list = [item for item in os.listdir(case_file_path) if item.startswith('p')]
            case_file_list = sorted(case_file_list, key=lambda x: (int(x.split('-')[0][1:]), int(x.split('-')[1][1:])))
            self.current_index = 0
            covt_seq = self.load_covt_seq(case_file_list[self.current_index])
            if covt_seq:
                self.set_items(covt_seq)
                self.setWindowTitle(case_file_list[self.current_index])

def main():
    app = QApplication(sys.argv)
    window = AnimatedDisplay()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
