const STUDENT_SUBJECT_KEY = "da_student_subject";
const LEGACY_STUDENT_SUBJECT_KEY = "da_student_last_subject";

type CourseLike = {
  title: string;
};

export function getSavedStudentSubject() {
  return localStorage.getItem(STUDENT_SUBJECT_KEY) || localStorage.getItem(LEGACY_STUDENT_SUBJECT_KEY) || "";
}

export function saveStudentSubject(subject: string) {
  const next = String(subject || "").trim();
  if (!next) {
    localStorage.removeItem(STUDENT_SUBJECT_KEY);
    localStorage.removeItem(LEGACY_STUDENT_SUBJECT_KEY);
    return;
  }
  localStorage.setItem(STUDENT_SUBJECT_KEY, next);
  localStorage.setItem(LEGACY_STUDENT_SUBJECT_KEY, next);
}

export function resolveStudentSubject(routeSubject: string, currentSubject: string, courses: CourseLike[]) {
  const available = new Set(courses.map((item) => item.title));
  const candidates = [routeSubject, currentSubject, getSavedStudentSubject(), courses[0]?.title || ""];
  for (const item of candidates) {
    const value = String(item || "").trim();
    if (!value) continue;
    if (!available.size || available.has(value)) return value;
  }
  return "";
}
