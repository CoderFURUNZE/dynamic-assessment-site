const TEACHER_SUBJECT_KEY = "da_teacher_subject";

type CourseLike = {
  title: string;
};

export function getSavedTeacherSubject() {
  return localStorage.getItem(TEACHER_SUBJECT_KEY) || "";
}

export function saveTeacherSubject(subject: string) {
  const next = String(subject || "").trim();
  if (!next) {
    localStorage.removeItem(TEACHER_SUBJECT_KEY);
    return;
  }
  localStorage.setItem(TEACHER_SUBJECT_KEY, next);
}

export function resolveTeacherSubject(
  routeSubject: string,
  currentSubject: string,
  courses: CourseLike[]
) {
  const available = new Set(courses.map((item) => item.title));
  const candidates = [routeSubject, currentSubject, getSavedTeacherSubject(), courses[0]?.title || ""];
  for (const item of candidates) {
    const value = String(item || "").trim();
    if (!value) continue;
    if (!available.size || available.has(value)) return value;
  }
  return "";
}

export function buildTeacherSubjectQuery(
  subject: string,
  extra: Record<string, string | undefined> = {}
) {
  return {
    ...extra,
    subject: String(subject || "").trim() || undefined,
  };
}
