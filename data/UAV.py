"""
无人机资产清单 (UAV Inventory)
包含无人机的静态属性（ID、类型）与动态属性（位置、状态、电量）。
"""

# 定义无人机状态机
class UAVStatus:
    IDLE = "IDLE"                   # 待机中 (可用)
    SEARCHING = "SEARCHING"         # 正在执行搜寻任务 (不可用)
    EXTINGUISHING = "EXTINGUISHING" # 正在执行灭火任务 (不可用)
    RETURN = "RETURN"               # 返航中 (如果电量充足，可用)
    CHARGING = "CHARGING"           # 充电中 (不可用)

# ==========================================
# 灭火无人机组 (UAV_01 ~ UAV_03)
# 特点：带载荷，速度稍慢，用于投弹灭火
# ==========================================

UAV_01 = {
    'id': 'UAV_01',
    'type': 'extinguishing_drone',
    'status': UAVStatus.IDLE,          # 状态：待机
    'location': [0.0, 0.0],            # 二维坐标 [x, y]
    'battery': 100.0,                  # 电量 (%)
    'capabilities': {
        'max_fire_extinguisher': 2,    # 最大挂载
        'current_payload': 2,          # 当前挂载
        'max_speed': 15.0,             # 最大速度 (m/s)
        'sensor_range': 0.15         # 感知半径
    },
    'description': '重型灭火无人机，满载2枚灭火弹，适合执行确认火情后的扑灭任务。'
}

UAV_02 = {
    'id': 'UAV_02',
    'type': 'extinguishing_drone',
    'status': UAVStatus.IDLE, 
    'location': [0.0, 0.0],            
    'battery': 65.0,                  
    'capabilities': {
        'max_fire_extinguisher': 2,
        'current_payload': 2,          
        'max_speed': 15.0,
        'sensor_range': 0.15
    },
    'description': '重型灭火无人机，满载2枚灭火弹，适合执行确认火情后的扑灭任务。'
}

UAV_03 = {
    'id': 'UAV_03',
    'type': 'extinguishing_drone',
    'status': UAVStatus.IDLE,      
    'location': [0.0, 0.0],
    'battery': 55.0,                   
    'capabilities': {
        'max_fire_extinguisher': 2,
        'current_payload': 2,          
        'max_speed': 15.0,
        'sensor_range': 0.15
    },
    'description': '重型灭火无人机，满载2枚灭火弹，适合执行确认火情后的扑灭任务。'
}

# ==========================================
# 侦查无人机组 (UAV_04 ~ UAV_05)
# 特点：轻量化，速度快，续航长，视野广
# ==========================================

UAV_04 = {
    'id': 'UAV_04',
    'type': 'surveillance_drone',
    'status': UAVStatus.IDLE,     
    'location': [0.0, 0.0],           
    'battery': 80.0,
    'capabilities': {
        'max_fire_extinguisher': 0,
        'current_payload': 0,
        'max_speed': 25.0,            
        'sensor_range': 0.3
    },
    'description': '高速侦查无人机，无挂载，配备广角红外摄像头，适合大范围快速扫描。'
}

UAV_05 = {
    'id': 'UAV_05',
    'type': 'surveillance_drone',
    'status': UAVStatus.IDLE,          
    'location': [0.0, 0.0],
    'battery': 100.0,
    'capabilities': {
        'max_fire_extinguisher': 0,
        'current_payload': 0,
        'max_speed': 25.0,
        'sensor_range': 0.3
    },
    'description': '高速侦查无人机，无挂载，配备广角红外摄像头，适合大范围快速扫描。'
}