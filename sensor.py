from homeassistant.components.sensor import PLATFORM_SCHEMA
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import logging
import requests
import time
from homeassistant.helpers.entity import Entity
import base64
import os
import datetime
from datetime import timedelta
from aip import AipFace
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)
TIME_BETWEEN_UPDATES = timedelta(seconds=5)  # 调整为5秒间隔

CONF_OPTIONS = "options"
CONF_APP_ID = 'app_id'
CONF_API_KEY = 'api_key'
CONF_ENTITY_ID = 'entity_id'
CONF_SECRET_KEY = 'secret_key'
CONF_HOST = 'host'
CONF_PORT = 'port'
CONF_ACCESS_TOKEN = 'access_token'
CONF_GROUP_LIST = 'group_list'
CONF_DELETE_TIME = 'delete_time'

OPTIONS = {
    'age': ["baidu_age", "年龄", "mdi:account", "岁"],
    'beauty': ["baidu_beauty", "颜值", "mdi:face-woman-shimmer", "分"],
    'emotion': ["baidu_emotion", "情绪", "mdi:emoticon-excited-outline", None],
    'gender': ["baidu_gender", "性别", "mdi:gender-female", None],
    'glasses': ["baidu_glasses", "眼镜识别", "mdi:glasses", None],
    'expression': ["baidu_expression", "表情", "mdi:emoticon-neutral-outline", None],
    'faceshape': ["baidu_faceshape", "脸型", "mdi:baby-face-outline", None],
    'facerecognition': ["baidu_facerecognition", "人脸识别", "mdi:face-recognition", None]
}

ATTRIBUTION_UPDATE_TIME = "更新时间"
ATTRIBUTION_CHECK = "识别状态"
ATTRIBUTION_POWER = "技术支持"
ATTRIBUTION_FACE = "识别结果"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_OPTIONS, default=[]): vol.All(cv.ensure_list, [vol.In(OPTIONS)]),
    vol.Required(CONF_APP_ID): cv.string,
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_SECRET_KEY): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.port,
    vol.Required(CONF_ENTITY_ID): cv.string,
    vol.Required(CONF_ACCESS_TOKEN): cv.string,
    vol.Required(CONF_GROUP_LIST): cv.string,
    vol.Required(CONF_DELETE_TIME): cv.string
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """平台初始化"""
    _LOGGER.info("初始化百度人脸识别传感器")
    
    # 修正为正确的www目录路径
    save_path = hass.config.path('www/face_detect/')
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        _LOGGER.info("创建截图目录: %s", save_path)

    data = FaceDetectData(
        appid=config[CONF_APP_ID],
        apikey=config[CONF_API_KEY],
        secretkey=config[CONF_SECRET_KEY],
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        cameraid=config[CONF_ENTITY_ID],
        accesstoken=config[CONF_ACCESS_TOKEN],
        save_path=save_path,
        grouplist=config[CONF_GROUP_LIST],
        deletetime=config[CONF_DELETE_TIME]
    )

    entities = [FaceDetectSensor(data, option) for option in config[CONF_OPTIONS]]
    add_entities(entities, True)

class FaceDetectSensor(Entity):
    """传感器实体类"""
    def __init__(self, data, option):
        self._data = data
        self._option = option
        self._state = None
        self._attributes = {
            ATTRIBUTION_UPDATE_TIME: None,
            ATTRIBUTION_CHECK: "否",
            ATTRIBUTION_FACE: "无"
        }

    @property
    def name(self):
        return OPTIONS[self._option][1]

    @property
    def unique_id(self):
        return f"face_detect_{OPTIONS[self._option][0]}"

    @property
    def icon(self):
        return OPTIONS[self._option][2]

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return OPTIONS[self._option][3]

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update(self):
        """更新数据"""
        self._data.update()
        self._state = getattr(self._data, self._option, None)
        self._attributes.update({
            ATTRIBUTION_UPDATE_TIME: self._data.updatetime,
            ATTRIBUTION_CHECK: self._data.check_status,
            ATTRIBUTION_FACE: self._data.face_info
        })

