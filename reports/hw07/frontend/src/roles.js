export const canWrite = (role) => role === "writer" || role === "moderator";
export const canDelete = (role) => role === "moderator";