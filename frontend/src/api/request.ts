import { SERVER_UNAVAILABLE_MESSAGE } from '../messages';

// What a failed request carries: the machine code, the Russian message and the per-field messages.
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fields: Readonly<Record<string, string>>;

  constructor(
    code: string,
    message: string,
    status: number,
    fields: Readonly<Record<string, string>>,
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}

interface ErrorEnvelope {
  error: { code: string; message: string; fields?: Record<string, string> | null };
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false;
  }
  const inner: unknown = value.error;
  return (
    typeof inner === 'object' &&
    inner !== null &&
    'code' in inner &&
    typeof inner.code === 'string' &&
    'message' in inner &&
    typeof inner.message === 'string'
  );
}

function toApiError(error: unknown, status: number): ApiError {
  if (isErrorEnvelope(error)) {
    return new ApiError(error.error.code, error.error.message, status, error.error.fields ?? {});
  }
  return new ApiError('unknown', SERVER_UNAVAILABLE_MESSAGE, status, {});
}

interface JsonResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

// Unwraps a generated-client result that has a JSON body: the data, or an ApiError.
export async function unwrap<T>(result: Promise<JsonResult<T>>): Promise<T> {
  const { data, error, response } = await result;
  if (data === undefined) {
    throw toApiError(error, response.status);
  }
  return data;
}

// Unwraps a generated-client result without a body (202, 204): nothing, or an ApiError.
export async function unwrapEmpty(
  result: Promise<{ error?: unknown; response: Response }>,
): Promise<void> {
  const { error, response } = await result;
  if (!response.ok) {
    throw toApiError(error, response.status);
  }
}

// The text to show for any failure: the server's message, or a generic one when there was no answer.
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : SERVER_UNAVAILABLE_MESSAGE;
}

// The per-field messages of a failure, by field name.
export function fieldErrors(error: unknown): ReadonlyMap<string, string> {
  return new Map(error instanceof ApiError ? Object.entries(error.fields) : []);
}

// True when the server refused the request because there is no live session.
export function isNotSignedIn(error: unknown): boolean {
  return error instanceof ApiError && error.code === 'not_signed_in';
}
