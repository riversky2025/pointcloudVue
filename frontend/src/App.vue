<template>
  <div class="app-container">
    <el-container>
      <el-aside width="300px">
        <div class="sidebar-header">
          <h2>点云可视化系统</h2>
        </div>
        <div class="video-controls">
          <div class="control-header">
            <el-icon><video-camera /></el-icon>
            <span>视频生成</span>
          </div>
          <div class="video-params">
            <el-form :model="videoParams" label-position="left" label-width="80px" size="small">
              <el-form-item label="帧率">
                <el-input-number 
                  v-model="videoParams.fps" 
                  :min="1" 
                  :max="60" 
                  size="small"
                />
              </el-form-item>
              <el-form-item label="分辨率">
                <el-select v-model="videoParams.resolution" size="small">
                  <el-option label="1920x1080" value="1080p" />
                  <el-option label="1280x720" value="720p" />
                  <el-option label="854x480" value="480p" />
                </el-select>
              </el-form-item>
              <el-form-item label="质量">
                <el-slider 
                  v-model="videoParams.quality" 
                  :min="1" 
                  :max="100" 
                  :format-tooltip="(val) => val + '%'"
                />
              </el-form-item>
            </el-form>
          </div>
          <el-button type="primary" @click="generateVideo" :loading="generatingVideo" class="generate-btn">
            <el-icon><film /></el-icon>
            生成视频
          </el-button>
          <div v-if="generatingVideo" class="progress-info">
            <el-progress 
              :percentage="videoProgress" 
              :format="format"
              :stroke-width="15"
              status="success"
            />
            <div class="progress-details">
              <span>已处理: {{ processedFrames }} / {{ totalFrames }} 帧</span>
              <span>预计剩余时间: {{ remainingTime }}</span>
            </div>
          </div>
        </div>
        <div class="upload-container">
          <el-upload
            class="upload-demo"
            action="/api/upload"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            accept=".bin"
            :show-file-list="true"
            :multiple="true"
            drag
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持上传多个.bin格式的点云文件
              </div>
            </template>
          </el-upload>
        </div>
        <div class="file-list">
          <div class="file-list-header" @click="toggleFileList">
            <el-icon><folder /></el-icon>
            <span>点云文件列表</span>
            <el-icon class="collapse-icon" :class="{ 'is-collapsed': isFileListCollapsed }">
              <arrow-down />
            </el-icon>
          </div>
          <el-collapse-transition>
            <el-scrollbar v-show="!isFileListCollapsed" height="200px">
              <el-menu>
                <el-menu-item 
                  v-for="file in files" 
                  :key="file" 
                  @click="() => loadPointCloud(file)"
                >
                  <el-icon><document /></el-icon>
                  <span>{{ file }}</span>
                </el-menu-item>
              </el-menu>
            </el-scrollbar>
          </el-collapse-transition>
        </div>
      </el-aside>
      <el-main class="main-container">
        <div class="viewer-header">
          <h3>点云实时预览</h3>
          <div class="viewer-controls">
            <el-tooltip content="重置视角" placement="top">
              <el-button circle @click="resetCamera">
                <el-icon><refresh /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip :content="isPlaying ? '暂停播放' : '自动播放'" placement="top">
              <el-button circle @click="toggleAutoPlay">
                <el-icon>
                  <video-play v-if="!isPlaying" />
                  <video-pause v-else />
                </el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="调整播放速度" placement="top">
              <el-slider
                v-model="playbackSpeed"
                :min="0.1"
                :max="2"
                :step="0.1"
                style="width: 100px"
              />
            </el-tooltip>
          </div>
        </div>
        <div ref="container" class="viewer-container"></div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import {
  UploadFilled,
  Document,
  Folder,
  VideoCamera,
  Film,
  Refresh,
  VideoPlay,
  VideoPause,
  ArrowDown
} from '@element-plus/icons-vue'

const container = ref(null)
const files = ref([])
const generatingVideo = ref(false)
const videoProgress = ref(0)
const isPlaying = ref(false)
const playbackSpeed = ref(0.2)
const currentFileIndex = ref(0)
let scene, camera, renderer, pointsObject, controls
let savedCameraState = null
let playbackInterval = null

// 添加文件列表折叠状态
const isFileListCollapsed = ref(false)
const toggleFileList = () => {
  isFileListCollapsed.value = !isFileListCollapsed.value
}

// 视频生成参数
const videoParams = ref({
  fps: 30,
  resolution: '1080p',
  quality: 80
})

