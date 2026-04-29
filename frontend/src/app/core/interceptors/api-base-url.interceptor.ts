import { HttpInterceptorFn } from '@angular/common/http';

import { environment } from '../../../environments/environment';

/**
 * Rewrites relative API paths (`api/...`) to the configured backend base URL.
 * Feature code stays environment-agnostic.
 */
export const apiBaseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  const isRelativeApiCall = req.url.startsWith('api/');
  if (!isRelativeApiCall) {
    return next(req);
  }

  const prefix = environment.apiBaseUrl.replace(/\/api\/v1\/?$/, '');
  const rewritten = req.clone({ url: `${prefix}/${req.url}` });
  return next(rewritten);
};
