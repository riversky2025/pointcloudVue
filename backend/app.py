from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import numpy as np
import open3d as o3d
import os
import cv2
from pathlib import Path
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

def create_top_view_image(points):
    """创建点云的俯视图"""
    # 创建点云对象
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points[:, :3])
    pcd.paint_uniform_color([1.0, 0.0, 0.0])  # 红色点云
    
    # 创建可视化窗口
    vis = o3d.visualization.Visualizer()
    vis.create_window(visible=False)  # 设置为不可见
    vis.add_geometry(pcd)
    
    # 设置渲染选项
    opt = vis.get_render_option()
    opt.point_size = 1.0
    opt.background_color = np.asarray([0, 0, 0])
    
    # 设置视角为俯视图
    ctr = vis.get_view_control()
    ctr.set_zoom(0.3)
    ctr.set_front([0, 0, -1])
    ctr.set_lookat([0, 0, 0])
    ctr.set_up([0, -1, 0])
    
    # 渲染并获取图像
    vis.poll_events()
    vis.update_renderer()
    image = vis.capture_screen_float_buffer()
    vis.destroy_window()
    
    # 转换为OpenCV格式
    image = (np.asarray(image) * 255).astype(np.uint8)
    return image

def create_video_from_folder(folder_path, output_path, fps=10):
    """从文件夹中的点云文件创建视频"""
    # 获取所有bin文件并按名称排序
    bin_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.bin')])
    
    if not bin_files:
        raise ValueError("No .bin files found in the folder")
    
    # 创建视频写入器
    first_image = None
    video_writer = None
    
    for bin_file in bin_files:
        # 读取点云数据
        bin_path = os.path.join(folder_path, bin_file)
        points = np.fromfile(bin_path, dtype=np.float32).reshape(-1, 4)
        
        # 创建俯视图
        image = create_top_view_image(points)
        
        # 如果是第一帧，初始化视频写入器
        if first_image is None:
            first_image = image
            height, width = image.shape[:2]
            video_writer = cv2.VideoWriter(
                output_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                fps,
                (width, height)
            )
        
        # 写入帧
        video_writer.write(image)
    
    # 释放视频写入器
    if video_writer:
        video_writer.release()
    
    return output_path

@app.route('/api/pointcloud/<filename>')
def get_pointcloud(filename):
    try:
        # 读取bin文件
        bin_path = os.path.join('src/output', filename)
        points = np.fromfile(bin_path, dtype=np.float32).reshape(-1, 4)
        
        # 转换为前端需要的格式
        pointcloud_data = {
            'points': points[:, :3].tolist(),  # 只取x,y,z坐标
            'colors': [[1.0, 0.0, 0.0] for _ in range(len(points))]  # 红色点云
        }
        
        return jsonify(pointcloud_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files')
def list_files():
    try:
        files = [f for f in os.listdir('src/output') if f.endswith('.bin')]
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create_video', methods=['POST'])
def create_video():
    try:
        # 确保输出目录存在
        output_dir = 'output_videos'
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出视频路径
        output_path = os.path.join(output_dir, 'pointcloud_video.mp4')
        
        # 创建视频
        video_path = create_video_from_folder('src/output', output_path)
        
        return jsonify({
            'success': True,
            'message': 'Video created successfully',
            'video_path': video_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件被上传'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
            
        if not file.filename.endswith('.bin'):
            return jsonify({'success': False, 'error': '只支持.bin格式的文件'}), 400
        
        # 确保目录存在
        os.makedirs('src/output', exist_ok=True)
        
        # 安全地保存文件
        filename = secure_filename(file.filename)
        file.save(os.path.join('src/output', filename))
        
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'filename': filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False) 