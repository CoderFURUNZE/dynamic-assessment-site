import { DataAnalysis, EditPen, Histogram, Management, Monitor, Reading, School, Setting, User } from "@element-plus/icons-vue";

export type AppNavItem = {
  key: string;
  label: string;
  path: string;
  icon?: any;
  children?: AppNavItem[];
};

export const appNavigation: Record<"student" | "teacher" | "admin", AppNavItem[]> = {
  student: [
    {
      key: "student-dashboard-group",
      label: "学习总览",
      path: "/student/dashboard",
      icon: Monitor,
      children: [
        { key: "student-dashboard", label: "首页概览", path: "/student/dashboard" },
        { key: "student-graph", label: "知识图谱", path: "/student/graph-workspace" },
      ],
    },
    {
      key: "student-learning-group",
      label: "学习任务",
      path: "/student/enroll",
      icon: Reading,
      children: [
        { key: "student-enroll", label: "课程加入", path: "/student/enroll" },
        { key: "student-report", label: "学习报告", path: "/student/report" },
        { key: "student-questionnaire", label: "补充问卷", path: "/student/questionnaire" },
      ],
    },
  ],
  teacher: [
    {
      key: "teacher-workspace-group",
      label: "课程工作台",
      path: "/teacher/workspace",
      icon: School,
      children: [
        { key: "teacher-workspace", label: "课程概览", path: "/teacher/workspace" },
        { key: "teacher-content", label: "知识图谱", path: "/teacher/content" },
      ],
    },
    {
      key: "teacher-evaluation-group",
      label: "阶段评价",
      path: "/teacher/evaluation?tab=stages",
      icon: DataAnalysis,
      children: [
        { key: "teacher-evaluation-stages", label: "阶段设置", path: "/teacher/evaluation?tab=stages" },
        { key: "teacher-evaluation-indicators", label: "指标配置", path: "/teacher/evaluation?tab=indicators" },
        { key: "teacher-evaluation-imports", label: "数据导入", path: "/teacher/evaluation?tab=imports" },
        { key: "teacher-evaluation-behavior", label: "结果查看", path: "/teacher/evaluation?tab=behavior" },
      ],
    },
    {
      key: "teacher-students-group",
      label: "学生分析",
      path: "/teacher/students?tab=class",
      icon: User,
      children: [
        { key: "teacher-students-class", label: "班级总览", path: "/teacher/students?tab=class" },
        { key: "teacher-students-detail", label: "学生详情", path: "/teacher/students?tab=detail" },
        { key: "teacher-students-rules", label: "规则参考", path: "/teacher/students?tab=rules" },
      ],
    },
    {
      key: "teacher-review-group",
      label: "审核与评分",
      path: "/teacher/review?tab=enrollment",
      icon: EditPen,
      children: [
        { key: "teacher-review-enrollment", label: "报名审核", path: "/teacher/review?tab=enrollment" },
        { key: "teacher-review-final", label: "最终评分", path: "/teacher/review?tab=final" },
      ],
    },
  ],
  admin: [
    {
      key: "admin-dashboard-group",
      label: "平台概览",
      path: "/admin/dashboard",
      icon: Histogram,
      children: [
        { key: "admin-dashboard", label: "总览首页", path: "/admin/dashboard" },
      ],
    },
    {
      key: "admin-basic-group",
      label: "基础管理",
      path: "/admin/basic/courses",
      icon: Management,
      children: [
        { key: "admin-courses", label: "课程管理", path: "/admin/basic/courses" },
        { key: "admin-users", label: "用户管理", path: "/admin/basic/users" },
        { key: "admin-teachers", label: "教师管理", path: "/admin/basic/teachers" },
      ],
    },
    {
      key: "admin-evaluation-group",
      label: "评价配置",
      path: "/admin/evaluation/dimensions",
      icon: Setting,
      children: [
        { key: "admin-dimensions", label: "维度指标", path: "/admin/evaluation/dimensions" },
        { key: "admin-persona", label: "画像规则", path: "/admin/evaluation/persona" },
      ],
    },
  ],
};

export function flattenNavigation(items: AppNavItem[]): AppNavItem[] {
  return items.flatMap((item) => [item, ...(item.children ? flattenNavigation(item.children) : [])]);
}
