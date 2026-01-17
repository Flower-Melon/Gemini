"""
批量重命名指定文件夹内的图片文件，按顺序命名为0000, 0001, 0002等格式。
"""
import os

# 图片文件夹路径
folder_path = "./image"

# 支持的图片格式
extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')

def batch_rename():
    # 获取文件夹内所有文件
    try:
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(extensions)]
    except FileNotFoundError:
        print("错误：找不到指定的文件夹，请检查路径。")
        return

    files.sort() 

    count = 0
    print(f"找到 {len(files)} 张图片，开始重命名...")

    for filename in files:

        file_ext = os.path.splitext(filename)[1]

        new_name = f"{str(count).zfill(4)}{file_ext}"
        
        old_file = os.path.join(folder_path, filename)
        new_file = os.path.join(folder_path, new_name)
        
        # 重命名
        try:
            os.rename(old_file, new_file)
            print(f"重命名: {filename} -> {new_name}")
            count += 1
        except Exception as e:
            print(f"跳过 {filename}: {e}")

    print("完成！")

if __name__ == '__main__':
    batch_rename()