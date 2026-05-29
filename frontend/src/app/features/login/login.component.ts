import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'pf-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="pf-login">
      <div class="pf-login__panel">
        <h1>Admin sign in</h1>
        <p class="pf-muted">Use the seeded Milestone 2 administrator account.</p>

        <form [formGroup]="form" (ngSubmit)="submit()">
          <label>
            Email
            <input type="email" formControlName="email" autocomplete="username" />
          </label>

          <label>
            Password
            <input type="password" formControlName="password" autocomplete="current-password" />
          </label>

          @if (error()) {
            <p class="pf-error">{{ error() }}</p>
          }

          <button type="submit" [disabled]="form.invalid || loading()">
            {{ loading() ? 'Signing in...' : 'Sign in' }}
          </button>
        </form>
      </div>
    </section>
  `,
  styles: [
    `
      .pf-login {
        min-height: calc(100vh - 64px);
        display: grid;
        align-items: center;
        max-width: 420px;
      }

      .pf-login__panel {
        background: var(--pf-color-surface);
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        box-shadow: var(--pf-shadow);
        padding: 24px;
      }

      h1 {
        margin: 0 0 6px;
      }

      .pf-muted {
        color: var(--pf-color-ink-muted);
        margin: 0 0 20px;
      }

      form {
        display: grid;
        gap: 14px;
      }

      label {
        display: grid;
        gap: 6px;
        font-size: 13px;
        color: var(--pf-color-ink-muted);
      }

      input {
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 10px 12px;
        font: inherit;
        color: var(--pf-color-ink);
      }

      button {
        border: 0;
        border-radius: var(--pf-radius);
        background: var(--pf-color-primary);
        color: #fff;
        padding: 11px 14px;
        font-weight: 600;
        cursor: pointer;

        &:disabled {
          opacity: 0.6;
          cursor: default;
        }
      }

      .pf-error {
        color: var(--pf-color-danger);
        margin: 0;
        font-size: 13px;
      }
    `,
  ],
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly form = new FormGroup({
    email: new FormControl('admin@payrollfuturistic.co.uk', {
      nonNullable: true,
      validators: [Validators.required, Validators.email],
    }),
    password: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.minLength(8)],
    }),
  });

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.auth.login(this.form.getRawValue()).subscribe({
      next: () => {
        this.loading.set(false);
        void this.router.navigateByUrl('/framework');
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Sign in failed. Check the admin credentials.');
      },
    });
  }
}