// 视频生成进度相关状态
const processedFrames = ref(0)
const totalFrames = ref(0)
const remainingTime = ref('计算中...')
const lastUpdateTime = ref(0)

// 初始化Three.js场景
const initScene = () => {
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000)
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(window.innerWidth - 200, window.innerHeight)
  container.value.appendChild(renderer.domElement)

  // 设置相机位置
  camera.position.z = 50
  camera.position.y = 30
  camera.lookAt(0, 0, 0)

  // 添加轨道控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true // 启用阻尼效果
  controls.dampingFactor = 0.05 // 阻尼系数
  controls.screenSpacePanning = false
  controls.minDistance = 1 // 最小缩放距离
  controls.maxDistance = 500 // 最大缩放距离
  controls.maxPolarAngle = Math.PI // 最大垂直旋转角度

  // 添加坐标轴
  const axesHelper = new THREE.AxesHelper(10)
  scene.add(axesHelper)

  // 添加环境光
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
  scene.add(ambientLight)

  // 添加平行光
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5)
  directionalLight.position.set(1, 1, 1)
  scene.add(directionalLight)
}

// 加载点云数据
const loadPointCloud = async (filename) => {
  try {
    console.log('Loading point cloud:', filename)
    const response = await axios.get(`/api/pointcloud/${filename}`)
    const { points, colors } = response.data

    // 如果已有点云，先移除
    if (pointsObject) {
      scene.remove(pointsObject)
    }

    // 创建点云几何体
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(points.flat())
    const colorArray = new Float32Array(colors.flat())

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3))

    const material = new THREE.PointsMaterial({
      size: 0.1,
      vertexColors: true
    })

    pointsObject = new THREE.Points(geometry, material)
    scene.add(pointsObject)

    // 只在非自动播放时调整相机位置
    if (!isPlaying.value) {
      const box = new THREE.Box3().setFromObject(pointsObject)
      const center = box.getCenter(new THREE.Vector3())
      const size = box.getSize(new THREE.Vector3())
      const maxDim = Math.max(size.x, size.y, size.z)
      const fov = camera.fov * (Math.PI / 180)
      let cameraZ = Math.abs(maxDim / Math.tan(fov / 2))

      camera.position.set(center.x, center.y + cameraZ * 0.5, center.z + cameraZ)
      camera.lookAt(center)
      controls.target.copy(center)
      controls.update()
    }
  } catch (error) {
    console.error('Error loading point cloud:', error)
    ElMessage.error('加载点云失败：' + error.message)
  }
}

// 获取文件列表
const getFiles = async () => {
  try {
    const response = await axios.get('/api/files')
    files.value = response.data.files
  } catch (error) {
    console.error('Error getting files:', error)
  }
}

// 生成视频
const generateVideo = async () => {
  try {
    generatingVideo.value = true
    videoProgress.value = 0
    
    // 开始生成视频并直接下载
    const response = await axios.post('/api/create_video', videoParams.value, {
      responseType: 'blob', // 设置响应类型为blob
      onDownloadProgress: (progressEvent) => {
        if (progressEvent.lengthComputable) {
          videoProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        }
      }
    })
    
    // 创建Blob URL并下载
    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `pointcloud_video_${new Date().getTime()}.mp4`
    document.body.appendChild(link)
    link.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(link)
    
    ElMessage.success('视频生成并下载成功！')
    videoProgress.value = 100
  } catch (error) {
    console.error('生成视频错误:', error)
    ElMessage.error('视频生成失败：' + (error.response?.data?.message || error.message))
  } finally {
    generatingVideo.value = false
  }
}

// 进度条格式化
const format = (percentage) => {
  return percentage === 100 ? '完成' : `${percentage}%`
}

// 修改动画循环函数
const animate = () => {
  requestAnimationFrame(animate)
  controls.update() // 更新控制器
  renderer.render(scene, camera)
}

// 修改窗口大小调整事件处理
onMounted(() => {
  initScene()
  getFiles()
  animate()

  window.addEventListener('resize', () => {
    camera.aspect = (window.innerWidth - 200) / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth - 200, window.innerHeight)
    controls.update() // 更新控制器
  })
})

// 处理文件上传成功
const handleUploadSuccess = async (response) => {
  if (response.success) {
    ElMessage.success('文件上传成功')
    await getFiles() // 刷新文件列表
    // 直接加载刚上传的点云文件
    await loadPointCloud(response.filename)
  } else {
    ElMessage.error('文件上传失败：' + response.error)
  }
}

