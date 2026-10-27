// Reads a text field of a submitted form; a missing field counts as empty.
export function formValue(data: FormData, name: string): string {
  const value = data.get(name);
  return typeof value === 'string' ? value : '';
}
