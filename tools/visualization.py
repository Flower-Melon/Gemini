"""
可视化分割结果
将分割结果绘制在图像上，并保存可视化结果。
输入：分割结果字符串，图像路径（可选）
"""
import json
import ast
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

def visualize_segmentation_on_image(data_str, image_path=None):
    # --- 1. 解析数据 ---
    try:
        # 直接解析为 zones 列表，不再进行字典/列表格式判断
        zones = json.loads(data_str)
    except:
        try:
            zones = ast.literal_eval(data_str)
        except:
            return

    # --- 2. 加载图像  ---
    try:
        if image_path and os.path.exists(image_path):
            img_arr = np.array(Image.open(image_path))
        else:
            raise Exception
    except:
        img_arr = np.ones((1080, 1920, 3), dtype=np.uint8) * 240
    
    h, w = img_arr.shape[:2]

    # --- 3. 核心绘图 ---
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(img_arr)
    
    risk_colors = {'High': '#FF4500', 'Medium': '#FFA500', 'Low': '#FFD700', 'default': '#808080'}
    
    # 收集图例句柄
    legend_map = {}

    if isinstance(zones, list):
        for zone in zones:
            risk = zone.get('risk_level', 'default')
            color = risk_colors.get(risk, risk_colors['default'])
            
            # 绘制区域
            if 'coordinates' in zone:
                pts = np.array([(x * w, y * h) for x, y in zone['coordinates']])
                poly = patches.Polygon(pts, closed=True, linewidth=2, edgecolor=color, facecolor=color, alpha=0.3)
                ax.add_patch(poly)
                legend_map[risk] = poly
                
                # 绘制标签
                if len(pts) > 0:
                    cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
                    ax.text(cx, cy, f"{zone.get('id', '')}\n{risk}", color='white', fontsize=8, fontweight='bold',
                            ha='center', va='center', bbox=dict(facecolor=color, alpha=0.8, edgecolor='none', pad=1))

            # 绘制火点
            if 'fire_points' in zone and zone['fire_points']:
                fps = np.array([(x * w, y * h) for x, y in zone['fire_points']])
                sc = ax.scatter(fps[:, 0], fps[:, 1], c='red', marker='x', s=80, linewidths=2, zorder=10)
                legend_map['Fire Point'] = sc

    # --- 4. 装饰与保存 ---
    ax.axis('off')
    ax.set_title(f"Fire Risk Analysis: {os.path.basename(image_path) if image_path else 'Generated'}")
    if legend_map:
        ax.legend(legend_map.values(), legend_map.keys(), loc='upper right', framealpha=0.9)
    
    save_dir = os.path.join(os.path.dirname(image_path) if image_path else '.', "output")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{os.path.splitext(os.path.basename(image_path) if image_path else 'result')[0]}_visualized.png")
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == '__main__':
    
    json_path = "out/zones_data.json"
    image_dir = "temp"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        all_zones_data = json.load(f)
    
    for file_name, zones in all_zones_data.items():
        image_path = os.path.join(image_dir, file_name)
        visualize_segmentation_on_image(str(zones), image_path)
        