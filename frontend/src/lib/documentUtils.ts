/**
 * Safe document metadata display and error sanitization utilities for M07.
 */

export function formatFileSize(bytes?: number | null): string {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getMimeBadge(mimeType?: string | null, originalFilename?: string | null): string {
  const mt = (mimeType || "").toLowerCase();
  const fn = (originalFilename || "").toLowerCase();
  if (mt.includes("pdf") || fn.endsWith(".pdf")) return "PDF";
  if (mt.includes("jpeg") || mt.includes("jpg") || fn.endsWith(".jpg") || fn.endsWith(".jpeg")) return "JPEG";
  if (mt.includes("png") || fn.endsWith(".png")) return "PNG";
  if (mimeType) {
    const sub = mimeType.split("/")[1];
    return sub ? sub.toUpperCase() : mimeType.toUpperCase();
  }
  return "FILE";
}

/**
 * Returns formatted page count for PDFs, or null for images/non-paged documents.
 * Guarantees that images never display fake "1 page" or similar values.
 */
export function formatPageCount(
  pageCount?: number | null,
  mimeType?: string | null,
  originalFilename?: string | null
): string | null {
  const isImage = 
    (mimeType && mimeType.startsWith("image/")) || 
    (originalFilename && /\.(jpe?g|png)$/i.test(originalFilename));

  if (isImage) {
    // Images must NOT display page count
    return null;
  }

  if (pageCount !== null && pageCount !== undefined && pageCount > 0) {
    return `${pageCount} ${pageCount === 1 ? "page" : "pages"}`;
  }

  const isPdf = 
    (mimeType && mimeType.includes("pdf")) || 
    (originalFilename && /\.pdf$/i.test(originalFilename));

  if (isPdf) {
    return "N/A";
  }

  return null;
}

/**
 * Safely parses backend validation responses without leaking filesystem paths, stack traces, or SQL errors.
 */
export function sanitizeErrorMessage(err: any): string {
  if (!err) return "An unexpected error occurred.";
  let msg = typeof err === "string" ? err : err.detail || err.message || "";
  if (typeof msg !== "string") {
    try {
      msg = JSON.stringify(msg);
    } catch {
      msg = "Validation failed.";
    }
  }

  const lower = msg.toLowerCase();
  if (lower.includes("unsupported file") || lower.includes("extension not allowed")) {
    return "Unsupported file type. Allowed formats: PDF, JPEG, PNG.";
  }
  if (lower.includes("10 mb") || lower.includes("size exceeds") || lower.includes("exceeds the 10 mb")) {
    return "File size exceeds the 10 MB limit.";
  }
  if (lower.includes("empty file") || lower.includes("zero bytes")) {
    return "Empty files are not allowed.";
  }
  if (lower.includes("magic byte") || lower.includes("content does not match")) {
    return "File content does not match the declared file type.";
  }
  if (lower.includes("corrupt") || lower.includes("invalid or corrupted pdf")) {
    return "Invalid or corrupted PDF document.";
  }
  if (lower.includes("conflict of interest")) {
    return "Conflict of interest: Employees cannot review their own applications.";
  }

  // Strip filesystem paths or internal traces
  if (
    msg.includes("backend/storage") ||
    msg.includes("storage\\documents") ||
    msg.includes("Traceback") ||
    msg.includes("SELECT ") ||
    msg.includes("sqlalchemy") ||
    msg.includes("Exception")
  ) {
    return "A storage or server error occurred while processing the document.";
  }

  return msg;
}