// 处理文件上传失败
const handleUploadError = (error) => {
  ElMessage.error('文件上传失败：' + error.message)
}

// 添加重置相机位置的函数
const resetCamera = () => {
  if (!pointsObject) return
  
  const box = new THREE.Box3().setFromObject(pointsObject)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = camera.fov * (Math.PI / 180)
  let cameraZ = Math.abs(maxDim / Math.tan(fov / 2))

  camera.position.set(center.x, center.y + cameraZ * 0.5, center.z + cameraZ)
  camera.lookAt(center)
  controls.target.copy(center)
  controls.update()
}

// 保存相机状态
const saveCameraState = () => {
  savedCameraState = {
    position: camera.position.clone(),
    rotation: camera.rotation.clone(),
    target: controls.target.clone()
  }
}

// 恢复相机状态
const restoreCameraState = () => {
  if (savedCameraState) {
    camera.position.copy(savedCameraState.position)
    camera.rotation.copy(savedCameraState.rotation)
    controls.target.copy(savedCameraState.target)
    controls.update()
  }
}

// 自动播放控制
const toggleAutoPlay = () => {
  if (isPlaying.value) {
    stopAutoPlay()
  } else {
    startAutoPlay()
  }
}

const startAutoPlay = () => {
  if (!files.value.length) {
    ElMessage.warning('没有可播放的点云文件')
    return
  }
  
  if (!savedCameraState) {
    saveCameraState() // 第一次播放时保存相机状态
  }
  
  isPlaying.value = true
  playNextFile()
}

const stopAutoPlay = () => {
  isPlaying.value = false
  if (playbackInterval) {
    clearTimeout(playbackInterval)
    playbackInterval = null
  }
}

const playNextFile = async () => {
  if (!isPlaying.value || !files.value.length) return

  const filename = files.value[currentFileIndex.value]
  await loadPointCloud(filename)
  restoreCameraState() // 使用保存的相机状态

  currentFileIndex.value = (currentFileIndex.value + 1) % files.value.length
  
  // 设置下一个文件的播放
  playbackInterval = setTimeout(playNextFile, playbackSpeed.value * 1000)
}

// 修改组件卸载时的清理
onBeforeUnmount(() => {
  stopAutoPlay()
})
</script>

<style>
:root {
  --primary-color: #00f2fe;
  --secondary-color: #4facfe;
  --bg-color: #0a1929;
  --card-bg: rgba(16, 42, 67, 0.8);
  --text-color: #e0e0e0;
  --border-color: rgba(0, 242, 254, 0.3);
}

.app-container {
  width: 100vw;
  height: 100vh;
  background-color: var(--bg-color);
  color: var(--text-color);
  font-family: 'Arial', sans-serif;
  overflow: hidden;
}

.el-aside {
  background-color: var(--card-bg);
  box-shadow: 0 0 20px rgba(0, 242, 254, 0.1);
  display: flex;
  flex-direction: column;
  padding: 0;
  border-right: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
  height: 100vh;
  overflow: hidden;
}

.sidebar-header {
  padding: 15px;
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: var(--bg-color);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.sidebar-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 25%, rgba(255,255,255,0.1) 50%, transparent 75%);
  background-size: 200% 200%;
  animation: shimmer 3s infinite;
}

@keyframes shimmer {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 200%; }
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.5em;
  font-weight: bold;
  text-shadow: 0 0 10px rgba(0,0,0,0.3);
}

.video-controls {
  padding: 15px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(180deg, transparent, rgba(0, 242, 254, 0.05));
}

.control-header {
  margin-bottom: 15px;
  font-size: 16px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--primary-color);
}

.video-params {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 4px;
  background: rgba(0, 242, 254, 0.05);
}

.video-params .el-form-item {
  margin-bottom: 12px;
}

.video-params .el-form-item__label {
  color: var(--text-color);
}

.video-params .el-input-number,
.video-params .el-select {
  width: 100%;
}

.generate-btn {
  width: 100%;
  margin-bottom: 10px;
}

.progress-info {
  margin-top: 15px;
}

.progress-details {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-color);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.el-slider__runway {
  background-color: rgba(0, 242, 254, 0.1);
}

.el-input-number__decrease,
.el-input-number__increase {
  background-color: var(--card-bg);
  color: var(--text-color);
  border-color: var(--border-color);
}

.el-input__wrapper {
  background-color: var(--card-bg) !important;
}

