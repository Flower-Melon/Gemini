# 初始的无人机定义，共五架无人机。
# 其中三架（UAV_01~UAV_03）带有投放装置，可以带两枚灭火弹。
# 另外两架（UAV_04~UAV_05）只能执行搜索监视任务，不带灭火弹。

# 需要添加位置信息，当前状态（状态机），电量等属性。

UAV_01 = {
    'id': 'UAV_01',
    'max_fire_extinguisher': 2,
    'type': 'extinguishing_drone',
    'description': '带有投放装置，可携带2枚灭火弹，具备搜索与灭火能力'
}

UAV_02 = {
    'id': 'UAV_02',
    'max_fire_extinguisher': 2,
    'type': 'extinguishing_drone',
    'description': '带有投放装置，可携带2枚灭火弹，具备搜索与灭火能力'
}

UAV_03 = {
    'id': 'UAV_03',
    'max_fire_extinguisher': 2,
    'type': 'extinguishing_drone',
    'description': '带有投放装置，可携带2枚灭火弹，具备搜索与灭火能力'
}

UAV_04 = {
    'id': 'UAV_04',
    'max_fire_extinguisher': 0,
    'type': 'surveillance_drone',
    'description': '仅配备摄像头，无投放装置，专门用于搜索监视任务'
}

UAV_05 = {
    'id': 'UAV_05',
    'max_fire_extinguisher': 0,
    'type': 'surveillance_drone',
    'description': '仅配备摄像头，无投放装置，专门用于搜索监视任务'
}