const STUDENT_SUBJECT_KEY = "da_student_subject";
const LEGACY_STUDENT_SUBJECT_KEY = "da_student_last_subject";

type CourseLike = {
  title: string;
  active?: boolean;
  enroll_status?: string;
  completed?: boolean;
  learning_available?: boolean;
};

type ResolveStudentSubjectOptions = {
  allowCompleted?: boolean;
  allowUnavailable?: boolean;
};

function isAccessibleCourse(course: CourseLike | undefined, options: ResolveStudentSubjectOptions = {}) {
  if (!course) return false;
  if (course.active === false) return false;
  if (!options.allowUnavailable && course.learning_available === false) return false;
  if (String(course.enroll_status || "").trim().toLowerCase() === "closed") return false;
  return Boolean(String(course.title || "").trim());
}

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

export function resolveStudentSubject(
  routeSubject: string,
  currentSubject: string,
  courses: CourseLike[],
  options: ResolveStudentSubjectOptions = {},
) {
  const accessibleCourses = courses.filter((item) => isAccessibleCourse(item, options));
  const fallbackCourse = accessibleCourses[0] || courses[0];
  const accessibleTitles = new Set(accessibleCourses.map((item) => item.title));
  const candidates = [routeSubject, currentSubject, getSavedStudentSubject(), fallbackCourse?.title || ""];
  for (const item of candidates) {
    const value = String(item || "").trim();
    if (!value) continue;
    if (accessibleTitles.has(value)) return value;
  }
  return String(fallbackCourse?.title || "").trim();
}