.el-input__inner {
  color: var(--text-color) !important;
}

.el-select__popper {
  background-color: var(--card-bg) !important;
  border: 1px solid var(--border-color) !important;
}

.el-select-dropdown__item {
  color: var(--text-color) !important;
}

.el-select-dropdown__item.hover,
.el-select-dropdown__item:hover {
  background-color: rgba(0, 242, 254, 0.1) !important;
}

.upload-container {
  padding: 15px;
  border-bottom: 1px solid var(--border-color);
}

.el-upload {
  width: 100%;
}

.el-upload-dragger {
  width: 100%;
  height: 120px;
  background-color: rgba(16, 42, 67, 0.5);
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.el-upload-dragger:hover {
  border-color: var(--primary-color);
  box-shadow: 0 0 20px rgba(0, 242, 254, 0.2);
}

.file-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-list-header {
  padding: 12px 15px;
  font-size: 14px;
  font-weight: bold;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(90deg, transparent, rgba(0, 242, 254, 0.1), transparent);
  cursor: pointer;
  user-select: none;
}

.collapse-icon {
  margin-left: auto;
  transition: transform 0.3s ease;
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

.el-scrollbar {
  flex: 1;
}

.main-container {
  padding: 15px;
  background-color: var(--bg-color);
  position: relative;
  overflow: hidden;
  height: 100vh;
}

.main-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    linear-gradient(45deg, transparent 48%, var(--border-color) 49%, var(--border-color) 51%, transparent 52%),
    linear-gradient(-45deg, transparent 48%, var(--border-color) 49%, var(--border-color) 51%, transparent 52%);
  background-size: 20px 20px;
  opacity: 0.1;
  pointer-events: none;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 12px;
  background-color: var(--card-bg);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.viewer-header h3 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.2em;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
}

.viewer-container {
  width: 100%;
  height: calc(100vh - 100px);
  background-color: rgba(0, 0, 0, 0.5);
  border-radius: 8px;
  overflow: hidden;
  cursor: grab;
  box-shadow: 0 0 30px rgba(0, 242, 254, 0.1);
  border: 1px solid var(--border-color);
  position: relative;
}

.viewer-container::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 48%, var(--border-color) 49%, var(--border-color) 51%, transparent 52%);
  background-size: 20px 20px;
  opacity: 0.1;
  pointer-events: none;
}

.viewer-container:active {
  cursor: grabbing;
}

.el-upload__tip {
  font-size: 12px;
  color: var(--text-color);
  margin-top: 10px;
  opacity: 0.8;
}

.el-progress {
  margin-top: 15px;
}

.el-progress-bar__outer {
  background-color: rgba(0, 242, 254, 0.1);
}

.el-progress-bar__inner {
  background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
}

.viewer-controls {
  display: flex;
  gap: 15px;
  align-items: center;
}

.el-button {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  border: none;
  color: var(--bg-color);
  transition: all 0.3s ease;
}

.el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.3);
}

.el-slider {
  margin-left: 10px;
}

.el-slider__bar {
  background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
}

.el-slider__button {
  border: 2px solid var(--primary-color);
  background-color: var(--bg-color);
}

/* 图标样式 */
.el-icon {
  vertical-align: middle;
  color: var(--primary-color);
}

/* 动画效果 */
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(0, 242, 254, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0); }
}

.el-button--primary {
  animation: pulse 2s infinite;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .el-aside {
    width: 250px !important;
  }
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 242, 254, 0.1);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(var(--primary-color), var(--secondary-color));
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--primary-color);
}

.el-menu {
  border-right: none;
  background-color: transparent;
}

.el-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-color);
  transition: all 0.3s ease;
  background-color: transparent !important;
  border-left: 2px solid transparent;
}

.el-menu-item:hover {
  background-color: rgba(0, 242, 254, 0.1) !important;
  transform: translateX(5px);
  border-left: 2px solid var(--primary-color);
}

.el-menu-item.is-active {
  background-color: rgba(0, 242, 254, 0.15) !important;
  border-left: 2px solid var(--primary-color);
  color: var(--primary-color);
}

.el-menu-item .el-icon {
  color: var(--text-color);
}

.el-menu-item:hover .el-icon,
.el-menu-item.is-active .el-icon {
  color: var(--primary-color);
}

.el-scrollbar__view {
  background-color: transparent;
}

.el-scrollbar {
  background-color: transparent;
}

.file-list {
  background-color: var(--card-bg);
}
</style> 