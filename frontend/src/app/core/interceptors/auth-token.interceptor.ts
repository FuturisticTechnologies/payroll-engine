import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';

const PROTECTED_API_PATHS = ['/tenants', '/employees', '/employment-contracts', '/framework'];

export const authTokenInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.token();
  const isAuthEndpoint = req.url.includes('/auth/login') || req.url.includes('/auth/csrf');
  const isProtectedApi = PROTECTED_API_PATHS.some((path) => req.url.includes(path));

  if (isAuthEndpoint || !isProtectedApi) {
    return next(req);
  }

  if (!token) {
    auth.logout();
    void router.navigateByUrl('/login');
    return throwError(
      () =>
        new HttpErrorResponse({
          status: 401,
          statusText: 'Authentication expired',
          url: req.url,
        }),
    );
  }

  const tenantId = auth.tenantId();
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (tenantId) {
    headers['X-Tenant-ID'] = tenantId;
  }

  return next(req.clone({ setHeaders: headers })).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        auth.logout();
        void router.navigateByUrl('/login');
      }
      return throwError(() => error);
    }),
  );
};
