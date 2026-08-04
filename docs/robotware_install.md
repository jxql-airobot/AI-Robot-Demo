# RobotWare 安装记录

> 记录 RobotWare 6.08 的安装准备与结果。更新于 2026-08-04。

## 1. 需求确认

- 目标版本：**RobotWare 6.08.01**（与本机 RobotStudio 6.08.01 严格匹配）
- 用途：RobotStudio 虚拟控制器（Virtual Controller）运行环境

## 2. 本机检查结果（2026-08-04）

| 检查项 | 结果 |
| --- | --- |
| RobotStudio 6.08.01 | ✅ 已安装（D 盘） |
| RobotWare 6.08 | ❌ **未安装** |
| 本机安装包搜索（C 盘 / D 盘 / 下载目录） | ❌ 未找到 RobotWare 安装程序 |

## 3. 需要下载的官方安装包

**名称：RobotWare 6.08.01**（安装包通常为 `RobotWare_6.08.01.xxxx.exe` 或随
RobotStudio 安装介质的独立组件）

官方获取渠道（不要从未知来源下载）：

1. ABB 机器人官网下载中心（需 MyABB 账号）：
   https://new.abb.com/products/robotics/robotstudio/downloads
2. ABB RobotStudio 开发者中心：https://developercenter.robotstudio.com
3. 原 RobotStudio 安装介质（DVD/ISO）中的 RobotWare 组件

> 安装时务必选择与 RobotStudio 6.08.01 匹配的 RobotWare 6.08 版本，
> 版本不匹配会导致"新建工作站 -> 从布局创建系统"时下拉列表不显示虚拟控制器。

## 4. 安装记录（待补）

安装完成后填写：

| 项 | 值 |
| --- | --- |
| 安装包名称 | 待下载 |
| 安装路径 | 待确认 |
| 安装结果 | 待确认 |
| 问题 | 待记录 |

## 5. 安装后验证

```bash
# 重新运行环境检查，确认 RobotWare 出现在注册组件中
python robotstudio/check_environment.py
```
