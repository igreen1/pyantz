/** `pyantz.jobs.files.simple.mkdir` is in the group `files`. */
export const groupOf = (name: string): string => {
  const parts = name.split(".");
  if (parts[0] === "pyantz" && parts[1] === "jobs" && parts.length > 4) {
    return parts[2];
  }
  return parts.slice(0, -1).join(".") || "other";
};
