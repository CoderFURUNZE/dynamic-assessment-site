# 推荐系统说明（当前实现）

本文档说明系统的**推荐与解锁逻辑**、**证据清单**、**补救通道**与**数据来源**，并与代码实现保持一致。

---

## 1. 设计原则

1. **行为数据决定掌握（强证据）**  
   以小测/练习正确率为主，表情/状态只做策略调节（弱证据）。
2. **证据组合解锁（软门槛）**  
   解锁后继知识点需要“掌握度 + 小测/练习阈值 + 证据清单完成度”共同满足。
3. **错题进入补救通道**  
   通过“猜测/失误”与状态信号判断，决定继续同难度复核或进入补救路径。
4. **选题目标：补证据 + 学习收益 − 挫败风险**  
   优先补齐证据缺口，同时避免连续错引发挫败。

---

## 2. 核心流程（一次推荐）

1. 计算掌握度（Mastery）  
2. 计算证据清单完成度  
3. 判断是否满足解锁条件  
4. 生成补救建议  
5. 推荐下一题

---

## 3. 掌握度计算（behavior-driven）

文件：`backend/app/services/eval.py`

- 行为得分：小测正确率 + 练习正确率（强信号）
- 弱信号调节：表情轻松度、视频完成度、耗时惩罚（幅度限制在 ±0.1）
- 掌握度**单调不减**（保留历史最高值）

简化逻辑：
```
behavior_score = (w_quiz*quiz + w_practice*practice) / (w_quiz+w_practice)
mastery = clamp(behavior_score + clamp(aux, -0.1, 0.1))
```

---

## 4. 证据清单（Evidence Checklist）

文件：`backend/app/services/reco_policy.py`

每个知识点需要满足的强证据：
- 至少 1 道选择题正确
- 至少 1 道填空题正确
- 至少 1 道中等题正确
- 至少 1 道困难题正确（或 2 道中等题正确）
- **“确定”作答比例** ≥ 阈值（默认 0.5）

输出结构：
```
{
  items: {mcq_correct, blank_correct, medium_correct, hard_or_two_medium, sure_ratio},
  missing: [...],
  score: 0~1,
  summary: {total_correct, medium_correct, hard_correct, sure_ratio}
}
```

> “蒙的/确定”来自前端作答自评。

---

## 5. 解锁规则（后继知识点）

文件：`backend/app/services/reco.py`

需要同时满足：
1. 小测通过  
2. 练习完成且正确率 ≥ 阈值  
3. 掌握度 ≥ 0.7  
4. 证据清单得分 ≥ 0.75（可配置）

说明：  
该条件只限制“推荐下一步”的直接跳转，不会阻止学习非后继知识点。

---

## 6. 补救通道（Remedy）

文件：`backend/app/services/reco.py`  
辅助逻辑：`backend/app/services/reco_policy.py`

依据：
- 最近一次错题耗时
- 表情困难度（弱信号）
- 连续错误次数（wrong streak）
- 自评“蒙/确定”

输出：
```
remedy.action:
  - "retry_same_level"  # 更像失误，给同难度复核
  - "remedial_path"     # 更像没掌握，进入补救
  - "none"
```

---

## 7. 下一题推荐策略

文件：`backend/app/api/routers/practice.py`

核心评分：
```
score(q) = w_need * need(q) + w_gain * learn_gain(q) - w_risk * frustration_risk
```

含义：
1. **need(q)**：是否补齐证据缺口（题型/难度）
2. **learn_gain(q)**：与目标难度接近的学习收益
3. **frustration_risk**：表情困难度高 + 连错多 → 降风险

模型融合（可选）：
```
final = 0.7 * rule_score + 0.3 * model_gain
```

---

## 8. 关键配置参数

来源：`EvalConfig.window_json / weights_json / thresholds_json`

常用参数：
- `practice_total`：推荐练习总量  
- `difficulty_step`：难度区间步长  
- `expression_influence`：表情影响系数  
- `evidence_threshold`：证据清单阈值  
- `evidence_sure_ratio`：自评“确定”比例阈值  
- `guess_fast_ms / slip_slow_ms`：猜测/失误时长阈值  
- `w_need / w_gain / w_risk`：推荐评分权重  

---

## 9. 相关代码位置

- 推荐策略：`backend/app/services/reco.py`  
- 证据清单/补救判断：`backend/app/services/reco_policy.py`  
- 掌握度计算：`backend/app/services/eval.py`  
- 练习推荐与错题策略：`backend/app/api/routers/practice.py`  

---

如需继续扩展：
1) 证据清单可视化  
2) 补救通道 UI 引导  
3) 证据清单与小测联动  
4) 管理端参数可视化配置
