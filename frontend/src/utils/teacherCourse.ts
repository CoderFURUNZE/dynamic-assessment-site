const TEACHER_SUBJECT_KEY = "da_teacher_subject";

type CourseLike = {
  title: string;
  active?: boolean;
  lifecycle_status?: string;
};

function normalizeSubjectCandidate(input: string) {
  return String(input || "")
    .replace(/\uFFFD/g, "")
    .replace(/\?/g, "")
    .replace(/\s+/g, "")
    .trim();
}

function resolveFromCourses(raw: string, courses: CourseLike[]) {
  const value = String(raw || "").trim();
  if (!value) return "";

  const normalized = normalizeSubjectCandidate(value);
  if (!normalized) return "";

  const exact = courses.find((item) => item.title === value || item.title === normalized);
  if (exact) return exact.title;

  const fuzzy = courses.find((item) => {
    const title = normalizeSubjectCandidate(item.title);
    return normalized.includes(title) || title.includes(normalized);
  });
  return fuzzy?.title || "";
}

function isCourseAvailable(course?: CourseLike | null) {
  if (!course) return false;
  const lifecycle = String(course.lifecycle_status || "").trim().toLowerCase();
  if (typeof course.active === "boolean" && !course.active) return false;
  if (!lifecycle) return true;
  return lifecycle === "active";
}

function pickDefaultCourse(courses: CourseLike[]) {
  return courses.find((item) => isCourseAvailable(item))?.title || courses[0]?.title || "";
}

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
  const preferredAvailable = courses.some((item) => isCourseAvailable(item));
  const candidates = [routeSubject, currentSubject, getSavedTeacherSubject(), pickDefaultCourse(courses)];
  for (const item of candidates) {
    const value = resolveFromCourses(String(item || ""), courses);
    if (!value) continue;
    const matched = courses.find((course) => course.title === value);
    if (preferredAvailable && !isCourseAvailable(matched)) continue;
    return value;
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
