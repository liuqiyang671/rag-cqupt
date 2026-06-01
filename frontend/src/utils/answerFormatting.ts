export function normalizeReferenceSection(answer: string): string {
  const match = answer.match(/引用来源[:：]/);
  if (!match || match.index === undefined) {
    return answer;
  }

  const prefix = answer.slice(0, match.index).trimEnd();
  const suffix = answer.slice(match.index).trimStart();
  if (!prefix) {
    return suffix;
  }
  return `${prefix}\n\n${suffix}`;
}
