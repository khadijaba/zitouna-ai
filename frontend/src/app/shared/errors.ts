import { HttpErrorResponse } from '@angular/common/http';

/** The backend answers errors as ProblemDetail: { status, title, detail }. */
export function errorMessage(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return 'Serveur injoignable. Vérifiez que le backend tourne.';
    return err.error?.detail ?? err.error?.title ?? `Erreur ${err.status}`;
  }
  return 'Erreur inattendue';
}

export function fileFrom(event: Event): File | undefined {
  return (event.target as HTMLInputElement).files?.[0];
}
