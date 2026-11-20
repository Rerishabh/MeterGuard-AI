/**
 * MeterGuard AI - Status Evaluation Helpers
 */

export function getStatusType(meter) {
  const priority = meter?.decision?.priority;
  const status = meter?.decision?.final_status;

  if (
    priority === "CRITICAL" ||
    priority === "HIGH" ||
    status === "FAULT DETECTED" ||
    status === "HIGH PRIORITY ALERT"
  ) {
    return "fault";
  }

  if (priority === "MEDIUM" || status === "SUSPICIOUS") {
    return "suspicious";
  }

  return "normal";
}

export function getStatusText(meter) {
  const type = getStatusType(meter);
  if (type === "fault") return "FAULT";
  if (type === "suspicious") return "SUSPICIOUS";
  return "NORMAL";
}
