def SearchArea(uav_ids, zone_id):
    """
    使用指定的多架无人机对指定 ID 的区域执行协同搜索任务。

    参数说明：
    ----------
    uav_ids:
        执行搜索任务的无人机编号列表。
        - 示例：['UAV_01', 'UAV_03']
        - 合法范围：必须是当前空闲（IDLE）的无人机

    zone_id:
        任务区域的唯一标识符（对应任务区域情报中的 id 字段）。
        - 类型：字符串或整数
        - 示例：'Zone_1'

    行为说明：
    ----------
    函数内部会自动根据 zone_id 从地理数据库中索引具体的围栏坐标，
    并将航点上传至飞控系统。
    """

    return {
        'action': 'SearchArea',
        'uav_ids': uav_ids,
        'zone_id': zone_id
    }

def FlyToFire(uav_id, fire_coordinates):
    """
    调度**单架**无人机全速飞往确认的火点坐标。

    参数说明：
    ----------
    uav_id:
        执行打击任务的**单架**无人机编号（字符串）。
        - 格式：'UAV_01' (必须是字符串，不能是列表)
        - 约束：该无人机必须已分配给当前区域。

    fire_coordinates:
        火点的中心位置坐标 [x, y]。

    行为说明：
    ----------
    该指令覆盖当前航点，强制单机前往火点。
    """

    return {
        'action': 'FlyToFire',
        'uav_id': uav_id,  # 返回单机 ID
        'fire_coordinates': fire_coordinates,
        'status': 'en_route'
    }