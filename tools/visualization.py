import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image
import ast
import platform
import os

import ast
import platform
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import numpy as np

def visualize_segmentation_on_image(data_str, image_path=None):
    try:
        zones = ast.literal_eval(data_str)
    except Exception as e:
        print(f"数据解析错误: {e}")
        return

    system_name = platform.system()
    if system_name == "Windows":
        plt.rcParams['font.sans-serif'] = ['SimHei']
    elif system_name == "Darwin":
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    else:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
    plt.rcParams['axes.unicode_minus'] = False

    # 加载图像
    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            img_arr = np.array(img)
            h, w = img_arr.shape[:2]
            print(f"成功加载图像: {image_path}, 尺寸: {w}x{h}")
        except Exception as e:
            print(f"加载图像失败: {e}")
            return
    else:
        print(f"未找到图像或路径为空: {image_path}，使用空白底图。")
        h, w = 1080, 1920
        img_arr = np.ones((h, w, 3), dtype=np.uint8) * 240 

    # 设置绘图
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(img_arr)
    
    # 颜色映射
    color_map = {
        '森林': '#228B22',   
        '水面': '#1E90FF',   
        '陆地': '#D2691E',   
        'default': '#FFD700' 
    }

    # 遍历区域并绘制
    for zone in zones:
        coords_norm = zone['coordinates']
        z_type = zone.get('type', 'default')
        z_name = zone.get('name', 'Unknown')
        
        # 坐标转换
        pixel_coords = [(x * w, y * h) for x, y in coords_norm]
        
        color = color_map.get(z_type, color_map['default'])
        
        # 绘制多边形
        poly = patches.Polygon(
            pixel_coords, 
            closed=True, 
            linewidth=2, 
            edgecolor=color, 
            facecolor=color, 
            alpha=0.4,
            label=f"{z_name} ({z_type})"
        )
        ax.add_patch(poly)
        
        # 计算中心点
        poly_arr = np.array(pixel_coords)
        center_x = np.mean(poly_arr[:, 0])
        center_y = np.mean(poly_arr[:, 1])
        
        # 添加文字标签
        ax.text(
            center_x, center_y, 
            z_name, 
            color='white', 
            fontsize=9, 
            fontweight='bold',
            ha='center', 
            va='center', 
            bbox=dict(facecolor='black', alpha=0.6, edgecolor='none', pad=2)
        )

    ax.set_title(f"区域划分结果 (Source: {os.path.basename(image_path) if image_path else 'Blank'})")
    ax.axis('off')
    
    # 图例去重
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right', framealpha=0.8)

    plt.tight_layout()

    
    if image_path:
        # 获取原图所在目录
        dir_name = os.path.join(os.path.dirname(image_path), "output")
        os.makedirs(dir_name, exist_ok=True)
        # 获取文件名（不带后缀）
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        # 构建新的保存路径 (例如: 原名_visualized.png)
        save_name = f"{base_name}_visualized.png"
        save_path = os.path.join(dir_name, save_name)
    else:
        # 如果没有原图路径，保存到当前工作目录
        save_path = "segmentation_visualized_blank.png"

    try:
        # bbox_inches='tight' 可以去除周围多余的白边
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    except Exception as e:
        print(f"保存图片失败: {e}")

    # plt.show()