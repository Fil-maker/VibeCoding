// One-time tokens travel in the URL fragment (#token=…), so they never reach server logs.
export function readFragmentToken(hash: string): string | null {
  const token = new URLSearchParams(hash.replace(/^#/, '')).get('token');
  return token === null || token === '' ? null : token;
}
