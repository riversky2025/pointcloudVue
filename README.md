# 点云可视化系统 (Point Cloud Visualization System)

一个基于 Vue 3 和 Three.js 的点云数据可视化系统，支持点云文件的上传、预览、自动播放和视频生成功能。

## 功能特点

### 点云可视化
- 支持 .bin 格式点云文件的导入和显示
- 实时 3D 渲染和交互
- 支持鼠标控制视角（旋转、缩放、平移）
- 自动调整相机视角以最佳展示点云

### 批量处理
- 支持多文件拖拽上传
- 文件列表管理
- 自动播放功能，支持连续查看多个点云文件
- 可调节播放速度（0.1-2秒/帧）

### 视频生成
- 支持将点云序列转换为视频
- 实时进度显示
- 可自定义视频参数

## 技术栈

- 前端框架：Vue 3
- UI 组件库：Element Plus
- 3D 渲染：Three.js
- 后端框架：Flask
- 点云处理：Open3D
- 视频处理：OpenCV

## 项目结构
```
pointcloudVue/
├── frontend/ # 前端项目目录
│ ├── src/
│ │ ├── App.vue # 主应用组件
│ │ └── ...
│ ├── package.json
│ └── ...
├── backend/ # 后端项目目录
│ ├── app.py # Flask 应用主文件
│ ├── requirements.txt # Python 依赖
│ └── ...
└── README.md
```