class FaceDetectData:
    """数据处理核心类"""
    def __init__(self, appid, apikey, secretkey, host, port, cameraid, accesstoken, save_path, grouplist, deletetime):
        self._client = AipFace(appid, apikey, secretkey)
        self._host = host
        self._port = port
        self._cameraid = cameraid
        self._accesstoken = accesstoken
        self._save_path = save_path
        self._grouplist = grouplist
        self._deletetime = deletetime
        self._updatetime = None
        self._check_status = "否"
        self._face_info = "无"
        self._attributes = {}

    @Throttle(TIME_BETWEEN_UPDATES)
    def update(self):
        """主更新方法"""
        try:
            res1, img_data, res2 = self._get_face_data()
            self._process_detection_result(res1, img_data)
            self._process_recognition_result(res2)
        except Exception as e:
            _LOGGER.error("更新过程中发生严重错误: %s", str(e))
            self._reset_values()
        finally:
            self._updatetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self._cleanup_files()

    def _get_face_data(self):
        """获取人脸数据"""
        try:
            img_data = self._get_camera_snapshot()
            image = base64.b64encode(img_data).decode()
            
            # 人脸检测
            detect_options = {
                "face_field": "age,beauty,emotion,gender,glasses,expression,faceshape",
                "max_face_num": 1,
                "face_type": "LIVE"
            }
            res1 = self._client.detect(image, "BASE64", detect_options)
            
            # 人脸搜索
            search_options = {
                "max_face_num": 1,
                "match_threshold": 70,
                "quality_control": "NORMAL",
                "liveness_control": "LOW",
                "max_user_num": 1
            }
            res2 = self._client.multiSearch(image, "BASE64", self._grouplist, search_options)
            
            return res1, img_data, res2
        except Exception as e:
            _LOGGER.error("API调用失败: %s", str(e))
            raise

    def _process_detection_result(self, res, img_data):
        """处理检测结果"""
        if res.get("error_code") != 0 or not res.get("result"):
            _LOGGER.warning("人脸检测失败: %s", res.get("error_msg", "未知错误"))
            self._reset_values()
            return

        try:
            face = res["result"]["face_list"][0]
            self._attributes.update({
                'age': face.get("age"),
                'beauty': face.get("beauty"),
                'emotion': self._translate_emotion(face.get("emotion", {}).get("type")),
                'gender': self._translate_gender(face.get("gender", {}).get("type")),
                'glasses': self._translate_glasses(face.get("glasses", {}).get("type")),
                'expression': self._translate_expression(face.get("expression", {}).get("type")),
                'faceshape': self._translate_faceshape(face.get("face_shape", {}).get("type"))
            })
            self._check_status = "是"
            self._save_image(img_data)
        except (KeyError, IndexError) as e:
            _LOGGER.error("解析人脸属性失败: %s", str(e))
            self._reset_values()

    def _process_recognition_result(self, res):
        """处理识别结果"""
        if res.get("error_code") != 0 or not res.get("result"):
            _LOGGER.warning("人脸搜索失败: %s", res.get("error_msg", "未知错误"))
            self._face_info = "无"
            return

        try:
            user_info = res["result"]["face_list"][0]["user_list"][0]
            self._face_info = f"{user_info['user_id']} ({user_info['score']:.1f}%)"
            self._attributes['facerecognition'] = user_info['user_id']
        except (KeyError, IndexError) as e:
            _LOGGER.error("解析识别结果失败: %s", str(e))
            self._face_info = "无"

    def _get_camera_snapshot(self):
        """获取摄像头快照"""
        try:
            url = f"http://{self._host}:{self._port}/api/camera_proxy/{self._cameraid}"
            headers = {'Authorization': f"Bearer {self._accesstoken}"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            _LOGGER.error("获取摄像头快照失败: %s", str(e))
            raise

    def _save_image(self, img_data):
        """保存识别图片"""
        try:
            filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            path = os.path.join(self._save_path, filename)
            with open(path, 'wb') as f:
                f.write(img_data)
            _LOGGER.debug("图片已保存: %s", path)
        except Exception as e:
            _LOGGER.error("保存图片失败: %s", str(e))

    def _cleanup_files(self):
        """清理过期文件"""
        try:
            now = datetime.datetime.now()
            cutoff = now - datetime.timedelta(seconds=int(self._deletetime))
            
            for filename in os.listdir(self._save_path):
                path = os.path.join(self._save_path, filename)
                ctime = datetime.datetime.fromtimestamp(os.path.getctime(path))
                if ctime < cutoff:
                    os.remove(path)
                    _LOGGER.debug("已删除过期文件: %s", path)
        except Exception as e:
            _LOGGER.error("文件清理失败: %s", str(e))

    def _reset_values(self):
        """重置所有值"""
        self._check_status = "否"
        self._face_info = "无"
        self._attributes.clear()

    @staticmethod
    def _translate_emotion(emotion):
        """翻译情绪类型"""
        emotions = {
            'angry': '愤怒', 'disgust': '厌恶', 'fear': '恐惧',
            'happy': '高兴', 'sad': '伤心', 'surprise': '惊讶',
            'neutral': '无情绪', 'grimace': '鬼脸', 'pouty': '翘嘴'
        }
        return emotions.get(emotion, '未知情绪')

    @staticmethod
    def _translate_gender(gender):
        """翻译性别"""
        return '男性' if gender == 'male' else '女性' if gender == 'female' else '未知'

    @staticmethod
    def _translate_glasses(glasses):
        """翻译眼镜类型"""
        types = {'none': '无眼镜', 'common': '普通眼镜', 'sun': '墨镜'}
        return types.get(glasses, '未知类型')

    @staticmethod
    def _translate_expression(expression):
        """翻译表情"""
        types = {'none': '无表情', 'smile': '微笑', 'laugh': '大笑'}
        return types.get(expression, '未知表情')

    @staticmethod
    def _translate_faceshape(faceshape):
        """翻译脸型"""
        shapes = {
            'square': '方型脸', 'triangle': '三角脸',
            'oval': '椭圆脸', 'heart': '心型脸', 'round': '圆脸'
        }
        return shapes.get(faceshape, '未知脸型')

    @property
    def age(self): return self._attributes.get('age')
    @property
    def beauty(self): return self._attributes.get('beauty')
    @property
    def emotion(self): return self._attributes.get('emotion')
    @property
    def gender(self): return self._attributes.get('gender')
    @property
    def glasses(self): return self._attributes.get('glasses')
    @property
    def expression(self): return self._attributes.get('expression')
    @property
    def faceshape(self): return self._attributes.get('faceshape')
    @property
    def facerecognition(self): return self._attributes.get('facerecognition')
    @property
    def check_status(self): return self._check_status
    @property
    def face_info(self): return self._face_info
    @property
    def updatetime(self): return self._updatetime