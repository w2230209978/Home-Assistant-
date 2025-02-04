# Home Assistant百度人脸识别集成

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.6%2B-blue)](https://www.home-assistant.io)

本集成将百度AI人脸识别功能深度整合到Home Assistant中，支持实时人脸属性分析和人脸库匹配。

## 🚀 主要功能

- ✅ 实时人脸检测（年龄/性别/情绪等）
- 🔍 人脸库用户识别
- 📊 历史数据可视化
- 🔔 自动化触发支持
- 📸 自动保存识别快照

## 📥 安装方法

### 方式1：HACS安装（推荐）
1. 打开HACS面板
2. 选择「自定义仓库」
3. 添加仓库：`https://github.com/w2230209978/ha-baidu-face.git`
4. 搜索「Home-Assistant-」安装

### 方式2：手动安装

cd /config/custom_components
git clone https://github.com/w2230209978/ha-baidu-face.git

## ⚙️ 配置指南

### 前置准备
1. 前往[百度AI开放平台](https://ai.baidu.com)创建应用
2. 获取以下凭证：
   - App ID
   - API Key
   - Secret Key

### configuration.yaml 配置
```yaml
sensor:
  - platform: face_detect
    app_id: "your_app_id"
    api_key: "your_api_key"
    secret_key: "your_secret_key"
    entity_id: "camera.your_camera"  # 摄像头实体
    access_token: "HA_LONG_LIVED_TOKEN"
    host: "192.168.1.100"  # HA实例IP
    port: 8123
    group_list: "group1,group2"  # 百度人脸库组
    delete_time: 3600  # 图片保留时间(秒)
    options:
      - age
      - beauty
      - emotion
      - facerecognition
```

## 🖥️ 前端展示

### Lovelace配置示例
```yaml
type: picture-glance
title: 实时人脸识别
entities:
  - entity: sensor.ren_lian_shi_bie_2
    icon: mdi:face-recognition
  - entity: sensor.nian_ling_2
    icon: mdi:numeric
  - entity: sensor.xing_bie_2
    icon: mdi:gender-male-female
  - switch.hikvision_ds_2cd1211d_i3_ir_lamp
camera_image: 自己的摄像头id
camera_view: live
```

## 🛠️ 常见问题

### Q1：实体显示"不可用"
✅ 解决方案：
1. 检查百度API凭证是否正确
2. 确认摄像头实体正常工作
3. 查看日志排查错误：
```bash
grep "face_detect" /config/home-assistant.log
```

### Q2：识别结果不准确
✅ 优化建议：
1. 调整摄像头角度确保人脸清晰
2. 在百度控制台优化人脸库图片质量
3. 修改匹配阈值：
```yaml
# sensor.py 第287行
options["match_threshold"] = 80  # 默认70
```

## 🌟 高级用法

### 自动化示例
```yaml
automation:
  - alias: "识别到家人时开灯"
    trigger:
      platform: state
      entity_id: sensor.baidu_facerecognition
      to: "family_member"
    action:
      service: light.turn_on
      target:
        entity_id: light.living_room
```

### 性能优化
```yaml
# 调整检测间隔
scan_interval: 10  # 默认5秒

# 禁用不需要的检测项
options:
  - facerecognition
  - age
```

## 🤝 参与贡献
欢迎提交PR或Issue！请遵循以下流程：
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -am '添加新功能'`)
4. 推送到分支 (`git push origin feature/新功能`)
5. 创建Pull Request

## 📜 许可证
本项目采用 MIT 许可证 - 详情参见 [LICENSE](LICENSE) 文件
```

---

这个README包含：
1. 直观的功能展示图标
2. 多安装方式选择
3. 分步配置指南
4. 可视化配置示例
5. 常见问题速查
6. 高级用法示例
7. 规范的贡献指南

建议在GitHub仓库中额外添加：
1. 屏幕截图文件夹 `/images`
2. 演示视频链接
3. 版本更新日志
4. 捐赠支持链接
5. 讨论区链接

需要根据你的实际项目情况修改占位符（如仓库地址、API参数等）。这样的文档结构既适合新手快速上手，也能满足高级用户的定制需求。
