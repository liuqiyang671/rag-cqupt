const TIME_ZONE_SUFFIX_RE = /(?:Z|[+-]\d{2}:?\d{2})$/i;
const CAMPUS_TIME_ZONE = 'Asia/Shanghai';

export function parseBackendDate(value: string): Date {
  const normalized = TIME_ZONE_SUFFIX_RE.test(value) ? value : `${value}Z`;
  return new Date(normalized);
}

export function formatCampusDateTime(
  value: string,
  options: Intl.DateTimeFormatOptions = {},
): string {
  return parseBackendDate(value).toLocaleString('zh-CN', {
    timeZone: CAMPUS_TIME_ZONE,
    ...options,
  });
}
