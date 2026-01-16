# 无人机的函数。
def SearchArea(uav_ids, area_coordinates):
    """
    使用指定的多架无人机对目标区域执行协同搜索任务。

    参数说明：
    ----------
    uav_ids:
        执行搜索任务的无人机编号列表。
        - 示例：['UAV_01', 'UAV_03', 'UAV_07']
        - 合法范围：'UAV_01' ~ 'UAV_10'

    area_coordinates:
        搜索区域的多边形坐标（归一化坐标）。
        - 格式：[[x1, y1], [x2, y2], ...]
        - x, y 范围：0.0 ~ 1.0
        - 点数不少于 3 个

    行为说明：
    ----------
    当前阶段未对接真实飞控系统，
    打印日志即视为任务成功下发。
    """

    print("【搜索任务下发】")
    print(f"派出无人机: {uav_ids}")
    print(f"搜索区域坐标: {area_coordinates}")
    print("状态: 搜索任务已成功分配\n")

    return {
        'action': 'SearchArea',
        'uav_ids': uav_ids,
        'area_coordinates': area_coordinates,
        'status': 'assigned'
    }