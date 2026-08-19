import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, switchMap, tap } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  tenant_id: string;
  permissions: string[];
}

interface CsrfTokenResponse {
  csrf_token: string;
}

interface LoginPayload {
  email: string;
  password: string;
}

const TOKEN_KEY = 'pf.accessToken';
const TENANT_KEY = 'pf.tenantId';
const TOKEN_EXPIRY_SKEW_MS = 5_000;

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  readonly authenticated = signal(this.hasCurrentStoredToken());

  token(): string | null {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      return null;
    }
    if (!this.isTokenCurrent(token)) {
      this.clearStoredSession();
      this.authenticated.set(false);
      return null;
    }
    return token;
  }

  tenantId(): string | null {
    return localStorage.getItem(TENANT_KEY);
  }

  isAuthenticated(): boolean {
    return this.token() !== null;
  }

  login(payload: LoginPayload): Observable<TokenResponse> {
    return this.http.get<CsrfTokenResponse>(`${this.base}/auth/csrf`).pipe(
      switchMap((csrf) =>
        this.http.post<TokenResponse>(`${this.base}/auth/login`, payload, {
          headers: new HttpHeaders({ 'X-CSRF-Token': csrf.csrf_token }),
        }),
      ),
      tap((token) => this.storeToken(token)),
    );
  }

  logout(): void {
    this.clearStoredSession();
    this.authenticated.set(false);
  }

  private clearStoredSession(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TENANT_KEY);
  }

  private storeToken(token: TokenResponse): void {
    localStorage.setItem(TOKEN_KEY, token.access_token);
    localStorage.setItem(TENANT_KEY, token.tenant_id);
    this.authenticated.set(true);
  }

  private hasCurrentStoredToken(): boolean {
    const token = localStorage.getItem(TOKEN_KEY);
    return Boolean(token && this.isTokenCurrent(token));
  }

  private isTokenCurrent(token: string): boolean {
    const payload = this.decodeJwtPayload(token);
    if (!payload?.exp) {
      return false;
    }
    return payload.exp * 1000 > Date.now() + TOKEN_EXPIRY_SKEW_MS;
  }

  private decodeJwtPayload(token: string): { exp?: number } | null {
    const payload = token.split('.')[1];
    if (!payload) {
      return null;
    }
    try {
      const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
      const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');
      return JSON.parse(atob(padded)) as { exp?: number };
    } catch {
      return null;
    }
  }
}
