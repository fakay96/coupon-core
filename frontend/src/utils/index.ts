type ErrorMessages = Record<string, string[] | string>;

export function simplifyErrors(errors: unknown): string {
  if (
    typeof errors !== 'object' ||
    errors === null ||
    Array.isArray(errors)
  ) {
    console.warn('Invalid error object passed to simplifyErrors.');
    return '';
  }

  const safeErrors = errors as ErrorMessages;
  const result: string[] = [];

  for (const [field, messages] of Object.entries(safeErrors)) {
    if (Array.isArray(messages)) {
      for (const msg of messages) {
        if (typeof msg === 'string') {
          result.push(`${field}: ${msg}`);
        }
      }
    } else if (typeof messages === 'string') {
      result.push(`${field}: ${messages}`);
    }
  }

  return result.join(' | ');
}
