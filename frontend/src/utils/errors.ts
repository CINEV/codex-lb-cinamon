export function getErrorMessage(error: unknown, fallback = "요청에 실패했습니다"): string {
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

export function getErrorMessageOrNull(error: unknown, fallback = "요청에 실패했습니다"): string | null {
  if (!error) {
    return null;
  }
  return getErrorMessage(error, fallback);
}
